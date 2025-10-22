# dashboard/callbacks/forecast_callbacks.py
from dash import Input, Output, State, html, dcc
from dash import dash_table
import plotly.graph_objs as go
import pandas as pd
import io, base64, requests
import logging, traceback
import numpy as np



def sanitize_df_for_chronos(df, timestamp_col=None, target_col=None, preview_rows=3):
    """
    Normalize DataFrame cells:
      - convert numpy.ndarray -> list
      - convert numpy scalar -> python scalar
      - convert pd.NA / np.nan -> None
      - ensure timestamp column parsed to datetime (coerce)
      - ensure target numeric (coerce)
    Returns cleaned DataFrame.
    """
    df = df.copy()
    def _conv(x):
        # numpy array -> Python list
        if isinstance(x, np.ndarray):
            try:
                return x.tolist()
            except Exception:
                return x
        # numpy scalar -> python native
        if isinstance(x, (np.generic,)):
            try:
                return x.item()
            except Exception:
                return x
        # pandas NA / nan -> None
        try:
            if pd.isna(x):
                return None
        except Exception:
            pass
        return x

    for c in df.columns:
        try:
            df[c] = df[c].astype(object).apply(_conv)
        except Exception:
            # last-resort: convert entire column to string then apply
            try:
                df[c] = df[c].apply(lambda v: _conv(v))
            except Exception:
                # keep as-is
                pass

    # timestamp normalization
    if timestamp_col and timestamp_col in df.columns:
        try:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
        except Exception:
            try:
                df[timestamp_col] = pd.to_datetime(df[timestamp_col].astype(str), errors="coerce")
            except Exception:
                pass

    # target normalization
    if target_col and target_col in df.columns:
        try:
            df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
        except Exception:
            pass

    return df



def register_callbacks(app, uploaded_df):
    @app.callback(
        [Output('select-columns', 'children'),
         Output('preview-data', 'children')],
        [Input('upload-data', 'contents')],
        [State('upload-data', 'filename')]
    )
    def update_select_columns(contents, filename):
        if contents is None:
            return "", ""
        try:
            content_type, content_string = contents.split(',')
            decoded = io.BytesIO(base64.b64decode(content_string))
            df = pd.read_csv(decoded)
        except Exception:
            return html.Div("Gagal membaca file CSV. Pastikan format benar.", style={'color': 'red'}), ""
        uploaded_df['df'] = df
        columns = df.columns
        dropdowns = [
            html.Label('ID Column:'),
            dcc.Dropdown(id='id-col', options=[{'label': c, 'value': c} for c in columns], value=columns[0], clearable=False),
            html.Label('Timestamp Column:', style={'marginTop': 8}),
            dcc.Dropdown(id='timestamp-col', options=[{'label': c, 'value': c} for c in columns], value=columns[1], clearable=False),
            html.Label('Target Column:', style={'marginTop': 8}),
            dcc.Dropdown(id='target-col', options=[{'label': c, 'value': c} for c in columns], value=columns[2], clearable=False),
            html.Label('Prediction Length:', style={'marginTop': 8}),
            dcc.Input(id='pred-len', type='number', value=7, min=1, className='form-control'),
            html.Br()
        ]
        preview_table = dash_table.DataTable(
            data=df.head(10).to_dict('records'),
            columns=[{"name": i, "id": i} for i in columns],
            page_size=10,
            style_table={'overflowX': 'auto'}, style_cell={'textAlign': 'left', 'padding': '6px'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
            style_as_list_view=True
        )
        return dropdowns, preview_table

    @app.callback(
        [Output('forecast-log', 'children'),
         Output('forecast-result', 'children'),
         Output('forecast-chart', 'figure')],
        Input('forecast-btn', 'n_clicks'),
        State('id-col', 'value'),
        State('timestamp-col', 'value'),
        State('target-col', 'value'),
        State('pred-len', 'value'),
        State('chronos-model', 'value'),
        prevent_initial_call=True
    )
    def probabilistic_forecast(n_clicks, id_col, timestamp_col, target_col, pred_len, chronos_model):
        
        logger = logging.getLogger("dashboard.forecast")
        if n_clicks is None or n_clicks == 0:
            return "Log belum ada, silakan klik Forecast.", "", go.Figure()

        # basic validation
        df = uploaded_df.get('df', None)
        if df is None:
            return html.Div("Data not loaded! Upload data terlebih dahulu.", style={'color': 'red'}), "", go.Figure()
        if not all([id_col, timestamp_col, target_col, pred_len, chronos_model]):
            return html.Div("Kolom belum lengkap dipilih!", style={'color': 'red'}), "", go.Figure()

        # defensive: make a copy to avoid mutating original uploaded_df
        try:
            df_original = df.copy()
        except Exception:
            df_original = pd.DataFrame(df)

        # Debug: print basic info to logger (remove or lower level in prod)
        try:
            logger.debug("Starting forecast. rows=%s cols=%s", len(df_original), df_original.columns.tolist())
            # show types distribution for first few columns (useful for debugging)
            types_preview = {c: df_original[c].apply(lambda x: type(x)).value_counts().to_dict() for c in df_original.columns[:6]}
            logger.debug("Column types preview: %s", types_preview)
        except Exception:
            logger.exception("Failed to log preview")

        # sanitize dataframe before model call
        try:
            df_input = sanitize_df_for_chronos(df_original, timestamp_col=timestamp_col, target_col=target_col)
            # df_input = df_original
            # optional quick check: ensure no ndarray remains in first rows
            ndarray_cols = []
            for c in df_input.columns:
                sample_types = df_input[c].iloc[:5].apply(lambda x: type(x)).unique().tolist()
                if any(t is np.ndarray for t in sample_types):
                    ndarray_cols.append((c, sample_types))
            if ndarray_cols:
                logger.warning("Found ndarray types in columns: %s", ndarray_cols)
                # convert arrays to lists if present
                for c, _ in ndarray_cols:
                    df_input[c] = df_input[c].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)
        except Exception as e:
            logger.exception("Sanitization failed")
            tb = traceback.format_exc()
            return html.Div(f"Sanitization Error: {str(e)}\n{tb}", style={'color': 'red'}), "", go.Figure()

        # build payload info for passing (not used in direct call, but useful for logs)
        from app.chronos_model import forecast_with_chronos
        payload_info = {
            'id_col': id_col,
            'timestamp_col': timestamp_col,
            'target_col': target_col,
            'prediction_length': int(pred_len),
            'chronos_model': chronos_model,
            'freq': 'D',
            'rows': len(df_input)
        }
        logger.debug("Payload info: %s", payload_info)

        # call forecast function (internal) and catch errors
        try:
            df_pred, logs = forecast_with_chronos(
                df_input,
                id_col=id_col,
                timestamp_col=timestamp_col,
                target_col=target_col,
                freq='D',
                prediction_length=int(pred_len),
                chronos_model=chronos_model,
            )
            forecast_log = logs or ""
            result_df = df_pred.copy() if hasattr(df_pred, "copy") else pd.DataFrame(df_pred)
        except Exception as e_model:
            logger.exception("Model inference error")
            tb = traceback.format_exc()
            # try to include logs variable if exists
            logs_preview = locals().get("logs", "")
            return html.Div(f"Model Error: {str(e_model)}\n{logs_preview}\n\nTraceback:\n{tb}", style={'color': 'red'}), "", go.Figure()

        # validate result_df
        if result_df is None or result_df.empty:
            logger.error("Empty result_df returned from model. logs: %s", forecast_log)
            return html.Div("API Error: empty forecast result. Periksa log model.", style={'color': 'red'}), "", go.Figure()

        # normalize timestamp column
        try:
            if 'timestamp' in result_df.columns:
                result_df['timestamp'] = pd.to_datetime(result_df['timestamp'], errors='coerce')
                # create friendly string for display (safe)
                result_df['timestamp_str'] = result_df['timestamp'].dt.strftime('%Y-%m-%d')
            else:
                # if model returned index as timestamp, try reset_index
                result_df = result_df.reset_index()
                if 'timestamp' in result_df.columns:
                    result_df['timestamp'] = pd.to_datetime(result_df['timestamp'], errors='coerce')
                    result_df['timestamp_str'] = result_df['timestamp'].dt.strftime('%Y-%m-%d')
        except Exception:
            logger.exception("Failed to normalize timestamp in result_df")

        # If the model returns an id column (e.g., 'item_id' or same as id_col), filter to first id for plotting
        try:
            id_column_candidates = [c for c in [id_col, 'item_id', 'id'] if c in result_df.columns]
            if id_column_candidates:
                filter_col = id_column_candidates[0]
                unique_ids = result_df[filter_col].unique()
                if len(unique_ids) > 1:
                    logger.debug("Multiple series in result_df; selecting first id: %s", unique_ids[0])
                result_df = result_df[result_df[filter_col] == unique_ids[0]]
        except Exception:
            logger.exception("Failed to filter by id column")

        # Adjust quantiles / mean to be consistent
        try:
            if 'p10' in result_df.columns and 'p90' in result_df.columns:
                result_df['min_p10_p90'] = result_df[['p10', 'p90']].min(axis=1)
                result_df['max_p10_p90'] = result_df[['p10', 'p90']].max(axis=1)
                result_df['p10'] = result_df['min_p10_p90']
                result_df['p90'] = result_df['max_p10_p90']
            if 'mean' in result_df.columns and 'p10' in result_df.columns and 'p90' in result_df.columns:
                result_df['mean'] = result_df['mean'].clip(lower=result_df['p10'], upper=result_df['p90'])
        except Exception:
            logger.exception("Failed to normalize quantiles/mean")

        # store forecast in shared dict for later download/use
        try:
            uploaded_df['forecast'] = result_df.copy()
        except Exception:
            logger.exception("Failed to write forecast to uploaded_df['forecast']")

        # Build DataTable for UI
        try:
            result_table = dash_table.DataTable(
                data=result_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in result_df.columns],
                page_size=max(1, int(pred_len)),
                style_table={'overflowX': 'auto'}, style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                style_as_list_view=True
            )
        except Exception:
            logger.exception("Failed to build result_table")
            result_table = html.Div("Error building result table", style={'color': 'red'})

        # Build figure
        try:
            fig = go.Figure(layout={'template': 'plotly_white'})
            if 'p90' in result_df.columns and 'p10' in result_df.columns:
                fig.add_trace(go.Scatter(x=result_df['timestamp'], y=result_df['p90'],
                                         line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'))
                fig.add_trace(go.Scatter(x=result_df['timestamp'], y=result_df['p10'],
                                         line=dict(color='rgba(0,0,0,0)'), fill='tonexty',
                                         fillcolor='rgba(33,150,243,0.16)', name='P10–P90 Interval'))
            if 'mean' in result_df.columns:
                fig.add_trace(go.Scatter(x=result_df['timestamp'], y=result_df['mean'],
                                         mode='lines+markers', name='Forecast (mean)', line=dict(width=3), marker=dict(size=6)))
            fig.update_layout(title=f"Probabilistic Forecast ({chronos_model})",
                              xaxis_title="Timestamp", yaxis_title="Forecast Value",
                              legend_title="Quantile", margin={'t': 40, 'l': 40, 'r': 24, 'b': 40})
        except Exception:
            logger.exception("Failed to build figure")
            fig = go.Figure()

        # finally return log, table and figure
        # forecast_log may be long; show top part to UI and keep full logs in server log
        try:
            short_log = (forecast_log[:2000] + '...') if len(str(forecast_log)) > 2000 else forecast_log
        except Exception:
            short_log = str(forecast_log)
        return short_log, result_table, fig


    @app.callback(
        Output('upload-data', 'contents'),
        Input('reset-upload', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_upload(n):
        uploaded_df.clear()
        return None

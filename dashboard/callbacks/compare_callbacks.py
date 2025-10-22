# dashboard/callbacks/compare_callbacks.py
from dash import Input, Output, State, html
from dash import dash_table
import plotly.graph_objs as go
import pandas as pd
from telegram_bot import send_telegram_message
import datetime
import dash_bootstrap_components as dbc
from auth.models import list_users
from dash.exceptions import PreventUpdate

def register_callbacks(app, uploaded_df):
    @app.callback(
        [Output('real-data-table', 'data'),
         Output('real-data-table', 'style_data_conditional'),
         Output('compare-chart', 'figure'),
         Output('forecast-alert', 'children')],
        [Input('add-real-btn', 'n_clicks')],
        [State('real-date', 'date'), State('real-value', 'value'),
         State('real-data-table', 'data')],
        prevent_initial_call=True
    )
    def add_real_data(n_clicks, real_date, real_value, current_data):
        if current_data is None:
            current_data = []
        forecast = uploaded_df.get('forecast', pd.DataFrame())
        if not forecast.empty and 'timestamp' in forecast.columns and 'timestamp_str' not in forecast.columns:
            try:
                forecast['timestamp'] = pd.to_datetime(forecast['timestamp'], utc=True)
                forecast['timestamp'] = forecast['timestamp'].dt.tz_convert(None)
            except Exception:
                forecast['timestamp'] = pd.to_datetime(forecast['timestamp'], errors='coerce')
            forecast['timestamp_str'] = forecast['timestamp'].dt.strftime('%Y-%m-%d')
            uploaded_df['forecast'] = forecast

        if forecast.empty or 'timestamp' not in forecast.columns:
            alert = html.Div(
                [
                    html.I(className="bi bi-exclamation-circle-fill me-2"),
                    "Anda belum melakukan forecasting di halaman Forecasting.",
                    html.Br(),
                    "Silakan upload data dan klik Forecast pada menu Forecasting terlebih dahulu."
                ],
                style={'color': 'orange'}
            )
            empty_fig = go.Figure(layout={'template':'plotly_white', 'title': 'Forecast vs Real Data'})
            return [], [], empty_fig, alert

        if n_clicks > 0 and real_date and real_value is not None:
            try:
                parsed_date = pd.to_datetime(real_date).strftime('%Y-%m-%d')
            except Exception:
                parsed_date = real_date
            exists = any(row['date'] == parsed_date for row in current_data)
            if not exists:
                current_data.append({'date': parsed_date, 'value': real_value})

        for row in current_data:
            pred = forecast[forecast['timestamp_str'] == row['date']]
            if not pred.empty:
                mean_val = float(pred['mean'].values[0]) if 'mean' in pred.columns else None
                p10 = float(pred['p10'].values[0]) if 'p10' in pred.columns else None
                p90 = float(pred['p90'].values[0]) if 'p90' in pred.columns else None
                if mean_val is not None:
                    error = row['value'] - mean_val
                    row['forecast'] = round(mean_val, 2)
                    row['error'] = round(error, 2)
                else:
                    row['forecast'] = '-'
                    row['error'] = '-'
                if p10 is not None and p90 is not None and mean_val is not None:
                    row['anomaly'] = 'Yes' if (row['value'] < p10 or row['value'] > p90) else ''
                else:
                    row['anomaly'] = ''
            else:
                row['forecast'] = '-'
                row['error'] = '-'
                row['anomaly'] = ''

        style_data_conditional = []
        for idx, row in enumerate(current_data):
            if row.get('anomaly') == 'Yes':
                style_data_conditional.append({
                    'if': {'row_index': idx},
                    'backgroundColor': '#ffdddd',
                    'color': '#222',
                    'fontWeight': '600'
                })

        fig = go.Figure(layout={'template': 'plotly_white'})
        if not forecast.empty:
            forecast_sorted = forecast.sort_values("timestamp")
            if 'p90' in forecast_sorted and 'p10' in forecast_sorted:
                fig.add_trace(go.Scatter(x=forecast_sorted['timestamp'], y=forecast_sorted['p90'],
                                         line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'))
                fig.add_trace(go.Scatter(x=forecast_sorted['timestamp'], y=forecast_sorted['p10'],
                                         line=dict(color='rgba(0,0,0,0)'), fill='tonexty',
                                         fillcolor='rgba(33,150,243,0.16)', name='P10–P90 Interval'))
            if 'mean' in forecast_sorted:
                fig.add_trace(go.Scatter(x=forecast_sorted['timestamp'], y=forecast_sorted['mean'],
                                         mode='lines+markers', name='Forecast (mean)', line=dict(width=3), marker=dict(size=6)))
        if current_data:
            dates = [pd.to_datetime(row['date']) for row in current_data]
            values = [row['value'] for row in current_data]
            color_list = ['red' if row.get('anomaly')=='Yes' else 'green' for row in current_data]
            fig.add_trace(go.Scatter(x=dates, y=values, mode='markers+text', name='Real Data',
                                     marker=dict(color=color_list, size=10, symbol='diamond'),
                                     text=[f"{v}" for v in values], textposition='top center'))
        fig.update_layout(title="Forecast vs Real Data (+ Anomaly Highlight)", xaxis_title="Timestamp", yaxis_title="Value", legend_title="Legend", margin={'t':40,'l':40,'r':24,'b':40})

        return current_data, style_data_conditional, fig, None
    
    @app.callback(
        Output("compare-alert", "children"),
        Input("compare-btn", "n_clicks"),
        State("dataset-name", "value"),
        State("real-value", "value"),
        State("p10-value", "value"),
        State("p50-value", "value"),
        State("p90-value", "value"),
        prevent_initial_call=True
    )
    def compare_forecast_with_bounds(n_clicks, dataset_name, real_value, p10, p50, p90):
        if not n_clicks:
            raise PreventUpdate

        if any(v is None for v in [real_value, p10, p50, p90]):
            return dbc.Alert("Lengkapi semua nilai Real, P10, P50, dan P90!", color="warning")

        dataset_name = dataset_name or "Unknown Dataset"
        real_value, p10, p50, p90 = map(float, [real_value, p10, p50, p90])

        # Hitung deviasi terhadap median
        deviation = real_value - p50
        deviation_pct = (deviation / p50) * 100 if p50 != 0 else 0

        # Tentukan status dan pesan alert
        if real_value < p10:
            status = "⚠️"
            alert_type = "danger"
            position_msg = "⚠️ Real value is BELOW the lower bound (P10)."
            alert_title = "🚨 Forecast Alert"
        elif real_value > p90:
            status = "⚠️"
            alert_type = "danger"
            position_msg = "⚠️ Real value is ABOVE the upper bound (P90)."
            alert_title = "🚨 Forecast Alert"
        else:
            status = "✅"
            alert_type = "success"
            position_msg = "✅ Real value is within the forecast confidence range."
            alert_title = "📊 Probabilistic Forecasting Result"

        # Format pesan Telegram
        msg = (
            f"{alert_title}\n\n"
            f"Dataset: <b>{dataset_name}</b>\n"
            f"Real Value: <b>{real_value:.2f}</b>\n\n"
            f"<b>Forecast Range:</b>\n"
            f"  Lower Bound (P10): <b>{p10:.2f}</b>\n"
            f"  Median (P50): <b>{p50:.2f}</b>\n"
            f"  Upper Bound (P90): <b>{p90:.2f}</b>\n\n"
            f"{position_msg}\n"
            f"Deviation from median: <b>{deviation:+.2f}</b> ({deviation_pct:+.2f}%)\n\n"
            f"🕒 Updated at: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
        )

        # Kirim ke semua user dengan telegram_id
        sent_to = 0
        for u in list_users():
            if u.get("telegram_id"):
                send_telegram_message(u["telegram_id"], msg)
                sent_to += 1

        return dbc.Alert(
            f"{status} Hasil dibandingkan. Notifikasi dikirim ke {sent_to} user Telegram.",
            color=alert_type
        )

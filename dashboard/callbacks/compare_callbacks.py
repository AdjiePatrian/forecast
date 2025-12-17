# dashboard/callbacks/compare_callbacks.py
from dash import Input, Output, State, html, dcc
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
import pandas as pd
import dash
from telegram_bot import send_telegram_message_to_all
import base64, io, json
import pandas as pd
from datetime import datetime
from flask_login import current_user

from dash import Input, Output, State
from auth.models import get_db_session, ForecastResult, RealDataInput,get_user_by_username



def _normalize_forecast_df(df):
    """Normalize forecast DataFrame agar punya timestamp & timestamp_str."""
    if df is None:
        return pd.DataFrame()
    df = pd.DataFrame(df) if isinstance(df, (list, dict)) else df.copy()
    if df.empty:
        return df

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    elif 'timestamp_str' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp_str'], errors='coerce')
    else:
        possible = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
        if possible:
            df['timestamp'] = pd.to_datetime(df[possible[0]], errors='coerce')

    df['timestamp_str'] = df['timestamp'].dt.strftime('%Y-%m-%d')
    return df


def register_callbacks(app):
    print("[DEBUG] compare_callbacks.register_callbacks() aktif ✅")

    # ==============================================================
    # 🔹 1️⃣ Tampilkan grafik forecast (saat halaman dibuka)
    # ==============================================================
    @app.callback(
        Output('compare-chart', 'figure'),
        Output('forecast-alert', 'children', ),
        Input('forecast-memory', 'data' ),
        prevent_initial_call=True
    )
    def display_forecast_chart(stored_forecast):
        forecast_df = _normalize_forecast_df(stored_forecast)

        if forecast_df.empty:
            alert = html.Div(
                [
                    html.I(className="bi bi-exclamation-circle-fill me-2"),
                    "Belum ada hasil forecasting tersimpan di browser.",
                    html.Br(),
                    "Silakan buka menu Forecasting → jalankan Forecast → lalu kembali ke halaman Compare."
                ],
                style={'color': 'orange'}
            )
            fig = go.Figure(layout={'template': 'plotly_white', 'title': 'Forecast vs Real Data'})
            return fig, alert

        fig = go.Figure(layout={'template': 'plotly_white'})
        forecast_sorted = forecast_df.sort_values("timestamp")

        # Interval & Mean line
        if {'p10', 'p90'} <= set(forecast_sorted.columns):
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['p90'],
                line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['p10'],
                line=dict(color='rgba(0,0,0,0)'), fill='tonexty',
                fillcolor='rgba(33,150,243,0.16)', name='P10–P90 Interval'
            ))

        if 'mean' in forecast_sorted.columns:
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['mean'],
                mode='lines+markers', name='Forecast (mean)', line=dict(width=3), marker=dict(size=6)
            ))

        fig.update_layout(
            title="Forecast vs Real Data",
            xaxis_title="Tanggal",
            yaxis_title="Nilai",
            legend_title="Legenda",
            margin={'t': 40, 'l': 40, 'r': 24, 'b': 40}
        )
        return fig, None

    # ==============================================================
    # 🔹 2️⃣ Tambahkan data real baru dan tampilkan di tabel
    # ==============================================================
    @app.callback(
        Output('real-data-table', 'data', allow_duplicate=True),
        Output('real-data-table', 'style_data_conditional'),
        Output('alert-select', 'options'),
        Output('compare-chart', 'figure', allow_duplicate=True),
        Input('add-real-btn', 'n_clicks'),
        State('real-date', 'date'),
        State('real-value', 'value'),
        State('real-data-table', 'data'),
        State('forecast-memory', 'data'),
        State('forecast-metadata', 'data'),
        prevent_initial_call=True
    )
    def add_real_data(n_clicks, real_date, real_value, current_data, stored_forecast,forecast_metadata):
        if not n_clicks or not real_date or real_value is None:
            raise PreventUpdate

        if current_data is None:
            current_data = []

        print(f"[DEBUG] Menambahkan data real: {real_date} => {real_value}")
        forecast_df = _normalize_forecast_df(stored_forecast)
        if forecast_df.empty:
            raise PreventUpdate

        parsed_date = pd.to_datetime(real_date).strftime('%Y-%m-%d')
        if not any(row.get('date') == parsed_date for row in current_data):
            current_data.append({'date': parsed_date, 'value': real_value, 'alert_sent': False})


        # Gabungkan dengan data forecast
        for row in current_data:
            pred = forecast_df[forecast_df['timestamp_str'] == row['date']]
            if not pred.empty:
                first = pred.iloc[0]
                mean_val = float(first.get('mean', None)) if pd.notna(first.get('mean', None)) else None
                p10 = float(first.get('p10', None)) if pd.notna(first.get('p10', None)) else None
                p90 = float(first.get('p90', None)) if pd.notna(first.get('p90', None)) else None

                if mean_val is not None:
                    row['forecast'] = round(mean_val, 3)
                    row['error'] = round(row['value'] - mean_val, 3)
                else:
                    row['forecast'], row['error'] = '-', '-'

                if all(v is not None for v in [p10, p90, mean_val]):
                    row['p10'] = p10
                    row['p90'] = p90
                    row['anomaly'] = 'Yes' if (row['value'] < p10 or row['value'] > p90) else ''
                else:
                    row['p10'], row['p90'], row['anomaly'] = '-', '-', ''
            else:
                row.update({'forecast': '-', 'error': '-', 'p10': '-', 'p90': '-', 'anomaly': ''})

        # ✅ Simpan Forecast + Real Data ke Database
        try:
            with get_db_session() as db:
                # Simpan hasil forecast (sekali per session)
                user = get_user_by_username(current_user.username)
                if not user:
                    print("[ERROR] User tidak ditemukan di database!")
                    raise PreventUpdate
                
                forecast_entry = ForecastResult(
                    user_id=user.id,
                    model_name=forecast_metadata.get("model_name", "unknown"),
                    uploaded_filename=forecast_metadata.get("uploaded_filename", "unknown.csv"),
                    forecast_output=stored_forecast,  # langsung simpan JSON forecast
                    created_at=datetime.utcnow()
                )
                db.add(forecast_entry)
                db.flush()

                # Simpan real data (per add)
                real_entry = RealDataInput(
                    forecast_id=forecast_entry.id,
                    real_data=current_data,  # seluruh real data terkini
                    alert_sent=False,
                    anomalies_summary=None,
                    created_at=datetime.utcnow()
                )
                db.add(real_entry)
                db.commit()

            print(f"[DEBUG] Data forecast_id={forecast_entry.id} berhasil disimpan untuk user {current_user.username}")

        except Exception as e:
            print(f"[ERROR] Gagal menyimpan ke database: {e}")

        # Style anomaly
        style_data_conditional = [
            {'if': {'row_index': i}, 'backgroundColor': '#ffdddd', 'color': '#222', 'fontWeight': '600'}
            for i, r in enumerate(current_data) if r.get('anomaly') == 'Yes'
        ]

        # Dropdown options
        options = [{"label": f"{r['date']} — Real: {r['value']}", "value": r['date']} for r in current_data]

        # Update chart
        fig = go.Figure(layout={'template': 'plotly_white'})
        forecast_sorted = forecast_df.sort_values("timestamp")

        if {'p10', 'p90'} <= set(forecast_sorted.columns):
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['p90'],
                line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['p10'],
                line=dict(color='rgba(0,0,0,0)'), fill='tonexty',
                fillcolor='rgba(33,150,243,0.16)', name='P10–P90 Interval'
            ))

        if 'mean' in forecast_sorted.columns:
            fig.add_trace(go.Scatter(
                x=forecast_sorted['timestamp'], y=forecast_sorted['mean'],
                mode='lines+markers', name='Forecast (mean)', line=dict(width=3), marker=dict(size=6)
            ))

        if current_data:
            dates = [pd.to_datetime(row['date']) for row in current_data]
            values = [row['value'] for row in current_data]
            colors = ['red' if row.get('anomaly') == 'Yes' else 'green' for row in current_data]
            fig.add_trace(go.Scatter(
                x=dates, y=values, mode='markers+text', name='Real Data',
                marker=dict(color=colors, size=10, symbol='diamond'),
                text=[f"{v}" for v in values], textposition='top center'
            ))

        fig.update_layout(title="Forecast vs Real Data (+ Anomaly Highlight)")

        return current_data, style_data_conditional, options, fig

    # ==============================================================
    # 🔹 3️⃣ Kirim Alert ke semua user yang punya telegram_id
    # ==============================================================
    @app.callback(
    Output('forecast-alert', 'children', allow_duplicate=True),
    Input('send-alert-btn', 'n_clicks'),
    State('alert-select', 'value'),
    State('real-data-table', 'data'),
    prevent_initial_call=True
    )
    def send_alert_to_selected_row(n_clicks, selected_date, table_data):
        if not n_clicks or not selected_date:
            raise PreventUpdate

        row = next((r for r in table_data if r['date'] == selected_date), None)
        if not row:
            return html.Div("❌ Data tidak ditemukan.", style={'color': 'red'})

        msg = (
            f"🚨 <b>Alert Anomali</b>\n"
            f"📅 Date: {row.get('date')}\n"
            f"📈 Real Value: {row.get('value')}\n"
            f"🔮 Forecast (Mean): {row.get('forecast')}\n"
            f"📉 Lower Bound (P10): {row.get('p10')}\n"
            f"📈 Upper Bound (P90): {row.get('p90')}\n"
            f"⚠️ Error: {row.get('error')}\n"
            f"❗ Anomaly: {row.get('anomaly', '-')}"
        )

        results = send_telegram_message_to_all(msg)
        sent_count = sum(results.values())

        if sent_count > 0:
            try:
                with get_db_session() as db:
                    user = get_user_by_username(current_user.username)
                    latest_forecast = (
                        db.query(ForecastResult)
                        .filter(ForecastResult.user_id == user.id)
                        .order_by(ForecastResult.created_at.desc())
                        .first()
                    )
                    if latest_forecast:
                        real_entry = (
                            db.query(RealDataInput)
                            .filter(RealDataInput.forecast_id == latest_forecast.id)
                            .order_by(RealDataInput.created_at.desc())
                            .first()
                        )
                        if real_entry:
                            real_entry.alert_sent = True
                            db.commit()
                            print(f"[DEBUG] Alert flag updated for forecast_id={latest_forecast.id}")

                return html.Div(f"✅ Pesan terkirim ke {sent_count} user Telegram. (alert_sent updated)", style={'color': 'green'})

            except Exception as e:
                print(f"[ERROR] Gagal update alert_sent: {e}")
                return html.Div("⚠️ Alert terkirim tapi gagal update status di DB.", style={'color': 'orange'})

        else:
            return html.Div("❌ Tidak ada user dengan telegram_id aktif.", style={'color': 'red'})


    # ==============================================================
    # 🔹 4️⃣ Hapus data real yang dipilih
    # ==============================================================
    @app.callback(
        Output('real-data-table', 'data', allow_duplicate=True),
        Output('alert-select', 'options', allow_duplicate=True),
        # Output("compare-output", "children", allow_duplicate=True),
        Input('delete-real-btn', 'n_clicks'),
        State('alert-select', 'value'),
        State('real-data-table', 'data'),
        prevent_initial_call=True
    )
    def delete_real_data(n_clicks, selected_date, table_data):
        """
        Hapus data real dari tabel dan database.
        """
        if not n_clicks or not selected_date:
            raise PreventUpdate

        # 1️⃣ Filter UI table
        new_data = [r for r in table_data if r['date'] != selected_date]
        options = [
            {"label": f"{r['date']} — Real: {r['value']}", "value": r['date']} for r in new_data
        ]

        # 2️⃣ Hapus dari database
        user = get_user_by_username(current_user.username)
        if not user:
            return new_data, options, "⚠️ User tidak ditemukan di database."

        try:
            with get_db_session() as db:
                # Ambil forecast terbaru milik user
                latest_forecast = (
                    db.query(ForecastResult)
                    .filter(ForecastResult.user_id == user.id)
                    .order_by(ForecastResult.created_at.desc())
                    .first()
                )

                if not latest_forecast:
                    return new_data, options #, "⚠️ Tidak ada data forecast ditemukan di database."

                # Ambil data real terkait forecast_id
                real_entry = (
                    db.query(RealDataInput)
                    .filter(RealDataInput.forecast_id == latest_forecast.id)
                    .first()
                )

                if real_entry:
                    db.delete(real_entry)
                    db.flush()

                    # (Opsional) hapus juga forecast-nya
                    # db.delete(latest_forecast)
                    # db.flush()
                    print(f"[DEBUG] Data real untuk tanggal {selected_date} dihapus dari database.")

            return new_data, options  #, f"🗑️ Data real untuk tanggal {selected_date} berhasil dihapus dari database."

        except Exception as e:
            print(f"[ERROR] Gagal menghapus data real dari database: {e}")
            return new_data, options  #, f"❌ Gagal menghapus data dari database: {e}"

    

    # ==============================================================
    # 🔥 5️⃣ RESET TOTAL — Hapus semua data (DB + LocalStorage + UI)
    # ==============================================================
    @app.callback(
        Output('forecast-memory', 'data', allow_duplicate=True),
        Output('forecast-metadata', 'data', allow_duplicate=True),
        Output('real-data-table', 'data', allow_duplicate=True),
        Output('alert-select', 'options', allow_duplicate=True),
        Output('compare-chart', 'figure', allow_duplicate=True),
        Input('reset-compare-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_all_compare(n):
        if not n:
            raise PreventUpdate

        print("[RESET] Tombol Reset Compare ditekan — menghapus DB + localStorage + UI")

        try:
            with get_db_session() as db:
                user = get_user_by_username(current_user.username)

                if not user:
                    print("[RESET][ERROR] User tidak ditemukan.")
                else:
                    # 1️⃣ Ambil semua forecast milik user
                    forecasts = db.query(ForecastResult).filter(
                        ForecastResult.user_id == user.id
                    ).all()

                    forecast_ids = [f.id for f in forecasts]

                    print(f"[RESET] Forecast IDs found: {forecast_ids}")

                    if forecast_ids:
                        # 2️⃣ Hapus semua real data yang terhubung ke forecast tersebut
                        deleted_real = db.query(RealDataInput).filter(
                            RealDataInput.forecast_id.in_(forecast_ids)
                        ).delete(synchronize_session=False)

                        # 3️⃣ Hapus forecast-nya
                        deleted_forecast = db.query(ForecastResult).filter(
                            ForecastResult.id.in_(forecast_ids)
                        ).delete(synchronize_session=False)

                        db.commit()

                        print(f"[RESET] Deleted RealDataInput: {deleted_real}, Deleted ForecastResult: {deleted_forecast}")
                    else:
                        print("[RESET] Tidak ada forecast yang perlu dihapus.")

        except Exception as e:
            print(f"[RESET][ERROR] Gagal menghapus database: {e}")

        # Bersihkan localStorage
        cleared_forecast = None
        cleared_metadata = None

        # Kosongkan UI
        empty_table = []
        empty_options = []

        fig = go.Figure(layout={'template': 'plotly_white'})
        fig.update_layout(title="Forecast vs Real Data")

        return cleared_forecast, cleared_metadata, empty_table, empty_options, fig



    @app.callback(
    Output("save-forecast-btn", "children", allow_duplicate=True),
    Output("save-forecast-btn", "color", allow_duplicate=True),
    Output("save-forecast-btn", "disabled", allow_duplicate=True),
    Input("save-forecast-btn", "n_clicks"),
    State("forecast-memory", "data"),
    State("forecast-metadata", "data"),
    prevent_initial_call=True
    )
    def save_forecast(n, forecast_data, metadata):
        if not n:
            raise PreventUpdate

        if not forecast_data:
            return "❌ No Forecast to Save", "danger", True

        try:
            with get_db_session() as db:
                user = get_user_by_username(current_user.username)

                forecast_entry = ForecastResult(
                    user_id=user.id,
                    model_name=metadata.get("model_name", "unknown"),
                    uploaded_filename=metadata.get("uploaded_filename", "unknown.csv"),
                    forecast_output=forecast_data,
                    created_at=datetime.utcnow()
                )
                db.add(forecast_entry)
                db.commit()

            print("[SAVE] Forecast saved successfully.")
            return "✔ Forecast Saved", "success", True

        except Exception as e:
            print("[SAVE][ERROR] Failed:", e)
            return "❌ Save Failed", "danger", False



    @app.callback(
        Output('forecast-memory', 'data', allow_duplicate=True),
        Output('real-data-table', 'data', allow_duplicate=True),
        Output('real-data-table', 'style_data_conditional', allow_duplicate=True),
        Output('alert-select', 'options', allow_duplicate=True),
        Input('db-load-trigger', 'n_intervals'),
        State('forecast-memory', 'data'),
        prevent_initial_call=True
    )
    def load_data_from_db_on_compare_page(n_intervals, local_forecast):
        print("[COMPARE] Loader triggered...")

        try:
            with get_db_session() as db:
                user = get_user_by_username(current_user.username)

                latest_forecast = (
                    db.query(ForecastResult)
                    .filter(ForecastResult.user_id == user.id)
                    .order_by(ForecastResult.created_at.desc())
                    .first()
                )
        except Exception as e:
            print("[COMPARE][ERROR] gagal akses database:", e)
            latest_forecast = None

        db_has_data = latest_forecast is not None

        # ======================================================
        # 1️⃣ PRIORITAS: DB ADA → Gunakan DB (meskipun Local ada)
        # ======================================================
        if db_has_data:
            print("[COMPARE] DB ditemukan → gunakan DB, abaikan Local")

            forecast_data = latest_forecast.forecast_output

            real_entry = (
                db.query(RealDataInput)
                .filter(RealDataInput.forecast_id == latest_forecast.id)
                .order_by(RealDataInput.created_at.desc())
                .first()
            )

            real_data = real_entry.real_data if real_entry else []

            # fallback tambahan: tambahkan alert_sent jika hilang
            for row in real_data:
                if 'alert_sent' not in row:
                    row['alert_sent'] = False

            # generate style anomaly
            style_data_conditional = [
                {
                    'if': {'row_index': i},
                    'backgroundColor': '#ffdddd',
                    'color': '#222',
                    'fontWeight': '600'
                }
                for i, r in enumerate(real_data)
                if r.get('anomaly') == 'Yes'
            ]

            options = [
                {"label": f"{r['date']} — Real: {r['value']}", "value": r['date']}
                for r in real_data
            ]

            return forecast_data, real_data, style_data_conditional, options

        # ======================================================
        # 2️⃣ PRIORITAS: DB KOSONG + Local ADA → gunakan LocalStorage
        # ======================================================
        if not db_has_data and local_forecast:
            print("[COMPARE] DB kosong, Local ada → gunakan Local forecast")
            raise PreventUpdate  # biarkan local_storage dipakai

        # ======================================================
        # 3️⃣ TIDAK ADA APA-APA → tampil kosong
        # ======================================================
        print("[COMPARE] Tidak ada DB dan tidak ada Local forecast → tampil kosong")
        return None, [], [], []


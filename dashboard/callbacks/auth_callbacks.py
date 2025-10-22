# # dashboard/callbacks/auth_callbacks.py
# import requests
# import dash
# from dash import Input, Output, State, dcc, html
# from dash.exceptions import PreventUpdate
# import dash_bootstrap_components as dbc

# def register_callbacks(app, uploaded_df):
#     """
#     Register auth/login related callbacks.
#     This callback posts credentials to the Flask endpoint /auth/login and
#     shows an alert or redirects to /forecast on success.
#     """
#     @app.callback(
#         Output("login-alert", "children"),
#         Input("login-submit", "n_clicks"),
#         State("login-username", "value"),
#         State("login-password", "value"),
#         prevent_initial_call=True
#     )
#     def handle_login(n_clicks, username, password):
#         # Basic validation
#         if not n_clicks:
#             raise PreventUpdate
#         if not username or not password:
#             return dbc.Alert("Username dan password diperlukan.", color="danger")

#         payload = {"username": username, "password": password}

#         try:
#             # Sesuaikan host:port jika aplikasi Anda jalan di port/host lain
#             resp = requests.post("http://localhost:8050/auth/login", json=payload, timeout=10)
#         except Exception as e:
#             return dbc.Alert(f"Gagal terhubung ke server: {e}", color="danger")

#         # coba parse respons JSON
#         try:
#             j = resp.json()
#         except Exception:
#             j = {}

#         if resp.status_code == 200 and j.get("success"):
#             # tampilkan Location untuk redirect ke /forecast
#             return dcc.Location(href="/forecast", id="login-redirect")
#         else:
#             # ambil pesan error bila ada
#             err = j.get("error") or j.get("msg") or j.get("message") or f"Status {resp.status_code}"
#             return dbc.Alert(f"Login gagal: {err}", color="danger")

# dashboard/callbacks/auth_callbacks.py
"""
Callbacks untuk auth ringan.

PENTING:
- Login sebenarnya dilakukan oleh browser melalui fetch ke /auth/login (assets/login.js).
- Jangan melakukan requests.post(...) ke /auth/login dari server — itu tidak meneruskan cookie ke browser.
"""

from dash import Input, Output
from dash.exceptions import PreventUpdate

def register_callbacks(app, uploaded_df):
    # Callback ringan: bersihkan login-alert saat user mulai mengetik ulang
    # (mencegah callback yang melakukan login server->server).
    try:
        @app.callback(
            Output("login-alert", "children"),
            Input("login-username", "value"),
            Input("login-password", "value"),
            prevent_initial_call=True
        )
        def clear_login_alert(username, password):
            # jika keduanya kosong, jangan ubah (prevent initial)
            if username is None and password is None:
                raise PreventUpdate
            # bersihkan pesan saat user mengubah input
            return ""
    except Exception:
        # Jika page login tidak ada atau elemen belum terdefinisi, aman untuk melewatkan
        pass

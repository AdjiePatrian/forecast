import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flask_login import current_user

# register sebagai root -> landing page
dash.register_page(__name__, path='/login', name='Login', order=0, icon='bi bi-box-arrow-in-right')

def layout():
    # jika sudah login, redirect ke /forecast (atau '/dashboard' sesuai kebutuhan)
    if current_user.is_authenticated:
        return dcc.Location(id='redirect-if-logged-in', pathname='/forecasting', refresh=True)

    form = dbc.Card(
        dbc.CardBody([
            html.H4("Login", className="mb-3"),
            dbc.Form([
                dbc.Row([
                    dbc.Col(dbc.Label("Username"), width=12),
                    dbc.Col(dbc.Input(id="login-username", placeholder="username", type="text"), width=12),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dbc.Label("Password"), width=12),
                    dbc.Col(dbc.Input(id="login-password", placeholder="password", type="password"), width=12),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dbc.Button("Login", id="login-submit", color="primary"), width=12)
                ])
            ]),
            html.Div(id='login-alert', className='mt-3')
        ]),
        style={"maxWidth": "420px", "margin": "40px auto"}
    )

    # tampilkan hanya form (tidak ada menu/topbar)
    return dbc.Container([form], fluid=True,    
                         style={
                            "position": "absolute",
                            "top": "50%",
                            "left": "50%",
                            "transform": "translate(-50%, -50%)"
    })
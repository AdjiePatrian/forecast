import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from flask_login import current_user

dash.register_page(__name__, path='/admin/users', name='User Management', order=50, icon='bi bi-people')

def layout():
    # hanya admin
    if not current_user.is_authenticated:
        return dcc.Location(pathname="/login")
    if getattr(current_user, "role", None) != "admin":
        return dbc.Container([html.H4("Forbidden"), html.P("Anda tidak punya akses ke halaman ini.")])

    return dbc.Container([
        html.H4("User Management", className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Button("Refresh", id="refresh-users", color="primary", className="mb-2"),
                dcc.Loading(html.Div(id="users-table-div"))
            ], md=8),

            dbc.Col([
                html.H5("Add / Edit User"),
                dbc.Input(id="uid", type="hidden"),
                dbc.Input(id="username", placeholder="Username", className="mb-2"),
                dbc.Input(id="password", type="password", placeholder="Password (kosong = tidak ubah)", className="mb-2"),
                dbc.Input(id="telegram-id", placeholder="Telegram ID", type="text", className="mb-2"),
                dbc.Select(
                    id="role",
                    options=[{"label": "admin", "value": "admin"}, {"label": "user", "value": "user"}],
                    value="user",
                    className="mb-2"
                ),
                dbc.Checklist(
                    options=[{"label": "Active", "value": "active"}],
                    value=["active"], id="is-active", className="mb-2"
                ),
                dbc.Button("Save", id="save-user", color="success", className="me-2"),
                dbc.Button("Delete", id="delete-user", color="danger"),
                html.Div(id="action-msg", className="mt-3")
            ], md=4)
        ])
    ], fluid=True)

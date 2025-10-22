from dash import Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
from flask_login import current_user
import dash_bootstrap_components as dbc

from auth.models import list_users, create_user, update_user_by_id, delete_user_by_id

def register_callbacks(app, _):
    @app.callback(
        Output("users-table-div", "children"),
        Input("refresh-users", "n_clicks"),
        prevent_initial_call=False
    )
    def load_users(_):
        if not current_user.is_authenticated or getattr(current_user, "role", None) != "admin":
            return dbc.Alert("Forbidden", color="danger")

        data = list_users()
        table = dash_table.DataTable(
            id="users-table",
            columns=[
                {"name": "ID", "id": "id"},
                {"name": "Username", "id": "username"},
                {"name": "Role", "id": "role"},
                {"name": "Active", "id": "is_active"},
                {"name": "Created", "id": "created_at"},
                {"name": "Telegram", "id": "telegram_id"},
            ],
            data=data,
            row_selectable="single",
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '6px'}
        )
        return table

    # isi form ketika pilih baris
    @app.callback(
        Output("uid", "value"),
        Output("username", "value"),
        Output("password", "value"),
        Output("role", "value"),
        Output("is-active", "value"),
        Output("telegram-id", "value"),
        Input("users-table", "selected_rows"),
        State("users-table", "data"),
        prevent_initial_call=True
    )
    def select_row(rows, data):
        if not rows:
            raise PreventUpdate
        row = data[rows[0]]
        active = ["active"] if row["is_active"] else []
        return row["id"], row["username"], "", row["role"], active, row["telegram_id"]

    # simpan perubahan / tambah user
    @app.callback(
        Output("action-msg", "children"),
        Input("save-user", "n_clicks"),
        State("uid", "value"),
        State("username", "value"),
        State("password", "value"),
        State("role", "value"),
        State("is-active", "value"),
        State("telegram-id", "value"),
        prevent_initial_call=True
    )
    def save_user(n, uid, username, password, role, active,telegram_id):
        if not n:
            raise PreventUpdate
        if getattr(current_user, "role", None) != "admin":
            return dbc.Alert("Forbidden", color="danger")

        try:
            if uid:
                update_user_by_id(int(uid), username=username, password=password or None, role_name=role, is_active=bool(active), telegram_id=telegram_id)
                msg = f"User {username} updated."
            else:
                create_user(username, password, role_name=role, is_active=bool(active))
                msg = f"User {username} created."
            return dbc.Alert(msg, color="success")
        except Exception as e:
            return dbc.Alert(str(e), color="danger")

    # hapus user
    @app.callback(
        Output("action-msg", "children", allow_duplicate=True),
        Input("delete-user", "n_clicks"),
        State("uid", "value"),
        prevent_initial_call=True
    )
    def delete_user(n, uid):
        if not n:
            raise PreventUpdate
        if getattr(current_user, "role", None) != "admin":
            return dbc.Alert("Forbidden", color="danger")

        try:
            delete_user_by_id(int(uid))
            return dbc.Alert("User deleted.", color="warning")
        except Exception as e:
            return dbc.Alert(str(e), color="danger")

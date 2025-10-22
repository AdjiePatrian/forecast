# dashboard/app.py (UPDATED)
import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pprint

# --- Theme + icons ---
BOOTSTRAP_THEME = dbc.themes.FLATLY
BOOTSTRAP_ICONS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"

# shared in-memory storage (dikembalikan/dioper ke callbacks module jika butuh)
uploaded_df = {}

# ---------------------------------------------------------------------
# Helper: duplicate-check (diagnostic) - panggil setelah Dash memuat pages
# ---------------------------------------------------------------------
def _check_duplicate_page_paths_or_modules():
    rels = [v.get("relative_path") for v in dash.page_registry.values()]
    dup_rels = {r for r in rels if rels.count(r) > 1}
    if dup_rels:
        modules = [f"{k} -> {v.get('relative_path')}" for k, v in dash.page_registry.items() if v.get("relative_path") in dup_rels]
        raise Exception(
            "Duplicate page relative_path(s) detected in dash.page_registry: "
            f"{dup_rels}. Modules: {modules}. "
            "Pastikan pages hanya diimport dari package `dashboard.pages` (tidak ada top-level `pages`)."
        )

# ---------------------------------------------------------------------
# Factory: create Dash app bound to an existing Flask server
# ---------------------------------------------------------------------
def create_dash_app(server):
    """
    Create and return a Dash app bound to the given Flask `server`.
    Call this from run.py after:
      - creating Flask app
      - initializing auth (if any)
      - registering any blueprints
    """
    # ensure we explicitly point Dash to the dashboard/pages folder to avoid
    # accidentally loading a top-level `pages/` package.
    this_dir = os.path.dirname(__file__)
    pages_folder = os.path.join(this_dir, "pages")

    if not os.path.isdir(pages_folder):
        # If folder missing, tell user what to do (dash will otherwise raise later).
        raise FileNotFoundError(f"Pages folder not found: {pages_folder}. Create directory dashboard/pages with your page modules.")

    app = dash.Dash(
        __name__,
        server=server,
        external_stylesheets=[BOOTSTRAP_THEME, BOOTSTRAP_ICONS],
        use_pages=True,
        pages_folder=pages_folder,                # <- explicitly point to dashboard/pages
        suppress_callback_exceptions=True,
    )
    app.title = "Zero-Shot Probabilistic Forecasting"

    # Dash will auto-discover pages from the folder we passed above.
    # Now check duplicates (if any).
    _check_duplicate_page_paths_or_modules()

    # -----------------------------------------------------------------
    # Helper: build sidebar (called per-request so current_user is present)
    # -----------------------------------------------------------------
    def build_sidebar():
        """
        Build sidebar: menu (from dash.page_registry) + bottom area:
        - shows "Signed in as ..." when authenticated
        - shows a visible Logout link styled as a red button (NavLink with btn-danger)
        This approach avoids theme/button rendering issues that made the button invisible.
        """
        from flask_login import current_user

        nav_items = []
        pages = list(dash.page_registry.values())
        pages = sorted(pages, key=lambda p: p.get("order", 99))

        for p in pages:
            rel = (p.get("relative_path") or "").rstrip('/')
            name = (p.get("name") or "").strip()
            if not rel or rel == "/":
                continue
            if rel == "/login" or name.lower() == "login" or "login" in (p.get("__module__", "") or "").lower():
                continue
            icon = p.get("icon", "bi bi-file-earmark-text me-2")
            nav_items.append(
                dbc.NavLink([html.I(className=icon), " " + name], href=p["relative_path"], active="exact")
            )

        # Menu: make it flexible and scrollable
        menu_div = html.Div(
            [
                html.Div(html.H5("Menu", className="m-0"), className="p-3 border-bottom"),
                dbc.Nav(nav_items, vertical=True, pills=True, className="p-3"),
            ],
            style={
                "background": "#ffffff",
                "flex": "1 1 auto",
                "overflow": "auto",
                "borderRight": "1px solid rgba(0,0,0,0.06)",
                "boxShadow": "0 4px 18px rgba(12, 38, 63, 0.06)",
            },
        )

        # Bottom area: user info + logout link styled as btn-danger (anchor)
        bottom_children = []
        if getattr(current_user, "is_authenticated", False):
            display_name = getattr(current_user, "username", None) or getattr(current_user, "name", None) or ""

            bottom_children.append(
                html.Div(
                    dbc.NavLink(
                        [html.I(className="bi bi-box-arrow-right me-2"), "Logout"],
                        href="#",
                        id="logout-btn",
                        className="btn btn-danger w-100 text-red",
                    ),
                    style={"padding": "8px 12px 4px 12px"}
                )
            )

            if display_name:
                bottom_children.append(
                    html.Div(f"Signed in as {display_name}", style={"padding": "8px 12px", "fontSize": "13px", "color": "#333"})
                )

            # Use a NavLink (anchor) styled as a Bootstrap danger button so it's always visible
            # bottom_children.append(
            #     html.Div(
            #         dbc.NavLink(
            #             [html.I(className="bi bi-box-arrow-right me-2"), "Logout"],
            #             href="#",
            #             id="logout-btn",
            #             className="btn btn-danger w-100 text-red",
            #         ),
            #         style={"padding": "12px"}
            #     )
            # )

        logout_block = html.Div(bottom_children)

        sidebar = html.Div(
            [
                html.Div(
                    menu_div,
                    className="sidebar-menu",
                ),
                html.Div(
                    logout_block,
                    className="sidebar-footer",
                ),
            ],
            className="sidebar fixed-sidebar"
        )



        return sidebar





    # -----------------------------------------------------------------
    # Serve layout as a callable so build_sidebar() runs per-request
    # -----------------------------------------------------------------
    def serve_layout():
        sidebar = build_sidebar()   # executed in request context

        return html.Div(
            [
                dbc.Navbar(
                    dbc.Container(
                        [
                            html.Div(
                                [
                                    html.Span(className="bi bi-graph-up me-2"),
                                    html.Span("Zero-Shot Probabilistic Forecasting", style={"fontWeight": "600", "fontSize": "18px"}),
                                ]
                            ),
                            html.Div([dbc.Button(html.I(className="bi bi-list"), id="btn-toggle-sidebar", color="light", outline=True, size="sm")]),
                        ]
                    ),
                    id="topbar",
                    color="white",
                    className="shadow-sm",
                    sticky="top",
                    style={"zIndex": 1100},
                ),
                dbc.Container(
                    dbc.Row(
                        [
                            dbc.Col(sidebar, id="sidebar-col", width=2, style={"position": "fixed", "left": 0, "top": "56px", "bottom": 0}),
                            dbc.Col(
                                html.Div([dcc.Location(id="url", refresh=False), dash.page_container]),
                                id="main-col",
                                width=10,
                                style={"marginLeft": "18%", "padding": "24px"},
                            ),
                        ],
                        className="g-0",
                    ),
                    fluid=True,
                    style={"paddingLeft": 0, "paddingRight": 0},
                ),
            ]
        )

    # set layout as callable so it's evaluated per-request (not at import time)
    app.layout = serve_layout

    # -----------------------------------------------------------------
    # UI toggle callback: sembunyikan sidebar/topbar untuk root/login page
    # -----------------------------------------------------------------
    @app.callback(
        Output("sidebar-col", "style"),
        Output("topbar", "style"),
        Output("main-col", "style"),
        Input("url", "pathname"),
    )
    def _toggle_ui_for_login(pathname):
        # daftar path di mana kita ingin menyembunyikan sidebar/topbar
        hide_paths = {"/", "/login"}
        if pathname in hide_paths:
            # sembunyikan sidebar & topbar, dan biarkan main content pakai full width
            return (
                {"display": "none"},
                {"display": "none"},
                {"marginLeft": "0px", "padding": "40px 24px"},
            )
        # default: tampilkan UI normal
        return (
            {"position": "fixed", "left": 0, "top": "56px", "bottom": 0},
            {"zIndex": 1100},
            {"marginLeft": "18%", "padding": "24px"},
        )

    # -----------------------------------------------------------------
    # register callbacks modules AFTER app dibuat (jika ada)
    # -- each callbacks module must expose register_callbacks(app, shared_store)
    # -----------------------------------------------------------------
    shared_store = uploaded_df  # alias


    try:
        from dashboard.callbacks import forecast_callbacks, compare_callbacks
        try:
            forecast_callbacks.register_callbacks(app, shared_store)
            compare_callbacks.register_callbacks(app, shared_store)
        except Exception:
            print("[ERROR]forecast_callbacks or compare_callbacks registration failed")
    except Exception:
        print("[ERROR]forecast_callbacks or compare_callbacks not found")

    # optional auth/admin callbacks if present
    try:
        from dashboard.callbacks import auth_callbacks, admin_callbacks
        try:
            auth_callbacks.register_callbacks(app, shared_store)
        except Exception:
            print("[ERROR]auth_callbacks not found")
        try:
            admin_callbacks.register_callbacks(app, shared_store)
        except Exception:
            print("[ERROR]admin_callbacks not found")
    except Exception:
        print("[ERROR]auth/admin callbacks not found")

    return app

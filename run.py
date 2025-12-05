# run.py
"""
Run script: buat Flask app, daftarkan blueprints (API + auth), buat Dash via dashboard.create_dash_app(server)
Lalu jalankan Flask (yang juga melayani Dash).
"""
import os, secrets
import importlib
import traceback

DEFAULT_HOST = os.environ.get("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("PORT", 8050))
DEBUG = os.environ.get("FLASK_DEBUG", "1") in ("1", "true", "True")

def main():
    # 1) buat Flask app
    from flask import Flask
    flask_app = Flask(__name__, static_folder=None)  # Dash will serve assets itself
    print("[run] Created Flask app")

    flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or "dev-" + secrets.token_urlsafe(24)

    flask_app.config['SESSION_COOKIE_SAMESITE'] = "Lax"

    # 2) register API blueprint(s) dari app.api (forecast_bp)
    try:
        from app.api import forecast_bp
        # jangan beri url_prefix supaya route tetap '/forecast' (sesuai app.api)
        flask_app.register_blueprint(forecast_bp)
        print("[run] Registered app.api.forecast_bp")
    except ModuleNotFoundError:
        print("[run] No app.api module found (skipping API blueprint).")
    except Exception:
        print("[run] Error registering forecast blueprint:\n", traceback.format_exc())

    # 3) init auth (optional)
    try:
        from auth.manager import init_auth
        # many auth.init_auth implementations expect the Flask app object
        try:
            init_auth(flask_app)   # jangan pakai keyword secret_key kecuali fungsi memang menerimanya
            print("[run] init_auth() called")
        except TypeError:
            # fallback: maybe init_auth expects no args or different signature
            try:
                init_auth()
                print("[run] init_auth() called (no-arg)")
            except Exception:
                print("[run] init_auth() call raised:\n", traceback.format_exc())
    except ModuleNotFoundError:
        print("[run] auth package not found — running without auth")
    except Exception:
        print("[run] Error importing/calling init_auth:\n", traceback.format_exc())

    # 4) register auth blueprint if exists (routes)
    try:
        from auth.routes import bp as auth_bp
        if auth_bp.name not in flask_app.blueprints:
            flask_app.register_blueprint(auth_bp)
            print("[run] Registered auth.routes.bp blueprint")
    except ModuleNotFoundError:
        pass
    except Exception:
        print("[run] Error registering auth.routes.bp:\n", traceback.format_exc())

    # 5) create/attach dash app using dashboard.create_dash_app(server)
    dash_app = None
    try:
        from dashboard.app import create_dash_app
        dash_app = create_dash_app(flask_app)
        print("[run] Dash app created via dashboard.create_dash_app()")
    except ModuleNotFoundError:
        print("[run] dashboard.app.create_dash_app not found — skipping Dash creation")
    except Exception:
        print("[run] Error creating Dash app:\n", traceback.format_exc())

    # Helpful debug: list registered pages (if dash is present)
    if dash_app is not None:
        try:
            import dash
            keys = list(dash.page_registry.keys())
            print("=== DASH PAGE REGISTRY KEYS ===")
            print(keys)
        except Exception:
            pass

    try:
        if DEBUG and hasattr(dash_app, "enable_dev_tools"):
            dash_app.enable_dev_tools(
                debug=True,
                dev_tools_ui=True,
                dev_tools_props_check=True,
                dev_tools_serve_dev_bundles=True,
                dev_tools_hot_reload=True,
            )
            print("[run] Dash Dev Tools ENABLED ✅")
        else:
            print("[run] Dash Dev Tools disabled (DEBUG=False)")
    except Exception as e:
        print(f"[run] Gagal mengaktifkan Dash Dev Tools: {e}")

    # 6) jalankan Flask (yang juga melayani Dash + API)
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"[run] Starting Flask (with Dash if attached) at http://{host}:{port} (debug={DEBUG})")
    flask_app.run(host=host, port=port, debug=DEBUG)

if __name__ == "__main__":
    main()

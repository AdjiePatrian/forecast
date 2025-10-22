# app/api.py
from flask import Blueprint, request, jsonify
import pandas as pd
from app.chronos_model import forecast_with_chronos

forecast_bp = Blueprint("forecast_api", __name__)

@forecast_bp.route("/forecast", methods=["POST"])
def forecast():
    try:
        payload = request.get_json()
        df = pd.DataFrame(payload["data"])
        result, logs = forecast_with_chronos(
            df,
            id_col=payload.get("id_col"),
            timestamp_col=payload.get("timestamp_col"),
            target_col=payload.get("target_col"),
            freq=payload.get("freq", "D"),
            prediction_length=int(payload.get("prediction_length", 7)),
            chronos_model=payload.get("chronos_model", "amazon/chronos-t5-tiny"),
        )
        return jsonify({"forecast": result.reset_index().to_dict(orient="records"), "log": logs})
    except Exception as e:
        import traceback
        return jsonify({"forecast": [], "log": traceback.format_exc(), "error": str(e)})

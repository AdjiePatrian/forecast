# app/dispatcher.py (snippet)
from . import lag_llama_model, chronos_model

MODEL_MAP = {
    "lag-llama": lag_llama_model,
    "amazon/chronos-t5-tiny": chronos_model,
    "amazon/chronos-t5-small": chronos_model,
    "amazon/chronos-t5-base": chronos_model,
    "amazon/chronos-bolt-tiny": chronos_model,
    "amazon/chronos-bolt-mini": chronos_model,
    "amazon/chronos-bolt-small": chronos_model,
    "amazon/chronos-bolt-base": chronos_model,
}


def predict(model_key, data_records, id_col, timestamp_col, target_col, prediction_length, **kwargs):
    
    handler = MODEL_MAP.get(model_key)
    if handler is None:
        raise ValueError("Unknown model: " + str(model_key))
    # handlers expected to return (df, log) or df; adapt:
    result = handler.predict(data_records=data_records,
                             id_col=id_col,
                             timestamp_col=timestamp_col,
                             target_col=target_col,
                             prediction_length=prediction_length,
                             **kwargs)
    if isinstance(result, tuple):
        df, log = result
    else:
        df, log = result, ""
    return df, log

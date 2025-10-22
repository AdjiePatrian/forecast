# app/lag_llama_model.py
import torch
import numpy as np
import pandas as pd
from gluonts.evaluation import make_evaluation_predictions, Evaluator
from gluonts.dataset.common import ListDataset
import traceback
import os

# LagLlama estimator class (from your installed package)
from lag_llama_package.lag_llama.gluon.estimator import LagLlamaEstimator

# module-level cache
_predictor_cache = {
    "predictor": None,
    "estimator_args": None,
    "ckpt_path": "app/lag_llama_package/lag-llama.ckpt",
    "device": None
}


def _ensure_predictor(ckpt_path: str, context_length: int, use_rope_scaling: bool,
                      num_parallel_samples: int, device: str = None, batch_size: int = 64):
    """
    Lazy-load predictor from checkpoint; cache into module variable.
    ckpt_path: path to lag-llama.ckpt
    """
    global _predictor_cache

    # simple cache key check
    if _predictor_cache["predictor"] is not None and _predictor_cache["ckpt_path"] == ckpt_path:
        return _predictor_cache["predictor"], _predictor_cache["estimator_args"]

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # load checkpoint
    ckpt = torch.load(ckpt_path, map_location=device)
    estimator_args = ckpt["hyper_parameters"]["model_kwargs"]

    # compute rope scaling if requested
    rope_scaling_arguments = None
    if use_rope_scaling:
        rope_scaling_arguments = {
            "type": "linear",
            "factor": max(1.0, (context_length + 1) / estimator_args.get("context_length", context_length)),
        }

    estimator = LagLlamaEstimator(
        ckpt_path=ckpt_path,
        prediction_length=estimator_args.get("prediction_length", 32),
        context_length=context_length,
        input_size=estimator_args.get("input_size", 1),
        n_layer=estimator_args.get("n_layer", 8),
        n_embd_per_head=estimator_args.get("n_embd_per_head", 32),
        n_head=estimator_args.get("n_head", 4),
        scaling=estimator_args.get("scaling", None),
        time_feat=estimator_args.get("time_feat", None),
        rope_scaling=rope_scaling_arguments,
        batch_size=batch_size,
        num_parallel_samples=num_parallel_samples
    )

    lightning_module = estimator.create_lightning_module()
    transformation = estimator.create_transformation()
    predictor = estimator.create_predictor(transformation, lightning_module, device=device)

    _predictor_cache.update({
        "predictor": predictor,
        "estimator_args": estimator_args,
        "ckpt_path": ckpt_path,
        "device": device
    })
    return predictor, estimator_args


def predict(data_records,
            id_col: str,
            timestamp_col: str,
            target_col: str,
            prediction_length: int,
            ckpt_path: str = "lag-llama.ckpt",
            context_length: int = None,
            use_rope_scaling: bool = False,
            num_samples: int = 100,
            batch_size: int = 64,
            freq: str = "D",
            device: str = None):
    """
    Dispatcher-compatible predict(...) function.

    - data_records: list[dict] (df.to_dict('records')) OR a pandas.DataFrame
    - returns: pd.DataFrame columns ['timestamp','mean','p10','p90'] (prediction_length rows)
    - raises exceptions on failure (caller should handle)
    """
    try:
        # build dataframe
        if isinstance(data_records, pd.DataFrame):
            df = data_records.copy()
        else:
            df = pd.DataFrame(data_records)

        # ensure timestamp column exists
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df = df.sort_values(timestamp_col)
        if df.empty:
            raise ValueError("Empty time series in input data_records")

        # infer context length if not given
        if context_length is None:
            # default: 3 * prediction_length or available history length
            context_length = min(len(df), max(3 * prediction_length, prediction_length))

        # ensure checkpoint exists
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

        # get predictor (lazy-load)
        predictor, est_args = _ensure_predictor(
            ckpt_path=ckpt_path,
            context_length=context_length,
            use_rope_scaling=use_rope_scaling,
            num_parallel_samples=num_samples,
            device=device,
            batch_size=batch_size
        )

        # prepare GluonTS ListDataset for this single series
        start = pd.Timestamp(df[timestamp_col].iloc[0], freq=freq)
        target = df[target_col].astype(float).values

        gluon_ds = ListDataset([{"start": start, "target": target}], freq=freq)

        # run prediction (returns iterator of Forecast objects)
        forecast_it, ts_it = make_evaluation_predictions(
            dataset=gluon_ds,
            predictor=predictor,
            num_samples=num_samples
        )
        forecasts = list(forecast_it)
        tss = list(ts_it)

        if len(forecasts) == 0:
            raise RuntimeError("No forecasts returned by predictor")

        fc = forecasts[0]  # single series
        # fc.samples shape: (num_samples, prediction_length)
        samples = np.asarray(fc.samples)  # (num_samples, prediction_length)
        # compute stats along samples axis
        means = np.mean(samples, axis=0)
        p10 = np.percentile(samples, 10, axis=0)
        p90 = np.percentile(samples, 90, axis=0)

        # build timestamp index for forecast horizon
        # fc.start_date is the first forecast timestamp (GluonTS Forecast has .start_date)
        try:
            horizon_start = pd.Timestamp(fc.start_date)
        except Exception:
            # fallback: last observed timestamp + freq
            last_ts = df[timestamp_col].max()
            horizon_start = pd.to_datetime(last_ts) + pd.tseries.frequencies.to_offset(freq)

        idx = pd.date_range(start=horizon_start, periods=prediction_length, freq=freq)

        out = pd.DataFrame({
            "timestamp": idx,
            "mean": means,
            "p10": p10,
            "p90": p90
        })
        return out, ""   # empty log for now

    except Exception as e:
        # include stacktrace in log to help debug
        return pd.DataFrame(), traceback.format_exc()

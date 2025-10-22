from autogluon.timeseries import TimeSeriesPredictor
from autogluon.timeseries import TimeSeriesDataFrame
import pandas as pd
import sys, io, logging, contextlib



class TeeLogger(io.StringIO):
    def __init__(self):
        super().__init__()
        self.terminal_out = sys.__stdout__
        self.terminal_err = sys.__stderr__
    def write(self, message):
        super().write(message)
        self.terminal_out.write(message)
    def flush(self):
        super().flush()
        self.terminal_out.flush()



def forecast_with_chronos(
    df: pd.DataFrame,
    id_col: str,
    timestamp_col: str,
    target_col: str,
    freq: str = "D",
    prediction_length: int = 7,
    chronos_model: str = 'amazon/chronos-t5-tiny'
):
    log_capture = TeeLogger()
    sys_stdout_backup = sys.stdout
    sys.stdout = log_capture
    try:
        if target_col != 'target':
            df = df.rename(columns={target_col: 'target'})
        df = df.sort_values([id_col, timestamp_col])
        ts_df = TimeSeriesDataFrame.from_data_frame(df, id_column=id_col, timestamp_column=timestamp_col)
        hyperparameters = {
            "Chronos": [
                {
                    "model_path": chronos_model,
                    "ag_args": {"name_suffix": "-ZeroShot"}
                }
            ]
        }
        predictor = TimeSeriesPredictor(
            prediction_length=prediction_length,
            path=None
        ).fit(
            train_data=ts_df,
            hyperparameters=hyperparameters,
            time_limit=60*3,
            enable_ensemble=False
        )
        # FIX: beri argumen data!
        pred = predictor.predict(data=ts_df)
        df_pred = pred.copy()
        if 'mean' not in df_pred.columns:
            if 0.5 in df_pred.columns:
                df_pred['mean'] = df_pred[0.5]
        if '0.1' in df_pred.columns and '0.9' in df_pred.columns:
            df_pred['p10'] = df_pred['0.1']
            df_pred['p90'] = df_pred['0.9']
        df_pred = df_pred.reset_index()
        logs = log_capture.getvalue()
        return df_pred[['timestamp', 'mean', 'p10', 'p90']], logs
    except Exception as e:
        logs = log_capture.getvalue() + f"\nException: {str(e)}"
        # Return empty DataFrame + logs, so unpacking always safe
        return pd.DataFrame(), logs
    finally:
        sys.stdout = sys_stdout_backup




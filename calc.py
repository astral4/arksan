from constants import *
import requests
import pandas as pd

def calc_drop_rates(df):
    df["drop_rate"] = df["quantity"] / df["times"]
    return df

def exclude_limited_stages(stage_ids):
    return stage_ids.str.startswith("main") | stage_ids.str.endswith("perm")

drop_matrix = requests.get("https://penguin-stats.io/PenguinStats/api/v2/result/matrix")\
                      .json()

drop_data = (
    pd.json_normalize(drop_matrix, record_path=["matrix"])
      .drop(["stdDev", "start", "end"], axis=1)
      .pipe(lambda df: df[df["times"] >= MIN_RUN_THRESHOLD])
      .pipe(lambda df: df[exclude_limited_stages(df["stageId"])])
      .pipe(lambda df: df[~df["itemId"].isin(EXCLUDED_ITEMS)])
      .pipe(calc_drop_rates)
      .drop(["times", "quantity"], axis=1)
      .pivot(index="stageId", columns="itemId", values="drop_rate")
      .fillna(0)
)
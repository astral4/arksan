from constants import *
import requests
import pandas as pd

def calc_drop_rates(df):
    df["drop_rate"] = df["quantity"] / df["times"]
    return df

def exclude_limited_stages(stage_ids):
    return stage_ids.str.startswith("main") | stage_ids.str.endswith("perm")

def fix_stage_ids(df):
    df.index = df.index.str.removesuffix("_perm")
    return df

drop_matrix = (
    requests.get("https://penguin-stats.io/PenguinStats/api/v2/result/matrix")
            .json()
            ["matrix"]
)

stage_data = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json")
            .json()
            ["stages"]
)

drop_data = (
    pd.DataFrame(drop_matrix, columns=["stageId", "itemId", "times", "quantity"])
      .pipe(lambda df: df[df["times"] >= MIN_RUN_THRESHOLD])
      .pipe(lambda df: df[exclude_limited_stages(df["stageId"])])
      .pipe(lambda df: df[~df["itemId"].isin(EXCLUDED_ITEMS)])
      .pipe(calc_drop_rates)
      .drop(["times", "quantity"], axis=1)
      .pivot(index="stageId", columns="itemId", values="drop_rate")
      .fillna(0)
      .pipe(fix_stage_ids)
      .assign(sanity = lambda df: df.index.map(lambda stage_id: stage_data[stage_id]["apCost"]))
)
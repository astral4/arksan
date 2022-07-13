from constants import *
import requests
import pandas as pd
from scipy.optimize import linprog

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

def filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "wk_kc", "wk_fly", "wk_armor")) # wk_kc, wk_fly, wk_armor
          | stage_ids.str.endswith("perm")
    )

def patch_sanity_cost(df):
    df.at["a003_f03_perm", "sanity"] = 15
    df.at["a003_f04_perm", "sanity"] = 18
    return df

drop_data = (
    pd.DataFrame(drop_matrix, columns=["stageId", "itemId", "times", "quantity"])
      .pipe(lambda df: df[df["times"] >= MIN_RUN_THRESHOLD])
      .pipe(lambda df: df[filter_stages(df["stageId"])])
      .pipe(lambda df: df[~df["itemId"].isin(EXCLUDED_ITEMS)])
      .assign(drop_rate = lambda df: df["quantity"] / df["times"])
      .drop(["times", "quantity"], axis=1)
      .pivot(index="stageId", columns="itemId", values="drop_rate")
      .fillna(0)
      .assign(sanity = lambda df: df.index.map(lambda stage_id: stage_data[stage_id.removesuffix("_perm")]["apCost"]))
      .pipe(patch_sanity_cost)
)

const_mat = drop_data.iloc[:, :-1].to_numpy()
obj_vec = -const_mat.sum(axis=0)
const_vec = drop_data.iloc[:, -1].to_numpy()

sanity_values = (
    linprog(obj_vec, const_mat, const_vec)
    .x
)
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
            .values()
)

def filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "wk_kc", "wk_fly", "wk_armor")) # wk_kc, wk_fly, wk_armor
          | stage_ids.str.endswith("perm")
    )

def fix_stage_ids(df):
    df.index = df.index.str.removesuffix("_perm")
    return df

drop_data = (
    pd.DataFrame(drop_matrix, columns=["stageId", "itemId", "times", "quantity"])
      .query("times >= @MIN_RUN_THRESHOLD")
      .pipe(lambda df: df[filter_stages(df["stageId"])])
      .query("itemId not in @EXCLUDED_ITEMS")
      .assign(drop_rate = lambda df: df["quantity"] / df["times"])
      .pivot(index="stageId", columns="itemId", values="drop_rate")
      .fillna(0) # do this in the to_numpy() method instead
      .pipe(fix_stage_ids)
)

def fixer(df):
    return df.loc[df.index.isin(drop_data.index)]

def patch_sanity_cost(df):
    df.at["a003_f03", "apCost"] = 15
    df.at["a003_f04", "apCost"] = 18
    return df

sanity_costs = (
    pd.DataFrame(stage_data, columns=["stageId", "apCost"])
      .set_index("stageId")
      .pipe(fixer) # try the same query thing as in drop_data
      .pipe(patch_sanity_cost)
      .reindex(drop_data.index)
)

const_mat = drop_data.to_numpy()
obj_vec = -const_mat.sum(axis=0)
const_vec = sanity_costs.to_numpy()

sanity_values = (
    linprog(obj_vec, const_mat, const_vec)
    .x
)
from constants import *
import requests
import pandas as pd
from scipy.optimize import linprog

drops = (
    requests.get("https://penguin-stats.io/PenguinStats/api/v2/result/matrix")
            .json()
            ["matrix"]
)

stages = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json")
            .json()
            ["stages"]
            .values()
)

recipes = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/en_US/gamedata/excel/building_data.json")
            .json()
            ["workshopFormulas"]
            .values()
)

def filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "sub", "wk_kc", "wk_fly", "wk_armor"))
          | stage_ids.str.endswith("perm")
    )

def fix_stage_ids(df):
    df.index = df.index.str.removesuffix("_perm")
    return df

drop_matrix = (
    pd.DataFrame(drops, columns=["stageId", "itemId", "times", "quantity"])
      .query("times >= @MIN_RUN_THRESHOLD")
      .pipe(lambda df: df[filter_stages(df["stageId"])])
      .query("itemId in @INCLUDED_ITEMS")
      .assign(drop_rate = lambda df: df["quantity"] / df["times"])
      .pivot(index="stageId", columns="itemId", values="drop_rate")
      .reindex(columns=INCLUDED_ITEMS)
      .pipe(fix_stage_ids)
)

def patch_sanity_cost(df):
    df.loc[STAGE_AP_COST.keys(), "apCost"] = list(STAGE_AP_COST.values())
    return df

sanity_costs = (
    pd.DataFrame(stages, columns=["stageId", "apCost"])
      .set_index("stageId")
      .pipe(patch_sanity_cost)
      .reindex(drop_matrix.index)
      .to_numpy()
)

recipe_data = (
    pd.json_normalize(recipes, record_path="extraOutcomeGroup", meta=["itemId", "count", "goldCost", "extraOutcomeRate"], record_prefix="bp_")
      .query("itemId in @INCLUDED_ITEMS")
      .assign(craft_lmd_value = lambda df: df["goldCost"] * LMD_SANITY_VALUE)
      .assign(total_bp_weight = lambda df: df.groupby("itemId")["bp_weight"].transform("sum"))
      .assign(bp_sanity_coeff = lambda df: BYPRODUCT_RATEUP * df["extraOutcomeRate"] * df["bp_weight"] / df["total_bp_weight"])
      .pivot(index=["itemId", "craft_lmd_value"], columns="bp_itemId", values="bp_sanity_coeff")
      .reindex(columns=INCLUDED_ITEMS)
)

def fill_ones(df):
    for id in df.index:
        df.at[id, id] = 1
    return df

recipe_matrix = (
    pd.json_normalize(recipes, record_path="costs", meta="itemId")
      .query("itemId in @INCLUDED_ITEMS")
      .pivot(index="itemId", columns="id", values="count")
      .reindex(columns=INCLUDED_ITEMS)
      .pipe(lambda df: -df)
      .pipe(fill_ones)
      .to_numpy(na_value=0)
)

drop_matrix = drop_matrix.to_numpy(na_value=0)
obj = -drop_matrix.sum(axis=0)
craft_matrix = recipe_matrix + recipe_data.to_numpy(na_value=0)
craft_lmd_values = recipe_data.index.get_level_values("craft_lmd_value").to_numpy()

sanity_values = (
    linprog(obj, drop_matrix, sanity_costs, craft_matrix, craft_lmd_values)
    .x
)
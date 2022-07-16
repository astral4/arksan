from constants import *
import requests
import pandas as pd
import dateparser
from scipy.optimize import linprog

def unix_to_dt(df):
    df["start"] = pd.to_datetime(df["start"], unit="ms")
    return df

def filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "sub", "wk"))
          | stage_ids.str.endswith("perm")
    )

def trim_stage_ids(df):
    df.index = df.index.str.removesuffix("_perm")
    return df

def patch_stage_costs(df):
    stages, sanity_costs = zip(*MISSING_STAGE_COSTS.items())
    df.loc[stages, "apCost"] = sanity_costs
    return df

def fill_diagonal(df, values):
    for id, val in zip(df.index, values):
        df.at[id, id] = val
    return df

def finalize_drops(df):
    matrix = df.to_numpy(na_value=0)
    return matrix, -matrix.sum(axis=0)

drops = (
    requests.get(DROP_URL)
            .json()
            ["matrix"]
)

stages = (
    requests.get(STAGE_URL)
            .json()
            ["stages"]
            .values()
)

recipes = (
    requests.get(RECIPE_URL)
            .json()
            ["workshopFormulas"]
            .values()
)

recipe_data = (
    pd.json_normalize(recipes,
                      record_path="extraOutcomeGroup",
                      meta=["itemId", "count", "goldCost", "extraOutcomeRate"],
                      record_prefix="bp_")
      .query("itemId in @INCLUDED_ITEMS")
      .assign(craft_lmd_value = lambda df: df["goldCost"] * LMD_SANITY_VALUE)
      .assign(total_bp_weight = lambda df: df.groupby("itemId")["bp_weight"]
                                             .transform("sum"))
      .assign(bp_sanity_coeff = lambda df: BYPRODUCT_RATEUP *
                                           df["extraOutcomeRate"] *
                                           df["bp_weight"] /
                                           df["total_bp_weight"])
      .pivot(index=["itemId", "count", "craft_lmd_value"],
             columns="bp_itemId",
             values="bp_sanity_coeff")
      .reindex(columns=INCLUDED_ITEMS)
)

ingredient_matrix = (
    pd.json_normalize(recipes,
                      record_path="costs",
                      meta="itemId")
      .query("itemId in @INCLUDED_ITEMS")
      .pivot(index="itemId",
             columns="id",
             values="count")
      .reindex(columns=INCLUDED_ITEMS)
      .pipe(lambda df: -df)
      .pipe(fill_diagonal,
            recipe_data.index.get_level_values("count"))
      .to_numpy(na_value=0)
)

drop_matrix = (
    pd.DataFrame(drops,
                 columns=["stageId", "itemId", "times", "quantity", "start"])
      .pipe(unix_to_dt)
      .query("times >= @MIN_RUN_THRESHOLD and \
              itemId in @INCLUDED_ITEMS")
      .pipe(lambda df: df[filter_stages(df["stageId"])])
      .assign(drop_rate = lambda df: df["quantity"] / df["times"])
      .pivot(index="stageId",
             columns="itemId",
             values="drop_rate")
      .reindex(columns=INCLUDED_ITEMS)
      .pipe(trim_stage_ids)
)

sanity_costs = (
    pd.DataFrame(stages,
                 columns=["stageId", "apCost"])
      .set_index("stageId")
      .pipe(patch_stage_costs)
      .reindex(drop_matrix.index)
      .to_numpy()
)

stage_drops, sanity_profit = finalize_drops(drop_matrix)
item_equiv_matrix = ingredient_matrix + recipe_data.to_numpy(na_value=0)
craft_lmd_values = recipe_data.index.get_level_values("craft_lmd_value").to_numpy()

sanity_values = (
    linprog(sanity_profit, stage_drops, sanity_costs, item_equiv_matrix, craft_lmd_values)
    .x
)

sanity_values = {item_id: sanity_value for item_id, sanity_value in zip(INCLUDED_ITEMS, sanity_values)}
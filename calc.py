from constants import *
import requests
import pandas as pd
from scipy.optimize import linprog

def filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "sub", "wk"))
          | stage_ids.str.endswith("perm")
    )

def trim_stage_ids(df):
    df["stageId"] = df["stageId"].str.removesuffix("_perm")
    return df

def unix_to_dt(df):
    df["start"] = pd.to_datetime(df["start"], unit="ms")
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
    requests.get(DROPS_URL)
            .json()
            ["matrix"]
)

drop_data = (
    pd.DataFrame(drops,
                 columns=["stageId", "itemId", "times", "quantity", "start"])
    .query("times >= @MIN_RUN_THRESHOLD")
    .pipe(lambda df: df[filter_stages(df["stageId"])])
    .pipe(trim_stage_ids)
    .pipe(unix_to_dt)
    .assign(drop_rate = lambda df: df["quantity"] / df["times"])
)

stages = (
    requests.get(STAGES_URL)
            .json()
            ["stages"]
            .values()
)

stage_sanity_costs = (
    pd.DataFrame(stages,
                columns=["stageId", "apCost"])
      .set_index("stageId")
      .pipe(patch_stage_costs)
)

recipes = (
    requests.get(RECIPES_URL)
            .json()
            ["workshopFormulas"]
            .values()
)

recipe_data = (
    pd.json_normalize(recipes,
                      record_path="extraOutcomeGroup",
                      meta=["itemId", "count", "goldCost", "extraOutcomeRate"],
                      record_prefix="bp_")
      .assign(craft_lmd_value = lambda df: LMD_SANITY_VALUE * df["goldCost"])
      .assign(total_bp_weight = lambda df: df.groupby("itemId")["bp_weight"]
                                             .transform("sum"))
      .assign(bp_sanity_coeff = lambda df: BYPRODUCT_RATEUP *
                                           df["extraOutcomeRate"] *
                                           df["bp_weight"] /
                                           df["total_bp_weight"])
      .pivot(index=["itemId", "count", "craft_lmd_value"],
             columns="bp_itemId",
             values="bp_sanity_coeff")
)

ingredient_matrix = (
    pd.json_normalize(recipes,
                      record_path="costs",
                      meta="itemId")
      .pivot(index="itemId",
             columns="id",
             values="count")
      .pipe(lambda df: -df)
)

def get_sanity_values(datetime, items):
    drop_matrix = (
        drop_data.query("start <= @datetime")
                 .pivot(index="stageId",
                        columns="itemId",
                        values="drop_rate")
                 .reindex(columns=items)
    )

    byproduct_matrix = (
        recipe_data.query("itemId in @items")
                   .reindex(columns=items)
    )

    recipe_matrix = (
        ingredient_matrix.query("itemId in @items")
                         .reindex(columns=items)
                         .pipe(fill_diagonal,
                               byproduct_matrix.index.get_level_values("count"))
                         .to_numpy(na_value=0)
    )

    sanity_costs = (
        stage_sanity_costs.reindex(drop_matrix.index)
                          .to_numpy()
    )

    stage_drops, sanity_profit = finalize_drops(drop_matrix)
    item_equiv_matrix = recipe_matrix + byproduct_matrix.to_numpy(na_value=0)
    craft_lmd_values = byproduct_matrix.index.get_level_values("craft_lmd_value").to_numpy()

    return linprog(sanity_profit, stage_drops, sanity_costs, item_equiv_matrix, craft_lmd_values).x
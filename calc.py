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
      .query("itemId in @INCLUDED_ITEMS")
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
      .query("itemId in @INCLUDED_ITEMS")
      .pivot(index="itemId",
             columns="id",
             values="count")
      .pipe(lambda df: -df)
)

def get_sanity_values(datetime):
    drop_matrix = (
        drop_data.query("itemId in @INCLUDED_ITEMS")
                 .pivot(index=["stageId", "start"],
                        columns="itemId",
                        values="drop_rate")
                 .reindex(columns=INCLUDED_ITEMS)
                 .reset_index()
                 .query("start <= @datetime")
                 .drop(columns="start")
                 .set_index("stageId")
    )

    ordered_recipe_data = recipe_data.reindex(columns=INCLUDED_ITEMS)

    real_ingredient_matrix = (
        ingredient_matrix.reindex(columns=INCLUDED_ITEMS)
                         .pipe(fill_diagonal,
                               ordered_recipe_data.index.get_level_values("count"))
                         .to_numpy(na_value=0)
    )

    item_equiv_matrix = real_ingredient_matrix + ordered_recipe_data.to_numpy(na_value=0)
    craft_lmd_values = ordered_recipe_data.index.get_level_values("craft_lmd_value").to_numpy()

    sanity_costs = (
        stage_sanity_costs.reindex(drop_matrix.index)
                          .to_numpy()
    )

    stage_drops, sanity_profit = finalize_drops(drop_matrix)

    return linprog(sanity_profit, stage_drops, sanity_costs, item_equiv_matrix, craft_lmd_values).x
import requests
import pandas as pd
from scipy.optimize import linprog

_MIN_RUN_THRESHOLD = 100

_MISSING_STAGE_COSTS = {
    "a003_f03": 15, # OF-F3
    "a003_f04": 18, # OF-F4
}

_LMD_SANITY_VALUE = 36/10000 # sanity:LMD ratio of CE-6. The sanity value of LMD was 30/7500 (CE-5)
                             # before 2022-05-01 08:00:00 GMT, but LMD value does not significantly affect results anyway
_BYPRODUCT_RATE_BONUS = 1.8

def _filter_stages(stage_ids):
    return (stage_ids.str.startswith(("main", "sub", "wk")) |
            stage_ids.str.endswith("perm"))

def _trim_stage_ids(df):
    df["stageId"] = df["stageId"].str.removesuffix("_perm")
    return df

def _unix_to_dt(df):
    df["start"] = pd.to_datetime(df["start"], unit="ms")
    return df

def _patch_stage_costs(df):
    stages, sanity_costs = zip(*_MISSING_STAGE_COSTS.items())
    df.loc[stages, "apCost"] = sanity_costs
    return df

def _fill_diagonal(df, values):
    for id, val in zip(df.index, values):
        df.at[id, id] = val
    return df

def _finalize_drops(df):
    matrix = df.to_numpy(na_value=0)
    return matrix, -matrix.sum(axis=0)

_drops = (
    requests.get("https://penguin-stats.io/PenguinStats/api/v2/result/matrix")
            .json()
            ["matrix"]
)

_drop_data = (
    pd.DataFrame(data=_drops,
                 columns=["stageId", "itemId", "times", "quantity", "start"])
    .query("times >= @_MIN_RUN_THRESHOLD")
    .pipe(lambda df: df[_filter_stages(df["stageId"])])
    .pipe(_trim_stage_ids)
    .pipe(_unix_to_dt)
    .assign(drop_rate = lambda df: df["quantity"] / df["times"])
    .pivot(index=["stageId", "start"],
           columns="itemId",
           values="drop_rate")
)

_stages = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json")
            .json()
            ["stages"]
            .values()
)

_stage_sanity_costs = (
    pd.DataFrame(data=_stages,
                 columns=["stageId", "apCost"])
      .set_index("stageId")
      .pipe(_patch_stage_costs)
)

_recipes = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/building_data.json")
            .json()
            ["workshopFormulas"]
            .values()
)

_recipe_data = (
    pd.json_normalize(data=_recipes,
                      record_path="extraOutcomeGroup",
                      meta=["itemId", "count", "goldCost", "extraOutcomeRate"],
                      record_prefix="bp_")
      .assign(craft_lmd_value = lambda df: _LMD_SANITY_VALUE * df["goldCost"])
      .assign(total_bp_weight = lambda df: df.groupby("itemId")
                                            ["bp_weight"]
                                             .transform("sum"))
      .assign(bp_sanity_coeff = lambda df: _BYPRODUCT_RATE_BONUS *
                                           df["extraOutcomeRate"] *
                                           df["bp_weight"] /
                                           df["total_bp_weight"])
      .pivot(index=["itemId", "count", "craft_lmd_value"],
             columns="bp_itemId",
             values="bp_sanity_coeff")
)

_ingredient_matrix = (
    pd.json_normalize(data=_recipes,
                      record_path="costs",
                      meta="itemId")
      .pivot(index="itemId",
             columns="id",
             values="count")
      .pipe(lambda df: -df)
)

def get_sanity_values(datetime, items):
    drop_matrix = (
        _drop_data.query("start <= @datetime")
                  .reindex(columns=items)
                  .reset_index(level="start", drop=True)
    )

    byproduct_matrix = (
        _recipe_data.query("itemId in @items")
                    .reindex(columns=items)
    )

    recipe_matrix = (
        _ingredient_matrix.query("itemId in @items")
                          .reindex(columns=items)
                          .pipe(_fill_diagonal,
                                byproduct_matrix.index.get_level_values("count"))
                          .to_numpy(na_value=0)
    )

    sanity_costs = (
        _stage_sanity_costs.reindex(drop_matrix.index)
                           .to_numpy()
    )

    stage_drops, sanity_profit = _finalize_drops(drop_matrix)
    item_equiv_matrix = recipe_matrix + byproduct_matrix.to_numpy(na_value=0)
    craft_lmd_values = byproduct_matrix.index.get_level_values("craft_lmd_value").to_numpy()

    return linprog(sanity_profit, stage_drops, sanity_costs, item_equiv_matrix, craft_lmd_values).x
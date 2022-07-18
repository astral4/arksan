from constants import *
import pandas as pd
import dateparser
import requests
from collections import defaultdict
import calc

def adjust_time(df):
    df["国服上线时间"] += pd.Timedelta(hours=16)
    return df

char_debut_times = (
    pd.read_html(CHAR_DEBUT_TIMES_URL,
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .drop(columns=["稀有度", "国服上线途径", "主要获得方式", "干员预告"])
      .pipe(adjust_time)
      .set_index("干员")
      .rename_axis("name")
)

chars = (
    requests.get(CHARS_URL)
            .json()
            .values()
)

char_upgrade_costs = (
    pd.json_normalize(chars,
                      record_path=["skills", "levelUpCostCond", "levelUpCost"],
                      meta=["name", "appellation", "rarity",
                            ["skills", "skillId"],
                            ["skills", "lvlUpCostCond", "lvlUpTime"]],
                      sep="_")
      .query("rarity == 5")
      .pivot(index=["name", "appellation", "skills_skillId", "skills_lvlUpCostCond_lvlUpTime"],
             columns="id",
             values="count")
      .groupby(["name", "appellation", "skills_skillId"])
      .sum()
      .reset_index(level="appellation")
      .join(char_debut_times)
      .set_index(["appellation", "国服上线时间"])
      .sort_index(axis=0, level="国服上线时间")
      .reindex(columns=VALID_ITEMS)
)

sanity_costs = defaultdict()

for char_name, upgrade_costs in char_upgrade_costs.groupby(level="appellation", sort=False):
    debut_time = upgrade_costs.index.get_level_values("国服上线时间")[0]

    if debut_time < pd.to_datetime("2019-12-24 08:00:00"): # ch6
        upgrade_costs = upgrade_costs.drop(columns=["31013", "31014", "31023", "31024"])
    if debut_time < pd.to_datetime("2020-11-01 08:00:00"): # ch8
        upgrade_costs = upgrade_costs.drop(columns=["31033", "31034", "30145"])
    if debut_time < pd.to_datetime("2021-09-17 08:00:00"): # ch9
        upgrade_costs = upgrade_costs.drop(columns=["31043", "31044", "31053", "31054"])

    sanity_values = calc.get_sanity_values(debut_time, upgrade_costs.columns)
    sanity_costs[char_name] = upgrade_costs.to_numpy(na_value=0).dot(sanity_values)

mastery_costs = (
    pd.DataFrame(sanity_costs)
      .set_axis([1, 2, 3])
      .rename_axis("Skill Number", axis=0)
      .rename_axis("Operators", axis=1)
)
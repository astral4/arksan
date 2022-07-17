from constants import *
import pandas as pd
import dateparser
import requests

def adjust_time(df):
    df["国服上线时间"] += pd.Timedelta(hours=16)
    return df

char_debut_times = (
    pd.read_html(CHAR_DEBUT_TIMES_URL,
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .drop(columns=["稀有度", "国服上线途径", "主要获得方式", "干员预告"])
      .pipe(adjust_time)
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
      .pipe(lambda df: pd.pivot_table(df,
                                      index=["name", "appellation", "skills_skillId", "skills_lvlUpCostCond_lvlUpTime"],
                                      columns="id",
                                      values="count",
                                      sort=False,
                                      fill_value=0))
      .groupby(["name", "appellation", "skills_skillId"])
      .sum()
)

print(char_upgrade_costs)
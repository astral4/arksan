from constants import *
import pandas as pd
import dateparser
import requests
from collections import defaultdict
from calc import get_sanity_values

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
                      record_path=["phases", "evolveCost"],
                      meta=["name", "appellation", ["phases", "maxLevel"]],
                      sep="_")
      .query("phases_maxLevel == 90")
      .pivot(index=["name", "appellation"],
             columns="id",
             values="count")
      .reset_index()
      .merge(char_debut_times,
             how="left",
             left_on="name",
             right_on="干员")
      .drop(columns=["name", "干员"])
      .set_index(["appellation", "国服上线时间"])
      .sort_index(level="国服上线时间")
      .reindex(columns=INCLUDED_ITEMS)
)

sanity_costs = defaultdict()

for char_data, upgrade_cost in char_upgrade_costs.iterrows():
    char_name, debut_time = char_data
    sanity_costs[char_name] = upgrade_cost.to_numpy(na_value=0).dot(get_sanity_values(debut_time))
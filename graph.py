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
      .reindex(columns=VALID_ITEMS)
)

sanity_costs = defaultdict(float)

for char_data, upgrade_cost in char_upgrade_costs.iterrows():
    char_name, debut_time = char_data
    
    if debut_time < pd.to_datetime("2019-12-24 08:00:00"): # ch6
        upgrade_cost = upgrade_cost.drop(labels=["31013", "31014", "31023", "31024"])
    if debut_time < pd.to_datetime("2020-11-01 08:00:00"): # ch8
        upgrade_cost = upgrade_cost.drop(labels=["31033", "31034", "30145"])
    if debut_time < pd.to_datetime("2021-09-17 08:00:00"): # ch9
        upgrade_cost = upgrade_cost.drop(labels=["31043", "31044", "31053", "31054"])

    sanity_costs[char_name] = upgrade_cost.to_numpy(na_value=0).dot(calc.get_sanity_values(debut_time, upgrade_cost.index.to_numpy()))

print(sanity_costs)
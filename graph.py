from constants import *
import pandas as pd
import dateparser
import requests
from collections import defaultdict
import calc
import seaborn as sns

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
      .reset_index()
      .melt(id_vars="index")
      .set_axis(["Skill", "Operator", "Sanity Cost"], axis=1)
)

sns.set_theme(style="whitegrid", context="paper", palette=["#fb2c20", "#43c03b", "#3060a8"], font_scale=2)
cost_bar = (
    sns.catplot(data=mastery_costs, kind="bar",
                x="Operator", y="Sanity Cost", hue="Skill",
                alpha=.8, height=10, aspect=4)
       .set_xticklabels(rotation=90)
       .set(ylim=(3200, 4800))
)
cost_bar.fig.suptitle("6* Operator Skill Mastery Costs", y=1.05)
cost_bar.savefig("mastery_costs_bar.png", dpi=200)

sns.set_theme(style="whitegrid", context="paper")
cost_hist = sns.displot(mastery_costs, x="Sanity Cost", color="#52ad9c", alpha=1, bins=20, aspect=1.2)
cost_hist.fig.suptitle("6* Operator Skill Mastery Costs", y=1.02)
cost_hist.savefig("mastery_costs_hist.png", dpi=200)
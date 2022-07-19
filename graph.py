import calc
import requests
from collections import defaultdict
import pandas as pd
import dateparser
import seaborn as sns

VALID_ITEMS = (
    "30011", "30021", "30031", "30041", "30051", "30061", # t1 mats
    "30012", "30022", "30032", "30042", "30052", "30062", # t2 mats
    "30013", "30023", "30033", "30043", "30053", "30063", "30073", "30083", "30093", "30103", "31013", "31023", "31033", "31043", "31053", # t3 mats
    "30014", "30024", "30034", "30044", "30054", "30064", "30074", "30084", "30094", "30104", "31014", "31024", "31034", "31044", "31054", # t4 mats
    "30115", "30125", "30135", "30145", # t5 mats
    "3301", "3302", "3303", # skillbooks
    "3003", # gold bar
    "2001", "2002", "2003", "2004", # exp cards
    "furni"
)

def _adjust_time(df):
    df["国服上线时间"] += pd.Timedelta(hours=16)
    return df

_char_debut_times = (
    pd.read_html("https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%8A%E7%BA%BF%E6%97%B6%E9%97%B4%E4%B8%80%E8%A7%88",
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .drop(columns=["稀有度", "国服上线途径", "主要获得方式", "干员预告"])
      .pipe(_adjust_time)
      .set_index("干员")
      .rename_axis("name")
)

_chars = (
    requests.get("https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json")
            .json()
            .values()
)

_char_upgrade_costs = (
    pd.json_normalize(_chars,
                      record_path=["skills", "levelUpCostCond", "levelUpCost"],
                      meta=["name", "appellation", "rarity", ["skills", "skillId"], ["skills", "lvlUpCostCond", "lvlUpTime"]],
                      sep="_")
      .query("rarity == 5")
      .pivot(index=["name", "appellation", "skills_skillId", "skills_lvlUpCostCond_lvlUpTime"],
             columns="id",
             values="count")
      .groupby(["name", "appellation", "skills_skillId"])
      .sum()
      .reset_index(level="appellation")
      .join(_char_debut_times)
      .set_index(["appellation", "国服上线时间"])
      .sort_index(axis=0, level="国服上线时间")
      .reindex(columns=VALID_ITEMS)
)

_sanity_costs = defaultdict()

for _char_name, _upgrade_costs in _char_upgrade_costs.groupby(level="appellation", sort=False):
    _debut_time = _upgrade_costs.index.get_level_values("国服上线时间")[0]

    if _debut_time < pd.to_datetime("2019-12-24 08:00:00"): # ch6
        _upgrade_costs = _upgrade_costs.drop(columns=["31013", "31014", "31023", "31024"])
    if _debut_time < pd.to_datetime("2020-11-01 08:00:00"): # ch8
        _upgrade_costs = _upgrade_costs.drop(columns=["31033", "31034", "30145"])
    if _debut_time < pd.to_datetime("2021-09-17 08:00:00"): # ch9
        _upgrade_costs = _upgrade_costs.drop(columns=["31043", "31044", "31053", "31054"])

    _sanity_values = calc.get_sanity_values(_debut_time, _upgrade_costs.columns)
    _sanity_costs[_char_name] = _upgrade_costs.to_numpy(na_value=0).dot(_sanity_values)

mastery_costs = (
    pd.DataFrame(_sanity_costs)
      .set_axis([1, 2, 3])
      .reset_index()
      .melt(id_vars="index")
      .set_axis(["Skill", "Operators", "Sanity Cost"], axis=1)
)

sns.set_theme(style="whitegrid",
              context="paper",
              palette=["#fb2c20", "#43c03b", "#3060a8"],
              font_scale=2)
cost_bar = (
    sns.catplot(data=mastery_costs, kind="bar",
                x="Operators", y="Sanity Cost", hue="Skill",
                alpha=.8, height=10, aspect=4)
       .set_xticklabels(rotation=90)
       .set(ylim=(3200, 4800))
)
cost_bar.fig.suptitle("6* Operator Skill Mastery Costs", y=1.01)
cost_bar.savefig("mastery_costs_bar.png", dpi=200)

sns.set_theme(style="whitegrid",
              context="paper")
cost_hist = (
    sns.displot(data=mastery_costs, kind="hist", bins=20,
                x="Sanity Cost",
                color="#52ad9c", alpha=1, aspect=2)
       .despine(left=True)
)
cost_hist.fig.suptitle("6* Operator Skill Mastery Costs", y=1.02)
cost_hist.savefig("mastery_costs_hist.png", dpi=200)
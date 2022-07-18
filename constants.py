CHAR_DEBUT_TIMES_URL = "https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%8A%E7%BA%BF%E6%97%B6%E9%97%B4%E4%B8%80%E8%A7%88"
CHARS_URL = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/character_table.json"
DROPS_URL = "https://penguin-stats.io/PenguinStats/api/v2/result/matrix"
STAGES_URL = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/stage_table.json"
RECIPES_URL = "https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/building_data.json"
MIN_RUN_THRESHOLD = 100
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
MISSING_STAGE_COSTS = {
    "a003_f03": 15, # OF-F3
    "a003_f04": 18, # OF-F4
}
LMD_SANITY_VALUE = 36/10000 # sanity:LMD ratio of CE-6 
# the sanity value is 30/7500 (CE-5) before 2022-05-01 08:00:00 GMT, but LMD is an insignificant factor anyway
BYPRODUCT_RATE_BONUS = 1.8
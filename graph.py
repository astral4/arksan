from constants import *
import pandas as pd
import dateparser
import requests

char_debut_times = (
    pd.read_html(CHAR_DEBUT_TIMES_URL,
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .set_index("干员")
      .query("稀有度 == 6")
      .drop(columns=["稀有度", "国服上线途径", "主要获得方式", "干员预告"])
)

chars = (
    requests.get(CHARS_URL)
            .json()
            .values()
)
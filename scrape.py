from constants import *
import pandas as pd
import dateparser

char_debut_dates = (
    pd.read_html(OPERATOR_URL,
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .set_index("干员")
      .drop(columns=["国服上线途径", "主要获得方式", "干员预告"])
)
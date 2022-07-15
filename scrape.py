from constants import *
import pandas as pd
import dateparser

char_debut_dates = (
    pd.read_html(OPERATOR_URL,
                 converters={"国服上线时间": dateparser.parse})
      [0]
      .set_index("干员")
)
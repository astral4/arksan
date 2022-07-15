from constants import *
import pandas as pd
import dateparser

df = pd.read_html(OPERATOR_URL, converters={"国服上线时间": dateparser.parse})[0]

print(df)
from constants import *
import requests
import pandas as pd

drop_matrix = requests.get("https://penguin-stats.io/PenguinStats/api/v2/result/matrix").json()

drop_data = (
    pd.json_normalize(drop_matrix, ["matrix"])
      .drop(["stdDev", "start", "end"], axis=1)
      .pipe(lambda df: df[df["times"] >= MIN_RUN_THRESHOLD])
)
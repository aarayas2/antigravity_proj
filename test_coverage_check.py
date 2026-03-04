import pandas as pd
import numpy as np

dates = pd.date_range(start="2023-01-01", periods=30)
closes = np.full(30, 100.0)
closes = closes + np.random.normal(0, 1, 30)

df = pd.DataFrame({'Close': closes}, index=dates)

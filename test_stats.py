import json
import os

data = [
    {
        "AAPL": {
            "date-begin": "2020-01-01",
            "date-end": "2024-01-01",
            "SMA": {
                "Total Return": "20%",
                "Average Return": "5%",
                "Number of Trades": 10,
                "Win Rate": "60%"
            },
            "BollingerBands": {
                "Total Return": "10%",
                "Average Return": "2%",
                "Number of Trades": 5,
                "Win Rate": "40%"
            }
        }
    }
]

os.makedirs('stock-analysis/data', exist_ok=True)
with open('stock-analysis/data/stats.json', 'w') as f:
    json.dump(data, f)


import json
import os

def migrate(file_path='stock_analysis/data/stats.json'):
    if not os.path.exists(file_path):
        print(f"Stats file not found at {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for entry in data:
        for ticker, stats in entry.items():
            for strategy, metrics in stats.items():
                if strategy in ['date-begin', 'date-end']:
                    continue
                
                for key in ['Total Return', 'Average Return', 'Win Rate']:
                    if key in metrics and isinstance(metrics[key], str):
                        try:
                            # Convert from "XX.XX%" to 0.XXXX
                            val = float(metrics[key].strip('%')) / 100.0
                            metrics[key] = round(val, 4)
                        except ValueError:
                            metrics[key] = 0.0

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Migration complete. stats.json updated with raw floats.")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'stock_analysis/data/stats.json'
    migrate(path)

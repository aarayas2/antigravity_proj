import subprocess
import sys
import os

def main():
    cmd = [
        sys.executable, "-m", "pytest", "stock-analysis/tests/test_trade_visuals.py",
        "--cov=trade_visuals", "--cov-report=term-missing"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "stock-analysis"
    subprocess.run(cmd, env=env)

if __name__ == '__main__':
    main()

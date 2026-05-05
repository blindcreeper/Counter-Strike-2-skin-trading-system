import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auto_tuner import AutoTuner
from backtest_db import BacktestDatabase
from run_backtest import CompleteBacktestSystem


def run_auto_tune(trials=12, hours_back=72, initial_balance=10000):
    system = CompleteBacktestSystem()
    db = BacktestDatabase()
    tuner = AutoTuner(system, db)
    result = tuner.tune(trials=trials, hours_back=hours_back, initial_balance=initial_balance)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result


if __name__ == "__main__":
    run_auto_tune()

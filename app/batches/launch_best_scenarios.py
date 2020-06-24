# -*- coding: utf-8 -*-


import app.dashboard.DBHandler as DBHandler
import sys

from app.config.env_func import reset_db_name

if __name__ == "__main__":
    quantile_step = 1 if len(sys.argv) < 2 else float(sys.argv[1])
    db_name = "mine2farm"
    if len(sys.argv) > 1:
        db_name = sys.argv[2]
    reset_db_name(db_name)
    DBHandler.get_best_scenarios(quantile_step, db_name)

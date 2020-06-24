# -*- coding: utf-8 -*-
from app.config.env_func import reset_db_name
from app.server.SimulationWorker import SimulationWorker
import sys


if __name__ == "__main__":
    db_name = "mine2farm"
    options_len = len(sys.argv)
    if options_len > 1:
        db_name = sys.argv[1]
    reset_db_name(db_name)
    worker = SimulationWorker()
    worker.consume()

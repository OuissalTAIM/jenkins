# -*- coding: utf-8 -*-
from app.config.env_func import reset_db_name
from app.data.DBAccess import DBAccess
from app.model.Simulator import *
import cProfile
from multiprocessing import Pool, TimeoutError, Process
from app.data.DBAccess import DBAccess
from flask import Response, render_template


def simulate(cycle=1, phase=0, use_db=False):
    if use_db:
        db = DBAccess(env.DB_RESULT_NAME)
        db.clear_collection(env.DB_GLOBAL_RESULT_COLLECTION_NAME)
        db.clear_collection(env.DB_DETAILED_RESULT_COLLECTION_NAME)
    scenarios_global, scenarios_details = Simulator().simulate(cycle, phase, logistics_lp=False)
    if use_db:
        for scenario in scenarios_global:
            db.save_to_db_no_check(env.DB_GLOBAL_RESULT_COLLECTION_NAME, scenarios_global[scenario])

        for scenario in scenarios_details:
            json_data = json.dumps(NodeJSONEncoder().encode(scenarios_details[scenario]))
            data = json.loads(json.loads(json_data))
            db.save_to_db_no_check(env.DB_DETAILED_RESULT_COLLECTION_NAME, data)



if __name__ == "__main__":
    #cProfile.run('simulate(1, 0)')
    reset_db_name("mine2farm")
    simulate()
    #results = s.simulate()
    # for i in results:
    #     results[i].to_csv("%app/samples/output/scenario_%.csv" % (APP_FOLDER, i), index=None, header=True)

    # cycle = 4
    # for num in range(cycle):
    #     Process(target=simulate, args=(cycle, num)).start()
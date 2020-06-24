# -*- coding: utf-8 -*-


import datetime
from bson import ObjectId
from app.config.env_func import reset_db_name
from app.data.DBAccess import DBAccess
import app.config.env as env
from pymongo import DESCENDING
from app.data.Client import Driver
from app.graph.Node import NodeJSONEncoder
from app.model.Simulator import Simulator
from app.risk.RiskEngine import RiskEngine
from tqdm import tqdm
import pandas as pd
from app.server.ClientMemcached import update_cache, delete_cache
import json
from collections import defaultdict
import app.tools.Utils as Utils
from app.tools.Logger import logger_best as logger


def get_best_global_scenarios(quantile_step):
    db = DBAccess(env.DB_RESULT_NAME)
    db.clear_collection(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME)

    scenarios = db.get_records(
        env.DB_GLOBAL_RESULT_COLLECTION_NAME,
        {}
    ).sort([("Cost PV", DESCENDING)])
    step = int(quantile_step*scenarios.count())
    representative_scenarios = [scenarios.skip(step*i)[0] for i in range(0, int(scenarios.count()/step))]
    db.save_to_db_no_check(env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME, representative_scenarios)


def get_best_detailed_scenarios(quantile_step):
    db = DBAccess(env.DB_RESULT_NAME)
    db.clear_collection(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME)

    scenarios = db.get_fields(
        env.DB_GLOBAL_RESULT_COLLECTION_NAME,
        {"Cost PV": 1, "Scenario": 1},
        [("Cost PV", DESCENDING)]
    )
    step = int(quantile_step*scenarios.count())
    points = [scenarios.skip(step*i)[0]["Scenario"] for i in range(0, int(scenarios.count()/step))]
    representative_scenarios = db.get_records(env.DB_DETAILED_RESULT_COLLECTION_NAME,
                                                   {"Scenario": {"$in": points}})
    db.save_to_db_no_check(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME, representative_scenarios)


def get_best_scenarios(quantile_step, db_name="mine2farm"):
    update_cache(db_name, -1)
    try:
        time_start = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")

        # insert status of best scenarios "running"
        db_history = DBAccess(env.MONITORING_DB_NAME)
        query_insert = {'time_start': time_start, 'db_name': db_name, 'quantile_step': quantile_step, 'status': -1}
        _id = db_history.save_to_db_no_check(env.MONITORING_COLLECTION_HISTORY_BEST_NAME, query_insert)

        # get best representative scenarios
        quantile_step = quantile_step / 100.
        reset_db_name(db_name)
        db = DBAccess(env.DB_RESULT_NAME)
        logger.info("Deleting best collections from DB")
        db.clear_collection(env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME)
        db.clear_collection(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME)
        scenarios = db.get_records(
            env.DB_GLOBAL_RESULT_COLLECTION_NAME,
            {}
        ).sort([("Cost PV", DESCENDING)])

        scenarios_count = scenarios.count()
        step = int(quantile_step * scenarios_count)
        # save to db
        if step == 0:
            # all scenarios are concerned
            logger.info("Moving all scenarios to best collections")
            db.copy_to_collection(env.DB_GLOBAL_RESULT_COLLECTION_NAME, env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME)
            db.copy_to_collection(env.DB_DETAILED_RESULT_COLLECTION_NAME, env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME)
            details_count = db.count(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME)
        else:
            # filter on specific scenarios
            representative_scenario_ids = [
                scenarios.skip(step*i)[0]["Scenario"] for i in range(0, int(scenarios_count/step))
            ]
            logger.info("List of selected best scenarios: %s" % representative_scenario_ids)
            # simulate
            scenarios_global, scenarios_details = \
                Simulator().simulate(scenarios_filter=representative_scenario_ids, logistics_lp=env.LOGISTICS_LP)
            # save
            for scenario in scenarios_global:
                db.save_to_db_no_check(env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME, scenarios_global[scenario])
            for scenario in scenarios_details:
                json_data = json.dumps(NodeJSONEncoder().encode(scenarios_details[scenario]))
                data = json.loads(json.loads(json_data))
                db.save_to_db_no_check(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME, data)
            details_count = len(scenarios_details)

        # status update
        query_insert['global_count'] = scenarios_count
        query_insert['detailed_count'] = details_count
        filter_ = {'_id': ObjectId(_id)}
        db_history.update_record(collection=env.MONITORING_COLLECTION_HISTORY_BEST_NAME,
                                 filter_=filter_, data=query_insert)

        # raw materials sensitivities
        logger.info("Running sensitivity over raw materials")
        db.clear_collection(env.DB_SENSITIVITY_COLLECTION_NAME)
        raw_materials_df = Driver().get_data("raw_materials")
        shocks = {}
        for raw_material in raw_materials_df:
            item = raw_material["Item"]
            shocks[item] = 1
        scenarios_df = pd.DataFrame(Driver().get_results(env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME))
        scenarios_dic = Utils.get_scenario_from_df(scenarios_df)
        risk_engine = RiskEngine()

        for scenario_id in scenarios_dic:
            deltas = risk_engine.compute_delta(scenarios_dic[scenario_id], shocks, with_logistics=env.LOGISTICS_LP)

            deltas['Scenario'] = int(scenario_id)
            db.save_to_db_no_check(env.DB_SENSITIVITY_COLLECTION_NAME, deltas)

        # status update
        query_insert['time_end'] = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
        query_insert['status'] = 0
        filter_ = {'_id': ObjectId(_id)}
        db_history.update_record(collection=env.MONITORING_COLLECTION_HISTORY_BEST_NAME, filter_=filter_, data=query_insert)
        update_cache(db_name, 0)

    except Exception as e:
        logger.error("Best scenarios failed")
        update_cache(db_name, 0)


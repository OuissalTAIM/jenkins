# -*- coding: utf-8 -*-


from app.config.env_func import reset_db_name
from app.config.env import DB_SENSITIVITY_COLLECTION_NAME
from app.data.DBAccess import DBAccess
import pandas as pd
import app.config.env as env
from app.data.Client import Driver
from app.risk.RiskEngine import RiskEngine
from tqdm import tqdm
import json
from app.tools import Utils

if __name__ == "__main__":
    reset_db_name('mine2farm')
    db = DBAccess(env.DB_RESULT_NAME)
    db.clear_collection(DB_SENSITIVITY_COLLECTION_NAME)
    raw_materials_sensitivity = []
    raw_materials_df = Driver().get_data("raw_materials")
    shocks = {}
    for raw_material in raw_materials_df:
        item = raw_material["Item"]
        shocks[item] = 1
    #scenarios_df = pd.DataFrame(Driver().get_results(DB_GLOBAL_BEST_RESULT_COLLECTION_NAME))
    scenarios_df = pd.read_csv(env.APP_FOLDER + "outputs/global.csv")
    scenarios_dic = Utils.get_scenario_from_df(scenarios_df)
    for scenario_id in scenarios_dic:
        risk_engine = RiskEngine()
        deltas = risk_engine.compute_delta(scenarios_dic[scenario_id], shocks)
        deltas['Scenario'] = int(scenario_id)
        db.save_to_db_no_check(DB_SENSITIVITY_COLLECTION_NAME, deltas)

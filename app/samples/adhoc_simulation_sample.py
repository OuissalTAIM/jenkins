# -*- coding: utf-8 -*-


import pandas as pd
import app.config.env as env
from app.config.env_func import reset_db_name
from app.tools import Utils
from app.data.DataManager import DataManager
from app.model.Simulator import Simulator
from app.model.ScenarioGenerator import ScenarioGeneratorFactory as SGF


if __name__ == "__main__":
    reset_db_name("mine2farm")
    scenarios_df = pd.read_csv(env.APP_FOLDER + "outputs/global.csv")
    scenarios_dic = Utils.get_scenario_from_df(scenarios_df)
    dm = DataManager()
    dm.load_data()
    for scenario_id in scenarios_dic:
        scenario = scenarios_dic[scenario_id]
        simulator = Simulator(dm=dm, monikers_filter=sum(scenario, []))
        scenarios = [
            simulator.nodes[layer] for layer in [
                env.PipelineLayer.PAP, env.PipelineLayer.SAP,
                env.PipelineLayer.BENEFICIATION, env.PipelineLayer.MINE, env.PipelineLayer.MINE_BENEFICIATION
            ] if layer in simulator.nodes
        ]
        scenario_generator = SGF.create_scenario_generator(env.ScenarioGeneratorType.SPECIFIC_SCENARIOS, simulator,
                                                           [scenarios])
        result, _ = simulator.simulate(scenario_generator=scenario_generator)
        print("Cost PV: %f" % result[1]["Cost PV"])

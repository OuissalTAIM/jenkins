# -*- coding: utf-8 -*-


import unittest
import pandas as pd
import time

from app.config import env
from app.config.env import ScenarioGeneratorType, PipelineLayer
from app.config.env_func import reset_db_name
from app.data.Client import Driver
from app.data.DataManager import DataManager
from app.model.Simulator import Simulator
from app.risk.RiskEngine import RiskEngine
from app.tools import Utils
from app.model.ScenarioGenerator import ScenarioGeneratorFactory as SGF


reset_db_name("mine2farm")
dm = DataManager()
dm.load_data()


class PricingTestSuite(unittest.TestCase):
    """Pricing test cases."""
    def __init__(self, *args, **kwargs):
        super(PricingTestSuite, self).__init__(*args, **kwargs)
        scenarios_df = pd.read_csv(env.APP_FOLDER + "tests/data/one_scenario.csv")
        self.scenarios_dic = Utils.get_scenario_from_df(scenarios_df)
        scenario_id = 1
        self.simulator = Simulator(dm=dm, monikers_filter=sum(self.scenarios_dic[scenario_id], []))
        scenarios = [
            self.simulator.nodes[layer] for layer in [
                PipelineLayer.PAP, PipelineLayer.SAP,
                PipelineLayer.BENEFICIATION, PipelineLayer.MINE, PipelineLayer.MINE_BENEFICIATION
            ] if layer in self.simulator.nodes
        ]
        self.scenario_generator = SGF.create_scenario_generator(ScenarioGeneratorType.SPECIFIC_SCENARIOS,
                                                                self.simulator, [scenarios])

    def test_pricing(self):
        result, _ = self.simulator.simulate(scenario_generator=self.scenario_generator)
        self.assertTrue(result[1]["Cost PV"] == 12057687291.92442)


    def test_twice(self):
        self.test_pricing()
        self.test_pricing()


    def test_timing(self):
        start = time.process_time()
        for _ in range(100):
            self.simulator.simulate(scenario_generator=self.scenario_generator)
        delta = time.process_time() - start
        self.assertTrue(delta < 10)


    def test_sensitivity(self):
        raw_materials_df = Driver().get_data("raw_materials")
        shocks = {}
        for raw_material in raw_materials_df:
            item = raw_material["Item"]
            shocks[item] = 1
        scenario_id = 1
        risk_engine = RiskEngine()
        deltas = risk_engine.compute_delta(self.scenarios_dic[scenario_id], shocks)
        expected_res = {
            'HNO3': 0.0,
            'ACS': 146849.90380477905,
            'HCl': 0.0,
            'Raw water': 2185043.1382694244,
            'Electricity': 261000787.2892666,
            'K09': 0.0,
            'Rock': 0.0
        }
        self.assertTrue(deltas == expected_res)


if __name__ == '__main__':
    unittest.main()
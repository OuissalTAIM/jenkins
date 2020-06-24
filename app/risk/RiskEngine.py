# -*- coding: utf-8 -*-


from app.data.DataManager import DataManager
from app.model.Simulator import Simulator
from app.data.Client import Driver
from app.tools.Logger import logger_sensitivity as logger
from app.model.ScenarioGenerator import ScenarioGeneratorFactory as SGF
from app.config.env import ScenarioGeneratorType, PipelineLayer


class RiskEngine:
    """
    Risk sensitivity class
    """

    def __init__(self):
        """
        ctor
        """
        self.dm = DataManager()
        self.dm.load_data()

    def compute_delta(self, scenario, shocks, with_logistics=False):
        # base scenario
        simulator = Simulator(dm=self.dm, monikers_filter=sum(scenario, []))
        scenarios = [
            simulator.nodes[layer] for layer in [
                PipelineLayer.PAP, PipelineLayer.SAP,
                PipelineLayer.BENEFICIATION, PipelineLayer.MINE, PipelineLayer.MINE_BENEFICIATION
            ] if layer in simulator.nodes
        ]
        scenario_generator = SGF.create_scenario_generator(ScenarioGeneratorType.SPECIFIC_SCENARIOS, simulator,
                                                           [scenarios])
        result_no_bump, _ = simulator.simulate(scenario_generator=scenario_generator, logistics_lp=with_logistics)
        logger.info("Base: %f" % result_no_bump[1]["Cost PV"])

        # bump data
        result_with_bump = {}
        raw_materials_df = Driver().get_data("raw_materials")
        for raw_material in raw_materials_df:
            item = raw_material["Item"]
            if item not in shocks:
                continue
            unit = raw_material["Unit"]
            currency = unit.split("/")[0]
            # bump
            self.dm.bump_raw_materials({item: shocks[item]})
            bumped_simulator = Simulator(dm=self.dm, monikers_filter=sum(scenario, []))
            bumped_scenarios = [
                bumped_simulator.nodes[layer] for layer in [
                    PipelineLayer.PAP, PipelineLayer.SAP,
                    PipelineLayer.BENEFICIATION, PipelineLayer.MINE, PipelineLayer.MINE_BENEFICIATION
                ] if layer in bumped_simulator.nodes
            ]
            scenario_generator = SGF.create_scenario_generator(ScenarioGeneratorType.SPECIFIC_SCENARIOS, bumped_simulator,
                                                               [bumped_scenarios])
            result_with_bump[item], _ = bumped_simulator.simulate(scenario_generator=scenario_generator)
            logger.info("Shock %s by %s%f: %f" % (item, currency, shocks[item], result_with_bump[item][1]["Cost PV"]))
            # reset
            self.dm.bump_raw_materials({item: -shocks[item]})

        # deltas
        base_price = result_no_bump[1]["Cost PV"]
        deltas = {}
        for item in result_with_bump:
            deltas[item] = result_with_bump[item][1]["Cost PV"] - base_price
        return deltas

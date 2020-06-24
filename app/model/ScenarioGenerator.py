# -*- coding: utf-8 -*-
import itertools

from app.model.Scenario import *
from app.entity.Entity import *


class ScenarioGeneratorFactory:
    """
    Scenario generator factory
    """
    @staticmethod
    def create_scenario_generator(type, simulator, scenarios=[]):
        """
        Factory method for scenario generators
        :param type: ScenarioGeneratorType
        :param simulator: Simulator
        :param scenarios: list
        :return: generator class
        """
        if type == env.ScenarioGeneratorType.FROM_PATHS:
            scenario_generator = ScenarioGeneratorFromPaths(simulator.graph, simulator.nodes)
        elif type == env.ScenarioGeneratorType.FROM_OPTIONS:
            scenario_generator = ScenarioGeneratorFromOption(simulator.layers)
        elif type == env.ScenarioGeneratorType.SPECIFIC_SCENARIOS:
            scenario_generator = SimpleGenerator(scenarios)
        else:
            logger.error("Scenario generator %s is not implemented" % type)
            raise Exception("Unimplemented generator %s" % type)
        return scenario_generator


class SimpleGenerator:
    """
    Class handling generators of collections
    """
    def __init__(self, scenarios):
        """
        ctor
        :param scenarios: collection
        """
        self.scenarios = scenarios

    def len(self):
        """
        # of scenarios
        :return: integer
        """
        return len(self.scenarios)

    def generate(self):
        """
        Generate all scenarios
        :return: iterator on all scenarios
        """
        for scenario in self.scenarios:
            yield scenario


class ScenarioGeneratorFromPaths:
    """
    Class handling path based scenarios
    """
    def __init__(self, graph, layer_nodes):
        """
        ctor
        :param graph: graph of nodes
        :param layer_nodes: dictionary of nodes per layer
        """
        (departure_layer, arrival_layer) = env.DEPARTURE_ARRIVAL[env.SUPPLY_CHAIN]
        departures = []
        for departure in layer_nodes[departure_layer]:
            departures.append(departure.moniker())
        arrivals = []
        for arrival in layer_nodes[arrival_layer]:
            arrivals.append(arrival.moniker())
            supplychain_paths = []
            for departure in departures:
                for arrival in arrivals:
                    da_paths = graph.paths(departure, arrival)
            if len(da_paths) > 0:
                supplychain_paths.extend(da_paths)
        logger.info("Number of paths: %d" % len(supplychain_paths))
        self.paths = supplychain_paths

    def len(self):
        """
        # of scenarios
        :return: integer
        """
        return 2 ** len(self.paths) - 1

    def generate(self):
        """
        Generate all scenarios
        :return: iterator on all scenarios
        """
        len_paths = self.len() + 1
        masks = ['{{0:0{0}b}}'.format(len_paths).format(n) for n in range(0, len_paths)]
        for mask in masks:
            scenario = []
            for i in range(0, len_paths):
                if mask[i] == '1':
                    scenario.append(self.paths[i])
            if scenario == []:
                continue
            yield ScenarioFromPath(scenario)


class ScenarioGeneratorFromOption:
    """
    Class handling options based scenarios
    """
    def __init__(self, layers):
        """
        ctor
        :param layers: dictionary of layers
        """
        layer_combinations = {}
        self.length = 1
        for layer_type in layers:
            if layer_type in [env.PipelineLayer.LOGISTICS, env.PipelineLayer.GRANULATION]:
                continue
            layer = layers[layer_type]
            combinations = layer.shuffle()
            layer_combinations[layer_type] = combinations
        sub_scenarios_pap_sap_only = itertools.product(*[layer_combinations[env.PipelineLayer.SAP], layer_combinations[env.PipelineLayer.PAP]])
        valid_scenarios_sap_pap_wise = ScenarioGeneratorFromOption.filter_over_sap_pap_locations(sub_scenarios_pap_sap_only)
        scenarios = itertools.product(*[valid_scenarios_sap_pap_wise,
                                        layer_combinations[env.PipelineLayer.MINE_BENEFICIATION]])
        self.combinations = [[comb[0][1]]+[comb[0][0]] + list(comb[1:]) for comb in scenarios]
        self.length = len(self.combinations)
        logger.info("Number of scenarios: %d" % self.length)

    @staticmethod
    def filter_over_sap_pap_locations(scenarios):
        valid_scenarios_sap_pap_wise = list()
        for scenario in scenarios:
            """ Ensuring that all valid scenarios have acp and sap lines in the same location."""
            sap = ScenarioGeneratorFromOption.get_scenario_subpart(scenario, env.PipelineLayer.SAP)
            pap = ScenarioGeneratorFromOption.get_scenario_subpart(scenario, env.PipelineLayer.PAP)

            # Section to check whether existing sap sites have corresponding pap sites
            pap_monikers = [pap_.moniker() for pap_ in pap]
            saps_with_associated_pap = [node for node in sap if pd.isna(node.entity.associated_pap) is False]
            existing_units_coherence = False not in set(sap_with_associated_pap.entity.associated_pap in pap_monikers
                                                        for sap_with_associated_pap in saps_with_associated_pap)

            if pap[-1].entity.location == sap[-1].entity.location and existing_units_coherence:
                valid_scenarios_sap_pap_wise.append(scenario)
        return valid_scenarios_sap_pap_wise

    @staticmethod
    def get_scenario_subpart(scenario, reference_layer):
        for layer in scenario:
            if layer[0].entity.layer == reference_layer:
                return layer

    def len(self):
        """
        # of scenarios
        :return: integer
        """
        return self.length

    def generate(self):
        """
        Generate all scenarios
        :return: iterator on all scenarios
        """
        return self.combinations

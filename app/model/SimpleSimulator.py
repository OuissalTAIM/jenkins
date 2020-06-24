# -*- coding: utf-8 -*-


from app.graph.Graph import *
from app.data.Client import Driver
from app.config.env import MONIKER_SEPARATOR
from app.entity.Transport import Transport
from app.samples.graph_sample import SimpleEntity


class SimpleSimulator:
    def __init__(self, graph):
        """
        Constructor
        :param graph: input graph
        """
        self.graph = graph

    def build_graph(self):
        """
        Get data from data service and build graph
        :return: None
        """
        # get locations
        locations = Driver.get_data("simplelocation")
        unit_locations = {}
        for location in locations:
            for key in location:
                if key not in unit_locations:
                    unit_locations[key] = []
                unit_locations[key].append(location[key])

        # get infrastructure
        infrastructure = Driver.get_data("infrastructure")

        # get connections
        connections = Driver.get_data("connection")
        upstream_to_downstream_connection = {}
        for connection in connections:
            #TODO: could the headers "From" and "To" be dynamic?
            # at least the unit in "Distance[km]" should be
            upstream_to_downstream_connection[(connection["From"],connection["To"])] = connection["Distance[km]"]

        # build graph
        nodes = {}
        for unit_location in unit_locations:
            if unit_location == "_id":
                continue
            for location in unit_locations[unit_location]:
                if location is None:
                    continue
                key = unit_location + MONIKER_SEPARATOR + location
                entity = SimpleEntity(key, 1, 1, 1)
                node = Node(entity)
                nodes[key] = node

        # upstream to downstream
        network = Network("CenterAxe")
        for node_key in nodes:
            node = nodes[node_key]
            has_downstream = False
            for up_down in upstream_to_downstream_connection:
                if node_key != up_down[0]:
                    continue
                from_to = up_down[1].split(MONIKER_SEPARATOR)
                if from_to[1] not in unit_locations[from_to[0]]:
                    continue
                distance = upstream_to_downstream_connection[up_down]
                for infra in infrastructure:
                    transport = Transport(infra, distance)
                    node.add_downstream(transport, up_down[1])
                    network.add_node(nodes[up_down[1]])
                    has_downstream = True
            if has_downstream:
                network.add_node(node)
        self.graph = Graph(network)

    def build_all_scenarios(self, start, end):
        """
        Brute force simulation
        :param start: list of starting points
        :param end: list of ending points
        :return: list
        """
        paths = []
        for s in start:
            for e in end:
                se_paths = self.graph.paths(s, e)
                if len(se_paths) > 0:
                    paths.extend(se_paths)
        len_paths = len(paths)
        masks = ['{{0:0{0}b}}'.format(len_paths).format(n) for n in range(0, 2 ** len_paths)]
        scenarios = []
        for mask in masks:
            scenario = []
            scenario_names = []
            for i in range(0, len_paths):
                if mask[i] == '1':
                    scenario.append(paths[i])
            print(scenario)
            scenarios.append(scenario)
        return scenarios

    def compute(self):
        """
        TODO: iterate over all scenarios and compute cost-pv
        and other metrics
        :return: dictionary
        """
        scenarios = self.build_all_scenarios()
        for scenario in scenarios:
            self.compute(scenario)
        return {}

    def simulate(self, scenario, plot=False, function="cost_pv"):
        """
        Apply function on scenario
        :param scenario: list[[string]]
        :param plot: boolean, choose to plot the graph or not
        :return: Result object
        """
        scenario_result = []
        for path in scenario:
            result = []
            next_node = None
            path.reverse()
            path_to_nodes = [self.graph.get_node(name) for name in path]
            for node in path_to_nodes:
                result.append(getattr(node, function)(next_node))
                next_node = node
            path.reverse()
            result.reverse()
            print("%s | %s" % (path, result))
            scenario_result.append(result)
        if plot:
            self.graph.plot()
        return scenario_result

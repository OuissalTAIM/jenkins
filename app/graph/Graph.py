# -*- coding: utf-8 -*-


import networkx as nx

class Edge:
    """
    An edge is a directed arrow from one entity to another
    """

    def __init__(self, transport, s_entity, e_entity):
        """
        ctor
        :param transport: mean of transport
        :param s_entity: start
        :param e_entity: end
        """
        self.transport = transport
        self.start = s_entity
        self.end = e_entity

    def cost(self):
        """
        Transport cost PV
        :return: double
        """
        return self.transport.cost()


class Network:
    """
    Network of nodes
    """

    def __init__(self, name):
        """
        ctor
        :param name: string
        """
        self.name = name
        self.nodes = {}

    def add_node(self, node):
        """
        Add node to network only if node was not added previously
        :param node: Node object
        :return: None
        """
        #TODO: replace node name by moniker as a unique identifier
        if node.name() not in self.nodes:
            self.nodes[node.moniker()] = node

    def add_layer(self, layer):
        """
        Add all nodes in layer
        :param layer: Layer object
        :return: None
        """
        for node in layer.nodes:
            self.add_node(node)

    def get_node(self, name):
        """
        Get node from network
        :param name: string
        :return: Node
        """
        if name not in self.nodes:
            raise Exception("Node {0} is not part of the network".format(name))
        return self.nodes[name]


class Graph:
    """
    Graph of all nodes and edges
    """

    def __init__(self, network):
        """
        ctor
        :param network: Network object
        """
        self.network = network

    def get_node(self, name):
        """
        Get node
        :param name: string
        :return: Node object
        """
        return self.network.get_node(name)

    def get_downstream_nodes(self, node):
        """
        Get list of downstream nodes
        :param node: Node object
        :return: list[Node]
        """
        [self.network.get_node(node.downstream[ds_name].end.name) for ds_name in node.downstream]

    def find_path(self, from_name, to_name):
        """
        Find a path between 2 nodes
        :param from_name: string
        :param to_name: string
        :return: list[string]
        """
        if from_name == to_name:
            return [to_name]
        from_node = self.network.get_node(from_name)
        ds_nodes = self.get_downstream_nodes(from_node)
        if ds_nodes == []:
            return []
        for ds_node in ds_nodes:
            path = self.find_path(ds_node.name(), to_name)
            if path == []:
                continue
            path.append(from_name)


    def paths(self, start, end):
        """
        Find all possible paths
        :param start: node name
        :param end: node name
        :return: list[list[string]]
        """
        s_node = self.network.get_node(start)
        e_node = self.network.get_node(end)
        if s_node.layer() > e_node.layer():
            raise Exception("Cannot walk back from node {0} to node {1}".format(start, end))
        return self.find_paths(s_node, end, [])

    def find_paths(self, from_node, to_moniker, path):
        """
        Find all paths between 2 nodes
        :param from_node: Node
        :param to_name: string
        :param path: list
        :return: list[list[string]]
        """
        from_moniker = from_node.moniker()
        path = path + [from_node]
        if from_moniker == to_moniker:
            return [path]
        if len(from_node.downstream) == 0:
            return []
        ds_nodes = (self.network.get_node(from_node.downstream[ds_moniker].end.moniker) for ds_moniker in from_node.downstream)
        paths = []
        for ds_node in ds_nodes:
            paths_tmp = self.find_paths(ds_node, to_moniker, path)
            if len(paths_tmp) == 0:
                continue
            for path_tmp in paths_tmp:
                paths.append(path_tmp)
        return paths

    def apply_function(self, from_name, to_name, function):
        """
        Apply function on all possible paths between 2 nodes
        and cumulate results
        :param from_name: string
        :param to_name: string
        :param function: Node function name
        :return: double
        """
        paths = self.paths(from_name, to_name)
        for path in paths:
            result = []
            next_node = None
            path.reverse()
            for node in path:
                result.append(getattr(node, function)(next_node))
                next_node = node
            print("%s | %s" % (path, result))

    def plot(self):
        """
        Plot graph
        :return: Viz
        """
        g = nx.Graph()
        g.add_nodes_from(self.network.nodes.keys())
        for node_name in self.network.nodes:
            node = self.network.nodes[node_name]
            for ds_node_name in node.downstream:
                g.add_edge(node_name, ds_node_name)
        nx.draw(g, with_labels=True, pos=nx.planar_layout(g))
        plt.show()

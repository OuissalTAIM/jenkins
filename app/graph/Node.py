# -*- coding: utf-8 -*-


from app.entity.MineBeneficiation import *
import json
import pandas as pd

from app.graph.Graph import Edge


class NodeJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Node):
            return o.moniker()
        if isinstance(o, pd.core.series.Series):
            return o.to_dict()
        return json.JSONEncoder.default(self, o)


class Node:
    """
    A node is an entity and its upstreams/downstreams
    """

    def __init__(self, entity):
        """
        ctor
        :param entity: Entity
        """
        self.entity = entity
        self.upstream = {}
        self.downstream = {}

    def __repr__(self):
        """
        Node representation
        :return: string
        """
        return self.moniker()

    def __str__(self):
        """
        Stringify
        :return: dict
        """
        return self.moniker()

    def name(self):
        """
        Primary entity name
        :return: string
        """
        return self.entity.name

    def location(self):
        return self.entity.location

    def nominal_capacity(self):
        return self.entity.nominal_capacity

    def moniker(self):
        """
        Primary moniker
        :return: string
        """
        return self.entity.moniker

    def layer(self):
        """
        Layer enumeration
        :return: Enum
        """
        return self.entity.layer

    def add_downstream(self, transport, entity_id):
        """
        Connect to downstream
        :param transport: mean of transport
        :param entity_id: identifier of entity
        :return: None
        """
        if entity_id not in Entity.ENTITIES:
            raise Exception("Downstream entity {0} does not exist".format(entity_id))

        ds_entity = Entity.ENTITIES[entity_id]
        if entity_id in self.downstream and self.downstream[entity_id].transport == transport:
            raise Exception("Downstream entity {0} via {1} already exists with node {2}".format(entity_id, transport, self.name()))

        self.downstream[entity_id] = Edge(transport, self.entity, ds_entity)

    def cost_pv(self, downstream_node=None):
        """
        Cost PV including transport
        :param downstream_node: destination node
        :return: double
        """
        if downstream_node is None:
            return self.entity.cost_pv()
        edge = self.downstream[downstream_node.moniker()]
        #TODO: make sure that edge.cost() is in same unit as volume,
        # rework this code
        transport_cost = edge.cost() * self.entity.volume()
        cost = self.entity.cost_pv()
        cost["transport"] = (transport_cost.unit, transport_cost.value)
        return cost


class ComboNode(Node):
    """
    Node combining 2 nodes
    """
    def __init__(self, layer, up_node, down_node):
        """
        ctor
        :param layer: PipelineLayer
        :param up_node: Node
        :param down_node: Node
        """
        self.layer = layer
        self.up_node = up_node
        self.down_node = down_node
        if layer == env.PipelineLayer.MINE_BENEFICIATION:
            self.entity = MineBeneficiationEntity(self.up_node.entity, self.down_node.entity)
        else:
            name = "%s%s%s" % (up_node.name(), env.COMBO_NODES_SEPARATION, down_node.name())
            moniker = "%s%s%s" % (up_node.moniker(), env.COMBO_NODES_SEPARATION, down_node.moniker())
            self.entity = Entity(name=name, layer=layer, id=moniker)

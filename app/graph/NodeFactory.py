# -*- coding: utf-8 -*-

from copy import deepcopy
from app.graph.Node import Node, MineBeneficiationEntity
from app.graph.Layer import Layer, ComboLayer
from app.config.env import *
from app.entity.Mine import *
from app.entity.Beneficiation import *
from app.entity.SAP import *
from app.entity.PAP import *
from app.entity.Granulation import *
from app.entity.Logistics import *
from app.data.Client import Driver
from collections import defaultdict


class NodeFactory:

    layer_entities_referential = {PipelineLayer.MINE: MineEntity,
                                  PipelineLayer.BENEFICIATION: BeneficiationEntity,
                                  PipelineLayer.SAP: SAPEntity,
                                  PipelineLayer.PAP: PAPEntity,
                                  PipelineLayer.GRANULATION: GranulationEntity,
                                  PipelineLayer.LOGISTICS: LogisticsEntity,
                                  PipelineLayer.MINE_BENEFICIATION: MineBeneficiationEntity}
    @staticmethod
    def create_nodes(layer, data, monikers_filter=None):
        nodes = []

        if layer in NodeFactory.layer_entities_referential:
            _, raw_materials, options, spec_prod, spec_cons, capex, product_type = NodeFactory.extract_data(data)
            signature_counter = 0
            if monikers_filter is not None and layer != PipelineLayer.LOGISTICS:
                options_ = options.set_index("Moniker").reindex(monikers_filter).reset_index()
                options = options_[options_["Moniker"].isin(options["Moniker"].tolist())]
            for _, option in options.iterrows():
                entity = NodeFactory.layer_entities_referential[layer](option, spec_cons, capex, spec_prod, raw_materials, product_type)
                if entity.max_number is None:
                    node = Node(entity)
                    nodes.append(node)
                else:
                    entity.signature = signature_counter
                    id_counter = 1
                    for i in range(int(entity.max_number)):
                        e = deepcopy(entity)
                        e.id_number = id_counter
                        e.name = e.location + '/' + str(e.nominal_capacity) + '/NEW' + str(id_counter)
                        tokens = entity.moniker.split(env.MONIKER_SEPARATOR)
                        e.moniker = env.MONIKER_SEPARATOR.join(tokens[:3] + ['NEW' + str(id_counter)] + tokens[4:])
                        Entity.ENTITIES[e.moniker] = e
                        node = Node(e)
                        nodes.append(node)
                        id_counter += 1
                    del Entity.ENTITIES[entity.moniker]
                    signature_counter += 1
        elif layer in [PipelineLayer.RAW_MATERIALS, PipelineLayer.COMMON, PipelineLayer.SALES_PLAN]:
            nodes = []
        else:
            logger.error("Cannot create node in layer %s" % layer)
            raise Exception("Unimplemented method to build nodes in layer %s, data: %s" % (layer, str(data)))

        base_nodes = []
        for node in nodes:
            logger.info("Node %s/%s created" % (layer.name, node.name()))
            if node.entity.status == 'Extension':
                # Specific to mine and benficiation objects. Assuming every entity with status == extension
                # has one and only one corresponding existing or new entity
                base_entities = [iter_node.entity for iter_node in nodes if iter_node.entity.name == node.entity.name and iter_node.entity.status in ['Existing', 'New']]
                if len(base_entities) > 0:
                    node.entity.base_entity = base_entities[0]
                    base_nodes.append(Node(node.entity.base_entity))
        nodes += base_nodes

        return nodes

    @staticmethod
    def extract_data(df):
        data = df["Entity"]
        raw_materials = df["RawMaterials"]
        options = data["Options"]
        spec_prod = data["SpecProd"]
        spec_cons = data["SpecCons"]
        capex = data["Capex"]
        try:
            product_type = data["product_type"]
        except KeyError:
            product_type = None
        return data, raw_materials, options, spec_prod, spec_cons, capex, product_type

    @staticmethod
    def load_entities(data_manager, monikers_filter=None):
        """
        Get data from data service and build entities
        :param data_manager: DataManager
        :param monikers_filter: list
        :return: dictionary of nodes and layers
        """
        # build nodes
        nodes = {}
        layers = {}
        sales_plan = data_manager.sales_plan
        for layer in data_manager.data:
            # list of nodes per layer
            data = {}
            data["Entity"] = data_manager.data[layer]
            data["RawMaterials"] = data_manager.raw_materials
            layer_nodes = NodeFactory.create_nodes(layer, data, monikers_filter)
            if len(layer_nodes) != 0:
                nodes[layer] = layer_nodes
                layers[layer] = Layer(layer_nodes, layer, sales_plan, data_manager.data)
        if all([monikers_filter is None, env.COMBO_NODES != {}]):
            for combo_layer in env.COMBO_NODES:
                combo = env.COMBO_NODES[combo_layer]
                connections = pd.DataFrame(Driver.get_data(combo["url"]))
                connections.set_index("Mine/Benef", inplace=True)
                connections = connections.to_dict(orient="index")
                up_layer = layers[combo["upstream_layer"]]
                down_layer = layers[combo["downstream_layer"]]
                layers[combo_layer] = ComboLayer(up_layer, down_layer, combo_layer, connections,
                                                 data_manager.data[env.PipelineLayer.MINE]["priority_mines"])
                nodes[combo_layer] = layers[combo_layer].nodes
                layers.pop(combo["upstream_layer"])
                layers.pop(combo["downstream_layer"])
                nodes.pop(combo["upstream_layer"])
                nodes.pop(combo["downstream_layer"])
        # check combos in filter
        if monikers_filter is not None:
            combos_filter = [moniker for moniker in monikers_filter if COMBO_NODES_SEPARATION in moniker]
            if len(combos_filter) > 0:
                connections = defaultdict(lambda: defaultdict(lambda: 0))
                names_source = set()
                names_destination = set()
                for couple_moniker in combos_filter:
                    couple = couple_moniker.split(COMBO_NODES_SEPARATION)
                    connections[couple[0]][couple[1]] = 1
                    names_source.add(couple[0])
                    names_destination.add(couple[1])
                nodes_source, layers_source, _ = NodeFactory.load_entities(data_manager, names_source)
                nodes_destination, layers_destination, _ = NodeFactory.load_entities(data_manager, names_destination)
                for combo_layer in env.COMBO_NODES:
                    combo = env.COMBO_NODES[combo_layer]
                    up_layer = layers_source[combo["upstream_layer"]]
                    down_layer = layers_destination[combo["downstream_layer"]]
                    layers[combo_layer] = ComboLayer(up_layer=up_layer, down_layer=down_layer, layer_type=combo_layer,
                                                     connections=connections, connect_by_moniker=True)
                    ordered_nodes = []
                    nodes_monikers = [node.moniker() for node in layers[combo_layer].nodes]
                    for moniker in nodes_monikers:
                        for node in layers[combo_layer].nodes:
                            if moniker == node.moniker():
                                ordered_nodes.append(node)
                                continue
                    nodes[combo_layer] = ordered_nodes
        return nodes, layers, sales_plan

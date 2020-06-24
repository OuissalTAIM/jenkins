# -*- coding: utf-8 -*-


from collections import Counter
from functools import reduce
import itertools
import pandas as pd
import numpy as np
from tqdm import tqdm

import app.config.env as env
from app.entity.Entity import Entity
from app.tools.Logger import logger_simulation as logger
from app.graph.Node import ComboNode
from app.tools.Utils import get_capacity, multidict


class Layer:
    """
    A grouping class for entities of the same level
    """
    def __init__(self, nodes=[], layer_type=env.PipelineLayer.UNDEFINED, sp=None, raw_data=None):
        """
        ctor
        :param nodes: list
        :param layer_type: Enum
        :param shuffle_level: Enum
        """
        self.type = layer_type
        self.shuffle_level = env.SHUFFLE_LEVELS[self.type]
        self.nodes = nodes
        self.global_sp = sp
        self.raw_data = raw_data  # Useful to compute needs, as it gives direct access to processes parameters

    def __str__(self):
        return str(self.type).split('.')[1]

    def __repr__(self):
        return str(self.type)

    def add_node(self, node):
        """
        Add node to layer
        :param node: Node
        :return: None
        """
        if node not in self.nodes:
            self.nodes.append(node)
        else:
            logger.warning("Node %s already in leayer %s" % (node.moniker(), str(self.type)))

    def shuffle(self):
        if self.shuffle_level == env.ShuffleLevel.SHUFFLE_WITHOUT_PERM:
            return self.shuffling_without_perms_with_all_elements()
        elif self.shuffle_level == env.ShuffleLevel.SHUFFLE_WITH_PERMUTATIONS:
            return self.shuffle_with_permutations(self.shuffle_without_permutations())
        elif self.shuffle_level == env.ShuffleLevel.SHUFFLE_WITH_PERMUTATIONS_WITH_FILTERS:
            return self.shuffle_with_permutations_with_filters()
        elif self.shuffle_level == env.ShuffleLevel.SHUFFLE_WITH_UNNAMED:
            return self.shuffle_unnamed_layer(self.nodes, self.raw_data, self.global_sp)
        else:
            logger.warning("Undefined shuffling method")

    def shuffle_without_permutations(self):
        """
        Shuffle nodes in layer
        :return: list
        """
        baskets = {}

        names = list(set(node.name() for node in self.nodes))
        for name in names: baskets[name] = list()
        for node in self.nodes:
            baskets[node.name()].append(node)

        # construct all possible combinations, with one representative from each name
        combinations_level1 = list(itertools.product(*[baskets[key] for key in baskets]))
        # construct all possible subsets of previous combinations
        combinations_level2 = []
        for l in combinations_level1:
            for i in range(1, len(l) + 1):
                intermediate_l = list(itertools.combinations(l, i))
                combinations_level2 += [list(intermediate_l[k]) for k in range(len(intermediate_l))]
        combinations_level2 = [list(x) for x in set(tuple(x) for x in combinations_level2)]
        return combinations_level2

    def shuffling_without_perms_with_all_elements(self):
        baskets = {}

        names = list(set(node.name() for node in self.nodes))
        for name in names: baskets[name] = list()
        for node in self.nodes:
            baskets[node.name()].append(node)
        return list(itertools.product(*[baskets[key] for key in baskets]))

    #TODO: filter functions could be merged into single function to avoid multiple linear exploration of list.
    # Probably lower on readability, but faster, TBD

    @staticmethod
    def filter_over_location(layer_possibilities):
        """ To be used on GRANULATION and PAP layers (so far) only. assume:
        :param layer_possibilities: corresponds to the output of shuffle_without_permutations function (i.e. without permutation,
        and contains the possibilities for a given layer
        :return: subpart of layer_possibilities, containing only options for which all nodes/entities are in the same location
        """
        output = list()
        for sub_scenario in layer_possibilities:
            if len(list(set(node.entity.get_location() for node in sub_scenario))) == 1: output.append(sub_scenario)
        return output

    @staticmethod
    def filter_over_process(layer_possibilities):
        """ same as filter_over_location
        :param layer_possibilities: same as filter_over_location (called sequentially)
        :return: subpart, containing only options with same process
        """
        output=list()
        for sub_scenario in layer_possibilities:
            if len(list(set(node.entity.process for node in sub_scenario))) == 1: output.append(sub_scenario)
        return output

    @staticmethod
    def filter_scenarios_over_granul_capacities(combis_unfiltered, sp):
        combinations_filtered = list()
        sp_granulation = sp[sp['Type'] == 'Fertilizer']
        sp_all_products_as_dap = sp_granulation.groupby(sp_granulation.index).sum()['volume']
        for combi in list(combis_unfiltered):
            if Layer.get_chemical_equivalent(sp_all_products_as_dap, combi):
                combinations_filtered.append(combi)
        return combinations_filtered

    @staticmethod
    def filter_scenarios_over_acp_capacities(combis_unfiltered, sp):
        combinations_filtered = list()
        acp_needs = Layer.get_acp_needs(sp)
        for combi in list(combis_unfiltered):
            if Layer.get_chemical_equivalent(acp_needs, combi):
                combinations_filtered.append(combi)
        return combinations_filtered

    @staticmethod
    def get_acp_needs(sp):
        """ Calculates roughly the quantity of acid needed to satisfy the sales plan
        :param sp: global sales plan
        :param scenario:
        :return: pd.Series(needs, index=timeline)
        """
        """ Getting acid needs """
        p2o5_needs = sp[sp['Type'] == 'Acid'].groupby('Tenor').sum()

        """ A potential scenario should be able to at least satisfy granulation demand, considering
        all ferts have an acid consumption = min(acid consumptions for all ferts and all entities in scenario).
        Such constraint can be reinforced if number of scenarios is still too high """
        granulation_layer = [entity for entity in list(Entity.ENTITIES.values())
                             if entity.layer == env.PipelineLayer.GRANULATION]
        sp_granulation = sp[sp['Type'] == 'Fertilizer']
        sp_all_products_as_dap = sp_granulation.groupby(sp_granulation.index).sum()
        acp_consumptions = [entity.specific_consumptions[fert]['ACP 29']['ACP 29']
                            for entity in granulation_layer
                            for fert in entity.outputs]
        acp_cons_minimal_value = min(map(min, acp_consumptions))
        approximate_acp_need_for_granulation = acp_cons_minimal_value * sp_all_products_as_dap

        return p2o5_needs['volume'] + approximate_acp_need_for_granulation['volume']

    @staticmethod
    def get_chemical_equivalent(production_needs, layer):
        """
        :param production_needs: represents all production or capacity needs as pd.Series
        :param layer: subpart considered of layer
        :return: 1 if considered scenario's production capacity is superior to needs, 0 otherwise
        """
        capacities = list(map(get_capacity, layer))
        equivalent_capacity = reduce(lambda x, y: x+y, capacities)
        return 1*all(equivalent_capacity.values >= production_needs.values)

    def shuffle_with_permutations(self, shuffle_without_permutations):
        """
        Shuffle nodes in layer
        :return: list
        """
        combination_level3 = []
        for combination in shuffle_without_permutations:
            intermediate_2 = list(itertools.permutations(combination))
            combination_level3 += [list(intermediate_2[k]) for k in range(len(intermediate_2))]
        return combination_level3

    def shuffle_with_permutations_with_filters(self):
        combinations_level2 = self.shuffle_without_permutations()
        loc_filtered = Layer.filter_over_location(combinations_level2)
        process_loc_filtered = Layer.filter_over_process(loc_filtered)
        if self.type == env.PipelineLayer.PAP:
            capacity_wise_filtered = Layer.filter_scenarios_over_acp_capacities(process_loc_filtered, self.global_sp)
        elif self.type == env.PipelineLayer.GRANULATION:
            capacity_wise_filtered = Layer.filter_scenarios_over_granul_capacities(process_loc_filtered, self.global_sp)
        else:
            capacity_wise_filtered = process_loc_filtered
        return self.shuffle_with_permutations(capacity_wise_filtered)

    @staticmethod
    def reverse_signature(layer_):
        signatures = list(set([node.entity.signature for node in layer_]))
        d = multidict(signatures, [], [])
        for node in layer_:
            d[node.entity.signature][node.entity.id_number] = node
        return d

    @staticmethod
    def permutate(l):
        if len(l) == 0:
            return []
        elif len(l) <= 9:
            return set(itertools.permutations(l))
        else:
            v = Layer.permutate(l[1:])
            return set(w[:k] + tuple([l[0]]) + w[k:] for w in v for k in range(len(w)))

    @staticmethod
    def shuffle_unnamed_entities_within_unnamed_layer(layer):
        """This shuffle function generates shuffles of unnamed entities only within layer."""
        unnamed_nodes = [node for node in layer if node.entity.status == 'New'] # Assumed that all new are unnamed
        entities_signatures_link = Layer.reverse_signature(unnamed_nodes)
        locations = set(node.entity.get_location() for node in unnamed_nodes)
        processes = set(node.entity.process for node in unnamed_nodes)

        bijection_baskets = multidict(locations, processes, [])  # Dictionary containing list of signatures per location per process
        bijection_permutations = multidict(locations, processes, [])  # Dictionary containing list of permutations of previous signatures per location per process
        bijection_permutations_mirror = multidict(locations, processes, [])  # Dictionary containing list of mirrors of previous dict lists per location per process
        perms_mirrors_zipped = multidict(locations, processes, [])  # Dictionary containing zips of tw previous dicts per location per process
        entities_permutations = multidict(locations, processes, [])  # Dictionary containing list of permutations of entities per location per process


        for node in unnamed_nodes:
            bijection_baskets[node.entity.get_location()][node.entity.process].append(node.entity.signature)

        # Creating unique combinations using bijection_baskets
        for location in locations:
            for process in processes:
                bijection_permutations[location][process] = list(Layer.permutate(bijection_baskets[location][process]))
                bijection_permutations_mirror[location][process] = [Layer.mirror_counter(l) for l in
                                                                    bijection_permutations[location][process]]
                perms_mirrors_zipped[location][process] = [zip(bijection_permutations[location][process][k],
                                                               bijection_permutations_mirror[location][process][k]) for k in
                                                           range(len(bijection_permutations[location][process]))]
                entities_permutations[location][process] = [[entities_signatures_link[t[0]][t[1]] for t in z] for z in
                                                            perms_mirrors_zipped[location][process]]

        return entities_permutations

    @staticmethod
    def shuffle_unnamed_layer(layer, raw_data, sp=None):
        """ Handles existing units for chemical units.
        Adds them to shuffle of unnamed
        Handles also closing date by generating different scenarios for each date"""
        permutations_of_unnamed = Layer.shuffle_unnamed_entities_within_unnamed_layer(layer)
        """ Section used for unification of new units permutation per basket and therefore reducing scenarios number
        Can be parametrized 
         assumptions: 
            - existing units are saturated, we allocate only v = needs - existing capacity
            -  optimal permutation doesn't depend on volume needed. This assumption will be checked by  computing needs 
            and optimal permutation for every choice of granulation process
            - Specialized units abroad are assumed to be saturated 
            - All new acp is supposed to be ACS-self-sufficient """
        #TODO: once granulation PL is implemented, we could either:
        #   - replicate the exact same PL for PAP and SAP layers, especially if execution time is short
        #   - keep current section but remove production of existing units from needs
        granulation_gr, acid_sc = Layer.get_granulation_processes_data(raw_data)
        granulation_acp_needs = Layer.calculate_acp_needs_for_ferts(sp, acid_sc)
        acp_drivers_list = Layer.calculate_total_acp_needs(sp, granulation_acp_needs)
        if layer[0].entity.layer == env.PipelineLayer.PAP:
            optimal_permutations = Layer.simple_allocator(permutations_of_unnamed, acp_drivers_list)

        elif layer[0].entity.layer == env.PipelineLayer.SAP:
            acs_needs = Layer.calculate_total_acs_needs(acp_drivers_list, raw_data)
            optimal_permutations = Layer.simple_allocator(permutations_of_unnamed, acs_needs, driver_name='ACS')

        else:
            pass #TODO: fix granulation

        existing_nodes = [node for node in layer if node.entity.status == 'Existing']
        names = list(set([node.entity.name for node in existing_nodes]))
        baskets_of_existing_by_name = multidict(names, [])
        for node in existing_nodes:
            baskets_of_existing_by_name[node.entity.name].append(node)

        unique_existing = [node for node in existing_nodes if len(baskets_of_existing_by_name[node.name()]) == 1]
        existing_with_different_possibilities = list(
            set(node.name() for node in existing_nodes if len(baskets_of_existing_by_name[node.name()]) != 1))
        shuffles_of_existing_with_different_possibilities = list(
            itertools.product(*[baskets_of_existing_by_name[name] for name in existing_with_different_possibilities]))
        scenarios_with_scenarized_existing = [list(e) + n
                                              for e in shuffles_of_existing_with_different_possibilities
                                              for n in optimal_permutations]

        return [unique_existing + scenario for scenario in scenarios_with_scenarized_existing]

    @staticmethod
    def calculate_acp_needs_for_ferts(sp, specific_consumptions):
        """
        :param sp: sales plan
        :return: dict(process: pd.Series(acp_needs_per_year)
        """
        needs_for_ferts_by_ferts_process = dict()
        sp_granulation = sp[sp['Type'] == 'Fertilizer']
        products_in_sp = list(sp_granulation['Product'].unique())
        for process in specific_consumptions.keys():
            if all(product in specific_consumptions[process].keys() for product in products_in_sp):
                s = sp_granulation.copy()
                for row in s.iterrows():
                    s['acp_needs'] = specific_consumptions[process][row[1]['Product']]
                s['total_acp'] = s['acp_needs']*s['volume']
                needs_for_ferts_by_ferts_process[process] = s.groupby(s.index).sum()['total_acp']
        return needs_for_ferts_by_ferts_process

    @staticmethod
    def calculate_total_acp_needs(sp, needs_for_ferts_by_ferts_process):
        """ This function is used to determine all possible acp needs. Depending on the granulation
        process, the ferts sp needs a different amount of phosphoric acid (henceforth called design_acid_needs).
        We determine best permutation for every design_acid_needs. Only those are kept to build scenarios.
        :param needs_for_ferts_by_ferts_process: dict of process chosen for granulation units with corresponding needs
        :param sp: design_acid_needs
        :return: dict(process: pd.Series(acp_needs_per_year)
        """
        output = []
        sp_acid = sp[sp["Type"] == "Acid"]
        sp_acid = sp_acid.groupby(sp_acid.index).sum()['volume']
        for process in needs_for_ferts_by_ferts_process.keys():
            output.append(needs_for_ferts_by_ferts_process[process]+sp_acid)

        return output

    @staticmethod
    def get_granulation_processes_data(raw_data):
        """
        :param raw_data: self.raw_data
        :return: dict(process: [products produced by process: granulation_ratio], idem for cs_acp
        """
        granulation_ratios_df = raw_data[env.PipelineLayer.GRANULATION]['SpecProd'].copy()
        specific_consumption = raw_data[env.PipelineLayer.GRANULATION]['SpecCons'].copy()
        del granulation_ratios_df['Moniker'], specific_consumption['Moniker'], \
            specific_consumption['Location'], specific_consumption['Capacity'],
        granulation_ratios = multidict(list(granulation_ratios_df.Process.unique()), {}, {})
        specific_consumptions = multidict(list(specific_consumption.Process.unique()), {}, {})
        for process in granulation_ratios.keys():
            sub_gr_by_process = granulation_ratios_df[granulation_ratios_df.Process == process]
            sub_sc_by_process = specific_consumption[(specific_consumption.Process == process) &
                                                     (specific_consumption.Item == 'ACP 29')]
            products = sub_sc_by_process.Product.unique()
            for product in products:
                # TODO: ATTENTION, les rations de granulations doivent être unique ove the years
                #  per product per process, à assurer
                #TODO: remove input from prod spec sheet eventually
                granulation_ratios[process][product] = float(
                    sub_gr_by_process[sub_gr_by_process.Product == product].drop_duplicates()['ratio'])
                specific_consumptions[process][product] = float(
                    sub_sc_by_process[sub_sc_by_process.Product == product].drop_duplicates()['sc/opex'])
        return granulation_ratios, specific_consumptions

    @staticmethod
    def calculate_total_acs_needs(acp_drivers_list, raw_data):
        """ Calculate ACS needed for acp_drivers_list
        Assumption: new ACPs are ACS self sufficient"""
        specific_consumption = raw_data[env.PipelineLayer.PAP]['SpecCons'].copy()
        acs_sc = specific_consumption[specific_consumption['Item'] == 'ACS']
        del acs_sc['Moniker'], acs_sc['Location'], acs_sc['Capacity'],
        output = list()
        for process in list(acs_sc.Process.unique()):
            sub_sc_by_process = acs_sc[acs_sc.Process == process]
            # TODO: ATTENTION, pareillement les cs_acs doivent être unique over the years
            #  by process, à assurer, sinon à gérer différemment
            process_sc = float(sub_sc_by_process.drop_duplicates()['sc/opex'])
            for driver in acp_drivers_list:
                output.append(driver*process_sc)
        return output

    @staticmethod
    def simple_allocator(permutations_dictionary, needs_list, driver_name ='ACP 29', max_permutations_to_keep=1):
        """
        :param permutations_dictionary: dictionary of potential permutations per location per process
        :param needs_list: list of pd.Series computed, representing the volume needed, for every set of choices
        (ex. granulation process for pap layer)
        :param max_permutations_to_keep: max number of permutations to keep per location per process
        :return: dictionary of best npv wise permutations per location per process
        """
        locations = list(permutations_dictionary.keys())
        output = multidict(locations, {}, [])

        # Calculation optimal npv for every set of acp_needs
        for driver_ in needs_list:
            for location in locations:
                for process in permutations_dictionary[location].keys():
                    if process not in output[location].keys():
                        output[location][process] = {}
                    dict_key_permutation = dict() # Dictionary where {key: permutation} are gonna be stored
                    df_key_npv = pd.DataFrame(columns=['key', 'npv'])
                    key = 0
                    for permutation in permutations_dictionary[location][process]:
                        npv = 0
                        key += 1
                        dict_key_permutation[key] = permutation
                        driver = driver_.copy()
                        for node in permutation:
                            produced = np.maximum(0, np.minimum(driver, node.entity.capacity))
                            driver = driver - produced

                            # update total_opex of entities
                            if np.count_nonzero(produced) != 0:
                                total_opex = produced * node.entity.opex[driver_name]
                                prod_start = total_opex[total_opex > 0].index.min()
                                total_capex = node.entity.total_capex.copy()
                                total_capex.index = total_capex.index + prod_start
                                total_capex = total_capex.loc[[x in node.entity.timeline for x in total_capex.index]]
                                total_yearly_expenses = total_opex.add(total_capex, fill_value=0)
                                npv += np.npv(env.WACC, total_yearly_expenses)
                            if np.count_nonzero(driver) == 0: break
                        df_key_npv = df_key_npv.append({'key': key, 'npv': npv}, ignore_index=True)
                    permutations_kept = df_key_npv.sort_values(by=['npv'], ascending=False).head(max_permutations_to_keep)
                    for key in permutations_kept['key']:
                        output[location][process][key] = dict_key_permutation[key]

        return [output[location][process][key]
                for location in output.keys()
                for process in output[location].keys()
                for key in output[location][process].keys()]

    @staticmethod
    def mirror_counter(l):
        output = list()
        for e in range(len(l)):
            signature = l[e]
            anterior = l[:e]
            if len(anterior) == 0: a = 1
            else:
                d = Counter(anterior)
                try: a= d[signature]+1
                except KeyError: a = 1
            output.append(a)
        return output


class ComboLayer(Layer):
    """
    Class for grouped layers
    """

    def __init__(self, up_layer, down_layer, layer_type=env.PipelineLayer.UNDEFINED, connections=None,
                 prioritized_mines=None, connect_by_moniker=False):
        """
        ctor
        :param up_layer: Layer
        :param down_layer: Layer
        :param layer_type: Enum
        :param connections: Dictionary
        :param prioritized_mines: list
        :param connect_by_name: boolean (if False then by location)
        """
        super().__init__(layer_type=layer_type, nodes=[])
        self.up_layer = up_layer
        self.down_layer = down_layer
        self.node_dico = {}
        self.priority_mines = prioritized_mines
        for up_node in self.up_layer.nodes:
            if connect_by_moniker:
                if up_node.moniker() not in connections:
                    continue
            else:
                if up_node.location() not in connections:
                    continue
            for do_node in self.down_layer.nodes:
                if connect_by_moniker:
                    if do_node.moniker() not in connections[up_node.moniker()]:
                        continue
                    if connections[up_node.moniker()][do_node.moniker()] != 1:
                        continue
                    combo_node = ComboNode(self.type, up_node, do_node)
                    self.nodes.append(combo_node)
                    self.node_dico[combo_node.moniker()] = combo_node
                else:
                    if do_node.location() not in connections[up_node.location()]:
                        continue
                    if connections[up_node.location()][do_node.location()] == 0 or \
                        pd.isna(connections[up_node.location()][do_node.location()]) or \
                            up_node.nominal_capacity() > do_node.nominal_capacity(): #TODO: should be: any(up_node.entity.capacity > do_node.entity.capacity), to correct when coherence of data is ensured
                        continue
                    combo_node = ComboNode(self.type, up_node, do_node)
                    self.nodes.append(combo_node)
                    self.node_dico[combo_node.moniker()] = combo_node

    @staticmethod
    def product_and_reduce(list1, list2):
        """ list1 and list2 are assumed to be two lists from dict_by_mine_dictionary or one of its resultants"""
        product = list(reduce(lambda x, y: x + y, tup) for tup in itertools.product(*[list1, list2]))
        to_be_kept = list()
        for sub in product:
            tester_benef_coherence = {}
            for thread in sub:
                if thread.entity.beneficiation.location not in tester_benef_coherence.keys():
                    tester_benef_coherence[thread.entity.beneficiation.location] = set([thread.entity.beneficiation.moniker])
                else:
                    tester_benef_coherence[thread.entity.beneficiation.location].add(thread.entity.beneficiation.moniker)

            if all(len(l) == 1 for l in tester_benef_coherence.values()):
                to_be_kept.append(sub)
        return to_be_kept

    @staticmethod
    def filter_over_beneficiation_capacity(reduced):
        """ Assume reduced to be the output of product_and_reduce"""
        to_be_kept = list()
        for list_ in reduced:
            tester_capa_mine_benef_coherence = {}
            for thread in list_:
                if thread.entity.beneficiation.location not in tester_capa_mine_benef_coherence.keys():
                    # Assumption number 1: the relation between locations and names for beneficiation is bijective
                    # Assumption number 2: for every location, only one beneficiation plant per location exists in data
                    tester_capa_mine_benef_coherence[thread.entity.beneficiation.location] = thread.entity.beneficiation.nominal_capacity - thread.entity.mine.nominal_capacity
                else:
                    tester_capa_mine_benef_coherence[thread.entity.beneficiation.location] -= thread.entity.mine.nominal_capacity

            if all(v >=0 for v in tester_capa_mine_benef_coherence.values()):
                to_be_kept.append(list_)
        return to_be_kept

    @staticmethod
    def simplify_two_thread_buckets(list1, list2):
        reduced = ComboLayer.product_and_reduce(list1, list2)
        return ComboLayer.filter_over_beneficiation_capacity(reduced)

    def shuffle(self):
        mine_locations = list(set(node.location() for node in self.up_layer.nodes))
        wp_locations = list(set(node.location() for node in self.down_layer.nodes))
        d = multidict(mine_locations, wp_locations, {})
        for thread in self.node_dico.values():
            if thread.entity.mine.name not in \
                    d[thread.entity.mine.location][thread.entity.beneficiation.location].keys():
                d[thread.entity.mine.location][thread.entity.beneficiation.location][thread.entity.mine.name] = []
            d[thread.entity.mine.location][thread.entity.beneficiation.location][thread.entity.mine.name].append(thread)

        dict_with_name_combinations = multidict(mine_locations, wp_locations, {})
        for mine in mine_locations:
            for wp in wp_locations:
                l = list()
                for name in d[mine][wp].keys():
                    if d[mine][wp][name]: l.append(d[mine][wp][name])
                if bool(l):
                    dict_with_name_combinations[mine][wp] = [list(tup) for tup in itertools.product(*l)]
                    # Keeping only scenarios for which mines belonging to a given location are connected to same WP
                    dict_with_name_combinations[mine][wp] = list(
                        filter(lambda x: len(list(set(thread.down_node.entity for thread in x))) == 1,
                               dict_with_name_combinations[mine][wp]))
                else:
                    dict_with_name_combinations[mine].pop(wp)

        # Construct dictionary of possible threads by mine
        dict_by_mine = {}
        for key in dict_with_name_combinations.keys():
            if len(dict_with_name_combinations[key].values()) > 0:
                dict_by_mine[key] = reduce(lambda x, y: x + y, dict_with_name_combinations[key].values())
            else:
                logger.warning("No values available for mine %s" % key)

        # Construct mine-benef sub scenarios, taking into account priority mines
        priority_mines = [dict_by_mine[key] for key in dict_by_mine.keys() if key in self.priority_mines]
        priority_combs = reduce(ComboLayer.product_and_reduce, priority_mines)

        non_priority_mines = [dict_by_mine[key] for key in dict_by_mine.keys() if key not in self.priority_mines]
        non_priority_combs = []
        if len(non_priority_mines) > 0:
            non_priority_combs = reduce(ComboLayer.product_and_reduce, non_priority_mines)

        return ComboLayer.product_and_reduce(priority_combs, non_priority_combs)

    def shuffle_old(self):
        """
        Shuffle combos of level 2
        :return: list
        """
        up_shuffles = self.up_layer.shuffle()
        down_shuffles = self.down_layer.shuffle()
        l = itertools.product(*[up_shuffles, down_shuffles])
        l2 = list()
        for couple in l:
            v = list()
            for m in couple[0]:
                for w in couple[1]:
                    moniker = "%s%s%s" % (m.moniker(), env.COMBO_NODES_SEPARATION, w.moniker())
                    if moniker not in self.node_dico:
                        continue
                    v.append(self.node_dico[moniker])
            if v not in l2: l2 += [v]
        permuted = list()
        for shuffle_unpermuted in l2:
            permuted += list(itertools.permutations(shuffle_unpermuted))
        return list(permuted)

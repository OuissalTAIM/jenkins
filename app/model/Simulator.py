# -*- coding: utf-8 -*-


import datetime
from functools import lru_cache
from app.graph.NodeFactory import *
from app.graph.Node import *
from app.model.GranulationSolver import GranulationSolver
from app.model.LogisticsSolver import LogisticsSolver
from app.model.ScenarioGenerator import ScenarioGeneratorFactory as SGF
from tqdm import tqdm
from app.data.DataManager import *
import numpy as np
import app.config.env as env
from app.server.ClientMemcached import memcached_client, insert_history, update_cache
from app.tools.Logger import logger_simulation as logger


class Simulator:
    def __init__(self, dm=None, monikers_filter=None):
        """
        Constructor
        :param graph: input graph
        :param sales_plan: Dataframe, sales plan
        """
        self.data_manager = dm
        if self.data_manager == None:
            self.data_manager = DataManager()
            self.data_manager.load_data()

        self.load_entities(monikers_filter)

    def load_entities(self, monikers_filter):
        """
        Get data from data service and build entities
        :param monikers_filter: list or None
        :return: None
        """
        Entity.ENTITIES.clear()
        self.nodes, self.layers, self.sales_plan = NodeFactory.load_entities(self.data_manager, monikers_filter)

    def simulate(self, cycle=1, phase=0, publishers=None, scenario_generator=None,
                 monitor=False, counter_limit=None, logistics_lp=False,
                 scenarios_filter=None):
        """
        Simulate scenarios and compute CostPV of all possible scenarios
        :param cycle: int
        :param phase: int
        :param publishers: list
        :param scenario_generator: ScenarioGenerator object
        :param monitor: boolean
        :param counter_limit: int
        :param logistics_lp: boolean
        :return: couple(list,list)
        """

        # create scenario generator
        if scenario_generator is None:
            scenario_generator = SGF.create_scenario_generator(env.SCENARIO_GEN_TYPE, self)

        # get driver from sales plan
        sales_plan = self.data_manager.sales_plan

        # monitoring
        counter = 0
        save_counter = 0
        scenarios_details = {}
        scenarios_global = {}
        check_work_infos = {}
        scenarios = scenario_generator.generate()
        scenarios_len = scenario_generator.len()

        # Launch granulation PL
        granulation_solver = GranulationSolver(self.nodes, self.sales_plan)
        total_scenarios = len(granulation_solver.couples) * scenarios_len

        check_work_infos[phase] = {
            "total_scenario": str(total_scenarios),
            "maxWorker": env.RABBITMQ_MAX_WORKER,
            'db_name': env.DB_NAME,
            'time_start': datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
        }

        for tup in granulation_solver.couples:
            if counter_limit is not None and counter > counter_limit:
                break

            granulation_solved = granulation_solver.launch_granulation_solver(tup)
            if granulation_solved.status != 1:
                counter += scenarios_len
                if monitor and counter >= total_scenarios - phase:
                    progress = round(int((counter * 100) / total_scenarios), 2)
                    check_work_infos[phase]["progress"] = str(progress)
                    check_work_infos[phase]["counter"] = str(counter)
                    update_cache("workers_info_%i" % phase, check_work_infos)
                continue

            granulation_solver.write_optimization_results(granulation_solved)
            recalculated_sales_plan = tup[1]
            domestic_granulation_nodes = list(filter(lambda x: (x.entity.productionSite == 'Morocco'), tup[0]))

            # Abroad nodes produce at full capacity NPK
            abroad_nodes = list(filter(lambda x: (x.entity.productionSite != 'Morocco'), tup[0]))
            if len(abroad_nodes) != 0:
                for node in abroad_nodes:
                    node.entity.production["NPK"]["volume"] = node.entity.capacity

            tup_acid_needs_per_year = \
                reduce(lambda x, y: x + y, [node.entity.production[product]["volume"] *
                                            node.entity.specific_consumptions[product]["ACP 29"]["ACP 29"]
                                            for node in domestic_granulation_nodes for product in node.entity.production.keys()])
            tup_rock_needs_per_year = \
                reduce(lambda x, y: x + y, [node.entity.production["TSP"]["volume"] *
                                            node.entity.specific_consumptions["TSP"]["ACP 29"]["Chimie"]
                                            for node in domestic_granulation_nodes if "TSP" in
                                            node.entity.production.keys()])

            # Running calculation of metrics for granulation layer
            granulation_npv = 0
            granulation_scenario_results = []
            for granulation in tup[0]:
                granulation.entity.compute_metrics()
                granulation_npv += granulation.entity.get_cost_pv(env.RANDOMIZE_RESULTS)
                for result in granulation.entity.get_data(env.RANDOMIZE_RESULTS):
                    granulation_scenario_results.append(result)

            counter_step = 0
            scenario_counter = 0
            for scenario in tqdm(scenarios, total=scenarios_len):

                counter += 1
                if scenarios_filter is not None:
                    if counter in scenarios_filter:
                        scenarios_filter.remove(counter)
                    else:
                        continue
                scenario_counter += 1
                if counter_limit is not None and scenario_counter > counter_limit:
                    break

                if monitor:
                    if counter_step == env.MONITORING_STEP or counter >= total_scenarios - phase:
                        progress = round(int((counter * 100) / total_scenarios), 2)
                        check_work_infos[phase]["progress"] = str(progress)
                        check_work_infos[phase]["counter"] = str(counter)
                        update_cache("workers_info_%i" % phase, check_work_infos)
                        counter_step = 0
                    counter_step += 1

                if scenario_counter % cycle != phase:
                    continue

                for product in recalculated_sales_plan.Product.unique():
                    product_needs = recalculated_sales_plan[recalculated_sales_plan.Product == product]
                    if product_needs.Type.unique() == 'Fertilizer':
                        pass
                    elif product == 'ACP 29':
                        driver = sales_plan[sales_plan.Product == product]["volume"] + tup_acid_needs_per_year
                        self.flow_upstream(product, driver, scenario)
                    else:
                        driver = sales_plan[sales_plan.Product == product]["volume"]
                        self.flow_upstream(product, driver, scenario)
                    # Flow upstream TSP needs separately
                self.flow_upstream("Chimie", tup_rock_needs_per_year, scenario)

                # Rebalance production in threads, and compute balances, opex
                Simulator.rebalance_thread_production(scenario)

                # Calculation for non-granulation entities that have non-zero production
                has_produced = list(filter(lambda x: (x.layer != env.PipelineLayer.GRANULATION) and
                                                     (True in set(any(x.production[product]["volume"] > 0)
                                                                  for product in x.production.keys())),
                                           Entity.ENTITIES.values()))

                scenario_results = []
                for gsr in granulation_scenario_results:
                    gsr_ = gsr.copy()
                    gsr_["Scenario"] = counter
                    scenario_results.append(gsr_)
                scenario_cost_pv = granulation_npv

                for entity in has_produced:
                    entity.compute_metrics()
                    scenario_cost_pv += entity.get_cost_pv(env.RANDOMIZE_RESULTS)
                    for result in entity.get_data(env.RANDOMIZE_RESULTS):
                        result["Scenario"] = counter
                        scenario_results.append(result)

                logistic_model_status = -1
                if logistics_lp:
                    logistics_solver = LogisticsSolver(self.nodes, scenario, sales_plan)
                    _, logistics_entities, logistic_model_status = logistics_solver.launch_logistics_solver()
                    if logistic_model_status != 1:
                        logger.warning("Logistics solver failed for scenario %d" % counter)
                    else:
                        for elt in logistics_entities:
                            has_produced.append(elt)
                    for entity in logistics_entities:
                        entity.compute_metrics()
                        scenario_cost_pv += entity.get_cost_pv(env.RANDOMIZE_RESULTS)
                        for result in entity.get_data(env.RANDOMIZE_RESULTS):
                            result["Scenario"] = counter
                            scenario_results.append(result)

                # must reset before moving on
                for entity in has_produced:
                    entity.reset()

                if logistics_lp and logistic_model_status != 1:
                    continue

                if publishers is None:
                    scenarios_details[counter] = scenario_results
                    scenarios_global[counter] = {
                        "Scenario": counter,
                        "Cost PV": scenario_cost_pv,
                        "Unit": "$", #TODO: check unit
                        "Moniker": json.dumps(NodeJSONEncoder().encode([tup[0]] + scenario))
                    }
                else:
                    publishers["details"].save(scenario_results, counter)
                    publishers["global"].save({
                        "Scenario": counter,
                        "Cost PV": scenario_cost_pv,
                        "Unit": "$", #TODO: check unit
                        "Moniker": [tup[0]] + scenario,
                    }, counter)
                save_counter += 1

            # Reset granulation entities
            for granulation in tup[0]:
                granulation.entity.reset()

        if monitor:
            if save_counter > 0:
                message = "Phase %s done successfully" % phase
                insert_history(phase=phase, task_to_save=check_work_infos[phase], status=env.HTML_STATUS.OK.value,
                               message=message)
            else:
                message = "All scenarios have failed for phase %s" % phase
                insert_history(phase=phase, task_to_save=check_work_infos[phase], status=env.HTML_STATUS.ERROR.value,
                               message=message)

        return scenarios_global, scenarios_details

    def flow_upstream(self, product, driver, sub_scenario):
        """
        Flow upstream in the scenario and transform products along the way
        :param product: output product
        :param driver: sales plan, transformed sales plan
        :param scenario: Scenario
        :return: None
        """
        if not sub_scenario:
            return
        layer = sub_scenario[0]
        if any(product in node.entity.outputs for node in layer):
            sublayer_producing_product = [node.entity for node in layer if
                                          product in node.entity.outputs]
            new_allocation = self.allocate_production(product, driver, sublayer_producing_product)
            if sublayer_producing_product[0].layer != PipelineLayer.MINE_BENEFICIATION:
                for entity in sublayer_producing_product:
                    if entity.name in new_allocation[product].keys():
                        if entity.main_input != 'All':
                            main = new_allocation[product][entity.name] * \
                                   entity.specific_consumptions[product][entity.main_input][entity.main_input]
                            self.flow_upstream(entity.main_input, main, sub_scenario[1:])
                        if 'ACS' in entity.specific_consumptions[product][entity.main_input].keys():
                            main = new_allocation[product][entity.name] * \
                                   entity.specific_consumptions[product][entity.main_input]['ACS']
                            self.flow_upstream('ACS', main, sub_scenario[1:])
            else:
                pass
        else:
            self.flow_upstream(product, driver, sub_scenario[1:])

    def allocate_production(self, driver_name, _driver, combination):
        """
        :param driver: product pulling the production in given combination (example: PA for a PAP comb.)
        assumed to be an ARRAY with sorted needs from y0 to y10
        :param combination: a combination from previous method
        :return: combination with values of production filled for driver, or -1 in case sp is not feasible
        in some year.
        """
        driver = _driver.copy()
        # define dictionary that is gonna be used for propagation
        new_allocation_to_propagate = Utils.multidict([driver_name], [], {})
        if combination[0].layer != env.PipelineLayer.MINE_BENEFICIATION:
            for entity in combination:
                if np.count_nonzero(driver) != 0:
                    # Filling production of entities in specific layer, taking nto account needs (sp+chem needs) and capacity
                    produced = np.maximum(0, np.minimum(driver, entity.capacity))
                    if np.count_nonzero(produced) != 0:
                        entity.production[driver_name]['volume'] = entity.production[driver_name]['volume'] + produced
                        driver = driver - produced
                        entity.capacity = entity.capacity - produced
                        new_allocation_to_propagate[driver_name][entity.name] = produced
        else:
            for thread in combination:
                if np.count_nonzero(driver) != 0:
                    if thread.mine.base_entity is None and thread.beneficiation.base_entity is None:
                        mine_capa_to_consider = thread.mine.capacity.copy()
                        wp_capa_to_consider = thread.beneficiation.capacity.copy()
                        driver, capa_mine_constrained, capa_wp_constrained = \
                            Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine,
                                                                                     thread.beneficiation, driver_name,
                                                                                     driver, mine_capa_to_consider,
                                                                                     wp_capa_to_consider)

                    elif thread.mine.base_entity is not None and thread.beneficiation.base_entity is None:
                        mine_capa_to_consider = thread.mine.base_entity.capacity
                        wp_capa_to_consider = thread.beneficiation.capacity
                        driver, capa_base_mine_constrained, capa_wp_constrained = \
                            Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine.base_entity,
                                                                                     thread.beneficiation, driver_name,
                                                                                     driver, mine_capa_to_consider,
                                                                                     wp_capa_to_consider)

                        if np.count_nonzero(driver) != 0 and any(capa_base_mine_constrained < capa_wp_constrained):
                            mine_capa_to_consider = np.maximum(
                                thread.mine.capacity - thread.mine.base_entity.nominal_capacity, 0)
                            wp_capa_to_consider = thread.beneficiation.capacity
                            driver, capa_mine_constrained, capa_wp_constrained = \
                                Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine,
                                                                                         thread.beneficiation,
                                                                                         driver_name, driver,
                                                                                         mine_capa_to_consider,
                                                                                         wp_capa_to_consider)

                    elif thread.mine.base_entity is None and thread.beneficiation.base_entity is not None:
                        mine_capa_to_consider = thread.mine.capacity
                        wp_capa_to_consider = thread.beneficiation.base_entity.capacity
                        driver, capa_mine_constrained, capa_base_wp_constrained = \
                            Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine,
                                                                                     thread.beneficiation.base_entity,
                                                                                     driver_name, driver,
                                                                                     mine_capa_to_consider,
                                                                                     wp_capa_to_consider)

                        if np.count_nonzero(driver) != 0 and any(capa_base_wp_constrained < capa_mine_constrained):
                            mine_capa_to_consider = thread.mine.capacity
                            wp_capa_to_consider = np.maximum(
                                thread.beneficiation.capacity - thread.beneficiation.base_entity.nominal_capacity, 0)
                            driver, capa_mine_constrained, capa_wp_constrained = \
                                Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine,
                                                                                         thread.beneficiation,
                                                                                         driver_name, driver,
                                                                                         mine_capa_to_consider,
                                                                                         wp_capa_to_consider)

                    elif thread.mine.base_entity is not None and thread.beneficiation.base_entity is not None:
                        mine_capa_to_consider = thread.mine.base_entity.capacity
                        wp_capa_to_consider = thread.beneficiation.base_entity.capacity
                        driver, capa_base_mine_constrained, capa_base_wp_constrained = \
                            Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine.base_entity,
                                                                                     thread.beneficiation.base_entity,
                                                                                     driver_name, driver,
                                                                                     mine_capa_to_consider,
                                                                                     wp_capa_to_consider)

                        if np.count_nonzero(driver) != 0:
                            mine_capa_to_consider = np.maximum(
                                thread.mine.capacity - thread.mine.base_entity.nominal_capacity, 0)
                            wp_capa_to_consider = np.maximum(
                                thread.beneficiation.capacity - thread.beneficiation.base_entity.nominal_capacity, 0)
                            driver, _, _ = Simulator.calculate_capa_and_prod_for_entities_in_thread(thread, thread.mine,
                                                                                                    thread.beneficiation,
                                                                                                    driver_name, driver,
                                                                                                    mine_capa_to_consider,
                                                                                                    wp_capa_to_consider)
        return new_allocation_to_propagate

    @staticmethod
    def calculate_capa_and_prod_for_entities_in_thread(thread, mine, beneficiation, driver_name, driver,
                                                       mine_capa_to_consider, benef_capa_to_consider):
        """ Function used as initial dispatch of production between origin-extension in propagation function
        :return: useful elements for the rest of the loop
        """
        capa_mine_constrained = mine_capa_to_consider / thread.raw_rock_consumption[driver_name]
        capa_wp_constrained = benef_capa_to_consider / thread.raw_rock_consumption[driver_name]

        output_driver = driver.copy()
        produced = np.maximum(0, np.minimum(driver, np.minimum(capa_mine_constrained, capa_wp_constrained)))

        if np.count_nonzero(produced) != 0:
            output_driver = driver - produced

            # Updating capacities
            mine.capacity = mine.capacity - produced * thread.raw_rock_consumption[driver_name]
            beneficiation.capacity = beneficiation.capacity - produced * thread.raw_rock_consumption[driver_name]
            # Updating prod
            mine.production['Raw Rock']['volume'] = mine.production['Raw Rock']['volume'] + produced * \
                                                    thread.raw_rock_consumption[driver_name]
            beneficiation.production[driver_name]['volume'] = beneficiation.production[driver_name]['volume'] + \
                                                              produced * thread.raw_rock_consumption[driver_name]

        return output_driver, capa_mine_constrained, capa_wp_constrained

    @staticmethod
    def rebalance_thread_production(scenario):
        """ rebalances thread production between base an original entities
        :param scenario: ongoing scenario
        :return: None, fills mine and beneficiation objects with relevant results
        """
        for thread in scenario[-1]:
            if thread.entity.mine.base_entity is None and thread.entity.beneficiation.base_entity is None:
                pass
            elif thread.entity.mine.base_entity is not None and thread.entity.beneficiation.base_entity is None:
                Simulator.rebalance_entity(thread, rebalance_mine=True)
            elif thread.entity.mine.base_entity is None and thread.entity.beneficiation.base_entity is not None:
                Simulator.rebalance_entity(thread, rebalance_ben=True)
            elif thread.entity.mine.base_entity is not None and thread.entity.beneficiation.base_entity is not None:
                Simulator.rebalance_entity(thread, rebalance_ben=True)
                Simulator.rebalance_entity(thread, rebalance_mine=True)
            Simulator.calculate_thread_opex_and_balances(thread.entity)

    @staticmethod
    def rebalance_entity(thread, rebalance_mine=False, rebalance_ben=False):
        if rebalance_mine:
            entity = thread.entity.mine
        if rebalance_ben:
            entity = thread.entity.beneficiation

        # Getting year where extension entity has produced its first ton. This year is gonna be
        # considered to be the year of arrival
        try:
            start_year = min(entity.production[key]["volume"][entity.production[key]["volume"] > 0].index[0]
                             for key in entity.production.keys())
        except IndexError:
            start_year = 10000
        # Correcting production dispatch
        for key in entity.production.keys():
            entity.production[key]["volume"] = entity.production[key]["volume"] + \
                                               entity.base_entity.production[key]["volume"] * \
                                               np.heaviside(entity.base_entity.production[key]["volume"].index - start_year, 1)
            entity.base_entity.production[key]["volume"] = entity.base_entity.production[key]["volume"] * \
                                                           (1 - np.heaviside(entity.base_entity.production[key][
                                                                                 "volume"].index - start_year, 1))

    @staticmethod
    def calculate_thread_opex_and_balances(thread):
        # Updating total opex and input balances for mine
        thread.mine.total_opex = thread.mine.production['Raw Rock']['volume'] * thread.mine.opex['Raw Rock']
        for input_ in thread.mine.inputs:
            thread.mine.consumption[input_]['volume'] = \
                thread.mine.consumption[input_]['volume'] + \
                (thread.mine.production['Raw Rock']['volume'] *
                 thread.mine.specific_consumptions['Raw Rock']['All'][input_])
        if thread.mine.base_entity is not None:
            thread.mine.base_entity.total_opex = thread.mine.production['Raw Rock']['volume'] * thread.mine.opex[
                'Raw Rock']
            for input_ in thread.mine.base_entity.inputs:
                thread.mine.base_entity.consumption[input_]['volume'] = \
                    thread.mine.base_entity.consumption[input_]['volume'] + \
                    (thread.mine.base_entity.production['Raw Rock']['volume'] *
                     thread.mine.base_entity.specific_consumptions['Raw Rock']['All'][input_])

        # Updating total opex and input balances for mine
        for driver_name in thread.wp_equivalent_opex.keys():
            thread.beneficiation.total_opex = thread.beneficiation.total_opex + \
                                              thread.beneficiation.production[driver_name]["volume"] * \
                                              thread.wp_equivalent_opex[driver_name]
            for input_ in thread.beneficiation.inputs:
                thread.beneficiation.consumption[input_]['volume'] = \
                    thread.beneficiation.consumption[input_]['volume'] + \
                    thread.beneficiation.production[driver_name]["volume"] * thread.wp_equivalent_specific_consumption[driver_name][input_]

            if thread.beneficiation.base_entity is not None:
                base_wp_equivalent_specific_consumption, base_wp_equivalent_opex = \
                    MineBeneficiationEntity.get_wp_specific_consumptions(thread.mine,
                                                                         thread.beneficiation.base_entity,
                                                                         thread.raw_rock_consumption)
                thread.beneficiation.base_entity.total_opex = thread.beneficiation.base_entity.total_opex + \
                                                              thread.beneficiation.base_entity.production[driver_name][
                                                                  "volume"] * \
                                                              base_wp_equivalent_opex[driver_name]
                for input_ in thread.beneficiation.inputs:
                    thread.beneficiation.base_entity.consumption[input_]['volume'] = \
                        thread.beneficiation.base_entity.consumption[input_]['volume'] + \
                        thread.beneficiation.base_entity.production[driver_name]["volume"] * \
                        base_wp_equivalent_specific_consumption[driver_name][input_]


    @lru_cache(maxsize=128, typed=True)
    def get_node(self, layer, id):
        """
        Get node and cache it
        :param layer: enumeration (MINE, ..)
        :param id: entity id
        :return: Node
        """
        layers = [layer] if layer is not None else list(env.PipelineLayer)
        for layer in layers:
            if layer not in self.nodes:
                continue
            for node in self.nodes[layer]:
                if node.moniker() == id:
                    return node
        logger.warning("Node %s not found" % id)
        return None

# -*- coding: utf-8 -*-


from app.entity.Entity import *
from pulp import *
import app.config.env as env
from app.tools.Logger import logger_simulation as logger


class LogisticsSolver:
    def __init__(self, nodes, scenario, salesPlan):

        pipeAndconveyorNodes = list(
            filter(lambda x: (x.entity.method != 'Train'), nodes[env.PipelineLayer.LOGISTICS]))

        newPAPentities = list(filter(lambda x: (x.entity.status == 'New'), scenario[0]))
        if newPAPentities[0].entity.location == 'Mzinda':
            trainNodes = list(
                filter(lambda x: (x.entity.method == 'Train' and x.entity.PAPlocation == 'Mz'),
                       nodes[env.PipelineLayer.LOGISTICS]))
        else:
            trainNodes = list(
                filter(lambda x: (x.entity.method == 'Train' and x.entity.PAPlocation == 'Safi'),
                       nodes[env.PipelineLayer.LOGISTICS]))

        logisticList = []
        logisticList.extend(pipeAndconveyorNodes)
        logisticList.extend(trainNodes)

        self.logistics_entities = logisticList    # Logistic nodes
        self.mine_beneficiation_entities = nodes[env.PipelineLayer.MINE_BENEFICIATION]  # Mine-beneficiation nodes
        self.beneficiation_entities = self.get_beneficiation_entities()     # Beneficiation nodes
        self.pap_entities = nodes[env.PipelineLayer.PAP] #  PAP nodes
        self.granul_entities = [node for node in nodes[env.PipelineLayer.GRANULATION] if node.entity.productionSite == "Morocco"] #   Granulation nodes
        self.existing_logistics_entities = self.get_Existing_logistics()    # Existing logistics nodes
        self.new_logistics_entities = self.get_new_logistics()  # New logistics nodes
        self.extended_logistics_entities = self.get_extended_logistics()    # Extended logistics nodes
        self.separator = '#'
        self.var_dict = dict()  #   Variables dictionnary
        self.locations = self.get_locations_function()  #   List of all possible locations
        self.timeline = list(range(env.T0, env.TMAX))   #   Timeline
        self.rock_port = salesPlan[(salesPlan.Type == 'Rock')].copy()  #    Rock sales plan
        self.acid_port = salesPlan[(salesPlan.Type == 'Acid')].copy()  #    Acid sales plan

    def get_locations_function(self):   #   Function that gets the locations
        dict = {}
        for lognode in self.logistics_entities:
            dict[lognode.entity.upstream] = {}
            dict[lognode.entity.downstream] = {}
        return list(dict.keys())

    def get_beneficiation_entities(self):   #   Function that get beneficiation nodes
        beneficiation_entities = []
        for mine_beneficiation in self.mine_beneficiation_entities:
            if mine_beneficiation.down_node not in beneficiation_entities:
                beneficiation_entities.append(mine_beneficiation.down_node)
        return beneficiation_entities

    def get_new_logistics(self):    #   Function that gets the new logistics nodes
        return list(filter(lambda x: (x.entity.status == 'New'), self.logistics_entities))

    def get_Existing_logistics(self):   #   Function that gets the existing logistics nodes
        return list(filter(lambda x: (x.entity.status == 'Exist'), self.logistics_entities))

    def get_extended_logistics(self):   #   Function that gets the extended logistics nodes
        return list(filter(lambda x: (x.entity.status == 'Extension'), self.logistics_entities))

    def create_logistics_model(self):
        """ Function that creates the linear problem"""
        return LpProblem('logistics lp', LpMinimize)

    def existing_logistics_definition(self):    #   Function that creates the existing logistics volume variables
        for node in self.existing_logistics_entities:
            for year in node.entity.timeline:
                var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                self.var_dict[var_name] = LpVariable(var_name, 0)

    def new_logistics_definition(self):     #   Function that creates the new logistics volume variables
        for node in self.new_logistics_entities:
            for year in node.entity.timeline:
                var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                self.var_dict[var_name] = LpVariable(var_name, 0)

    def new_investments_definition(self):   #   Function that creates the investment binary variables
        for node in self.new_logistics_entities:
            for year in node.entity.timeline:
                var_name = 'Investment' + self.separator + node.entity.moniker + self.separator + str(year)
                self.var_dict[var_name] = LpVariable(var_name, cat=LpBinary)

    def beneficiation_balance_constraint(self, model):
        """ Function that creates the demand constraint from beneficiation and
        that takes into consideration movement of Rock between washplants """
        for location in self.locations:
            for year in self.timeline:
                lhs = []
                rhs = []
                for node in self.logistics_entities:
                    if node.entity.downstream == location and node.entity.moniker.split('/')[5] == 'WP2WP':
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        lhs.append(self.var_dict[var_name])
                    elif node.entity.upstream == location and node.entity.product == 'Rock':
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        rhs.append(self.var_dict[var_name])
                for entity in self.beneficiation_entities:
                    if entity.entity.location == location:
                        lhs.append(entity.entity.production['Chimie']['volume'][year])
                if len(lhs) > 0 and len(rhs) > 0:
                    constraint_name_left = 'BalanceCstWP' + self.separator + location + self.separator + str(year) + "production_driving"
                    constraint_name_right = 'BalanceCstWP' + self.separator + location + self.separator + str(year)+"demand_driving"
                    model += lpSum(lhs) <= lpSum(rhs), constraint_name_right
                    model += lpSum(lhs) >= lpSum(rhs), constraint_name_left

    def consumption_at_destination_definition(self, model):
        """ Function that creates the demand constraint driven by the PAP, Granul and Port"""
        for location in self.locations:
            for year in self.timeline:
                lhsRock = []
                lhsAcid = []
                lhsFertilizer = []
                for node in self.logistics_entities:
                    if node.entity.downstream == location and node.entity.product == 'Rock':
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        lhsRock.append(self.var_dict[var_name])
                    if node.entity.downstream == location and node.entity.product == 'Acid':
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        lhsAcid.append(self.var_dict[var_name])
                    if node.entity.downstream == location and node.entity.product == 'Fertilizer':
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        lhsFertilizer.append(self.var_dict[var_name])

                rhsRock = []
                rhsAcid = []
                rhsFertilizer = []

                for entity in self.pap_entities :
                    if entity.entity.location == location:
                        try:
                            rhsRock.append(entity.entity.consumption['Chimie']['volume'][year])
                            if location == 'Safi':
                                rhsAcid.append(-entity.entity.production['ACP 29']['volume'][year])
                        except :
                            pass
                for entity in self.granul_entities:
                    if entity.entity.location == location:
                        try:
                            rhsRock.append(entity.entity.consumption['Chimie']['volume'][year])
                        except :
                            pass
                    if 'ACP 29' in entity.entity.consumption.keys():
                        rhsAcid.append(entity.entity.consumption['ACP 29']['volume'][year])


                if location == 'Safi':

                    rhsRock.append(self.rock_port['volume'][year])
                    rhsAcid.append(self.acid_port['volume'][year])

                if len(lhsRock)>0 and len(rhsRock)>0:
                    constraint_name = 'ConsumptionCst' + self.separator + 'Rock' + self.separator + location + self.separator + str(year)
                    model += lpSum(lhsRock) >= lpSum(rhsRock), constraint_name

                if len(lhsAcid) > 0 and len(rhsAcid) > 0:
                    constraint_name = 'ConsumptionCst' + self.separator + 'Acid' + self.separator + location + self.separator + str(year)
                    model += lpSum(lhsAcid) >= lpSum(rhsAcid), constraint_name

                if len(lhsFertilizer) > 0 and len(rhsFertilizer) > 0:
                    constraint_name = 'ConsumptionCst' + self.separator + 'Fertilizer' + self.separator + location + self.separator + str(year)
                    model += lpSum(lhsFertilizer) >= lpSum(rhsFertilizer), constraint_name

    def existing_transportation_capacity_definition(self, model):
        """ Function that creates the capacity constraint of existing logistic nodes"""
        for node in self.existing_logistics_entities:
            for year in node.entity.timeline:
                lhs = []
                var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                lhs.append(self.var_dict[var_name])

                if len(lhs)>0:
                    constraint_name = 'TransportCapaCst' + self.separator + node.entity.moniker + self.separator + str(year)
                    model += lpSum(lhs) <= node.entity.capacity[year], constraint_name

    def new_transportation_capacity_definition(self, model):
        """ Function that creates the capacity constraint of new logistic nodes"""
        for node in self.new_logistics_entities:
            for year in node.entity.timeline:
                lhs = []
                var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                lhs.append(self.var_dict[var_name])
                investment_years = [inv_year for inv_year in node.entity.timeline if inv_year <= year]
                for investment_year in investment_years:
                    inv_var_name = 'Investment' + self.separator + node.entity.moniker + self.separator + str(investment_year)
                    lhs.append(-self.var_dict[inv_var_name] * node.entity.capacity[investment_year])
                if len(lhs)>0:
                    constraint_name = 'TransportCapaCst' + self.separator + node.entity.moniker + self.separator + str(year)
                    model += lpSum(lhs) <= 0, constraint_name

    def investment_constraint_definition(self, model):
        """ Function that creates the constraint limiting the one time investment in a logistic nodes"""
        for node in self.new_logistics_entities:
            lhs = []
            for year in node.entity.timeline:
                var_name = 'Investment' + self.separator + node.entity.moniker + self.separator + str(year)
                lhs.append(self.var_dict[var_name])
            if len(lhs) > 0:
                constraint_name = 'InvestmentDefinitionCst' + self.separator + node.entity.moniker
                model += lpSum(lhs) <= 1, constraint_name

    def upstream_production_definition(self, model):
        """ Function that creates that the production volume constraint"""
        for location in self.locations:
            for year in self.timeline:
                lhs = []
                rhs = []
                for node in self.logistics_entities:
                    if node.entity.upstream == location and (node.entity.moniker.split('/')[5] == 'PAP2Granul' or node.entity.moniker.split('/')[5] == 'PAP2Port'):
                        var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                        lhs.append(self.var_dict[var_name])

                for entity in self.pap_entities :
                    if entity.entity.location == location :
                        rhs.append(entity.entity.production['ACP 29']['volume'][year])
                # TODO : à activer seulement si la granul peut se faire ailleurs qu'à Safi
                # for entity in self.granul_entities :
                #     if entity.entity.location == location :
                #         rhs.append(-entity.entity.consumption['ACP 29']['volume'][year])

                if len(lhs) > 0 and len(rhs)>0 :
                    constraint_name = 'ProductionCst' + self.separator + location + self.separator + str(year)
                    model += lpSum(lhs) <= lpSum(rhs), constraint_name


    def objective_function_definition(self, model):
        """ Function writing the objective function with the opex being opex
        per ton multiplied by the cost per ton """
        model.sense = LpMinimize

        opex = []
        for node in self.logistics_entities:
            for year in node.entity.timeline:
                var_name = 'Volume' + self.separator + node.entity.moniker + self.separator + str(year)
                opex.append(node.entity.opex[node.entity.product][year]/((1+env.WACC)**(year-node.entity.timeline[0]))*self.var_dict[var_name])

        capex = []
        for node in self.new_logistics_entities:
            for year in node.entity.timeline:
                var_name = 'Investment' + self.separator + node.entity.moniker + self.separator + str(year)
                for index in node.entity.capex.index:
                    capex.append(node.entity.capex[index]/((1+env.WACC)**((year-node.entity.timeline[0])+index))*self.var_dict[var_name])
        objective = lpSum(capex) + lpSum(opex)
        model += lpSum(objective)

    def variables_definition(self):
        self.existing_logistics_definition()
        self.new_logistics_definition()
        self.new_investments_definition()

    def add_constraints(self, model):
        self.consumption_at_destination_definition(model)
        self.existing_transportation_capacity_definition(model)
        self.new_transportation_capacity_definition(model)
        self.investment_constraint_definition(model)
        self.beneficiation_balance_constraint(model)

    def launch_logistics_solver(self):
        model = self.create_logistics_model()
        self.variables_definition()
        self.add_constraints(model)
        self.objective_function_definition(model)
        #model.writeLP("file_logistics.lp")
        model.solve()
        logger.info('Logistics model status :  %s ' % LpStatus[model.status])

        return self.write_optimization_results(model)

    def write_optimization_results(self, model):
        logistic_nodes = []
        logistic_entities = []
        if model.status == 1:
            logistics_entities = self.logistics_entities
            transported_volumes = list(
                filter(lambda x: (x.varValue != 0 and 'Volume' in x.name),
                       model.variables()))
            dict = {}
            for var in transported_volumes:
                variable_details = var.name.split(self.separator)
                node = list(filter(lambda x: (x.entity.moniker.replace(' ', '/') == variable_details[1].replace('_', '/')),
                                   self.logistics_entities))
                logistics_entities[self.logistics_entities.index(node[0])].entity.production[variable_details[1].split('_')[8]]['volume'][int(variable_details[2])] = var.varValue
                dict[node[0].entity.moniker] = logistics_entities[self.logistics_entities.index(node[0])]
            logistic_nodes = list(x for x in dict.values())
            logistic_entities = list(x.entity for x in dict.values())
        return logistic_nodes, logistic_entities, model.status

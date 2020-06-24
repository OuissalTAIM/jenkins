# -*- coding: utf-8 -*-


from functools import reduce
from app.model.GranulationDataPrep import *
from pulp import *
import app.config.env as env
from app.tools.Logger import logger_simulation as logger


class GranulationSolver:

    def __init__(self, nodes, salesPlan):

        self.granulation_nodes = nodes[env.PipelineLayer.GRANULATION]
        self.newEntities = GranulationDataPrep.get_new_entities_in_morocco(self.granulation_nodes)
        self.existingEntities = GranulationDataPrep.get_existing_entities(self.granulation_nodes)
        self.abroadEntities = GranulationDataPrep.get_entities_abroad(self.granulation_nodes)
        self.global_sp = salesPlan.copy()
        self.couples = self.get_sp_nodes_couples()
        self.separator = '#'
        self.var_dict = dict()

    def get_sp_nodes_couples(self):
        """ This method is usd to build all possible (nodes, sp) combinations,
        based on which abroad entities are considered to exist
        :return: list of tuples where tup[0]=granulation combination, tup[1]=sp
        """
        output = []
        existing_and_new_combinations = itertools.product(*[self.existingEntities, self.newEntities])
        existing_and_new_combinations = [tup[0]+tup[1] for tup in existing_and_new_combinations]

        # Possible abroad combinations
        abroad_ = [list(itertools.combinations(self.abroadEntities, i)) for i in range(len(self.abroadEntities) + 1)]
        abroad_ = reduce(lambda x, y: x+y, abroad_)
        abroad_possibilities = [list(comb) for comb in abroad_]

        for possibility in abroad_possibilities:
            # Production of abroad entities MUST be equal to their capacity. i.e. sales plan NPK>=capacity_abroad
            if len(possibility) == 0:
                npk_produced_abroad = 0
                acp_needs_abroad = 0
                dap_needs_abroad = 0
            else:
                npk_produced_abroad = reduce(lambda x, y: x + y, [p.entity.capacity for p in possibility])

                # Calculating ACP needs for units abroad
                acp_needs = [p.entity.capacity * p.entity.specific_consumptions['NPK']['ACP 29']['ACP 29']
                             for p in possibility if 'ACP 29' in p.entity.specific_consumptions['NPK']['ACP 29'].keys()]
                if len(acp_needs) == 0: acp_needs_abroad = 0
                else: acp_needs_abroad = reduce(lambda x, y: x + y, acp_needs)

                # Calculating DAP needs for units abroad
                dap_needs = [p.entity.capacity * p.entity.specific_consumptions['NPK']['ACP 29']['DAP']
                             for p in possibility if 'DAP' in p.entity.specific_consumptions['NPK']['ACP 29'].keys()]
                if len(dap_needs) == 0: dap_needs_abroad = 0
                else: dap_needs_abroad = reduce(lambda x, y: x + y, dap_needs)

            calculated_sales_plan = self.global_sp.copy()
            # Removing abroad capacity from sales plan
            calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'NPK', 'volume'] = \
                calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'NPK', 'volume'] - npk_produced_abroad
            # Adding removed NPK sales plan to acid sales plan
            calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'ACP 29', 'volume'] = \
                calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'ACP 29', 'volume'] + acp_needs_abroad
            # Adding removed NPK sales plan to DAP sales plan
            calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'DAP', 'volume'] = \
                calculated_sales_plan.loc[calculated_sales_plan['Product'] == 'DAP', 'volume'] + dap_needs_abroad

            # Constructing all possible combinations with existing+new with considered abroad possibility
            if len(possibility) == 0: all_with_possibility = existing_and_new_combinations
            else:
                all_with_possibility = [tup[0]+tup[1] for tup in itertools.product(*[existing_and_new_combinations, [possibility]])]
            for scenario in all_with_possibility:
                t = tuple([scenario, calculated_sales_plan])
                output.append(t)

        return output

    def create_granulation_model(self):
        return LpProblem('Granulation lp', LpMinimize)

    def existing_production_definition(self, existing_entities):
        for node in existing_entities:
            for product in node.entity.production.keys():
                for year in node.entity.production[product]['volume'].index:
                    var_name = 'ExistingProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    self.var_dict[var_name] = LpVariable(var_name, 0)

    def new_production_definition(self, combination_entities):
        for node in combination_entities:
            for product in node.entity.production.keys():
                for year in node.entity.production[product]['volume'].index:
                    var_name = 'NewProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    self.var_dict[var_name] = LpVariable(var_name, 0)

    def new_investment_definition(self, combination_entities):
        for node in combination_entities:
            for year in node.entity.timeline:
                var_name = 'NewInvestment' + self.separator + node.entity.moniker + self.separator + str(year)
                self.var_dict[var_name] = LpVariable(var_name, 0, 1, LpInteger)

    def demand_relaxation_definition(self, model_sales_plan):
        for year in model_sales_plan.index.unique():
            sales_plan = model_sales_plan[model_sales_plan.index == year]
            for product in sales_plan['Product'].unique():
                var_name = 'Relax_DemandSatisfaction' + self.separator + product + self.separator + str(year)
                self.var_dict[var_name] = LpVariable(var_name, 0)

    def demand_constraint_definition(self, model, model_sales_plan, combination_entities, existing_entities):
        for year in model_sales_plan.index.unique():
            sales_plan = model_sales_plan[model_sales_plan.index == year]
            for product in sales_plan['Product'].unique():
                lhs = []
                for node in existing_entities:
                    if year in node.entity.timeline and product in node.entity.production.keys():
                        var_name = 'ExistingProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                        lhs.append(self.var_dict[var_name])

                for node in combination_entities:
                    if year in node.entity.timeline and product in node.entity.production.keys():
                        var_name = 'NewProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                        lhs.append(self.var_dict[var_name])

                if env.GRANUL_RELAX:
                    var_name = 'Relax_DemandSatisfaction' + self.separator + product + self.separator + str(year)
                    lhs.append(self.var_dict[var_name])

                constraint_name = 'DemandSatisfaction' + self.separator + product + self.separator + str(year)
                model += lpSum(lhs) >= sales_plan[sales_plan['Product'] == product]['volume'], constraint_name

    def existing_capacity_constraint_definition(self, model, existing_entities):
        for node in existing_entities:
            for year in node.entity.timeline:
                lhs = []
                for product in node.entity.production.keys():
                    var_name = 'ExistingProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    granulation_ratio = node.entity.granulation_ratios[product][year]
                    if granulation_ratio != 0:
                        lhs.append((1/granulation_ratio)*self.var_dict[var_name])
                constraint_name = 'ExistingCapaCst' + self.separator + node.entity.moniker + self.separator + str(year)
                model += lpSum(lhs) <= node.entity.capacity[year], constraint_name

    def new_capacity_constraint_definition(self, model, combination_entities):
        for node in combination_entities:
            for year in node.entity.timeline:
                lhs = []
                for product in node.entity.production.keys():
                    var_name = 'NewProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    granulation_ratio = node.entity.granulation_ratios[product][year]
                    if granulation_ratio != 0:
                        lhs.append((1/granulation_ratio)*self.var_dict[var_name])
                investment_years = [inv_year for inv_year in node.entity.timeline if inv_year <= year]
                for investment_year in investment_years:
                    inv_var_name = 'NewInvestment' + self.separator + node.entity.moniker + self.separator + str(investment_year)
                    lhs.append(-self.var_dict[inv_var_name]*node.entity.capacity[investment_year])
                constraint_name = 'NewCapaCst' + self.separator + node.entity.moniker + self.separator + str(year)
                model += lpSum(lhs) <= 0, constraint_name

    def investment_definition(self, model, combination_entities):
        for node in combination_entities:
            lhs = []
            for year in node.entity.timeline:
                var_name = 'NewInvestment' + self.separator + node.entity.moniker + self.separator + str(year)
                lhs.append(self.var_dict[var_name])
            constraint_name = 'InvestmentDefinition' + self.separator + node.entity.moniker
            model += lpSum(lhs) <= 1, constraint_name

    def objective_function_definition(self, model, combination_entities, existing_entities, model_sales_plan):
        model.sense = LpMinimize

        opex = []
        for node in existing_entities:
            for product in node.entity.production.keys():
                for year in node.entity.production[product]['volume'].index:
                    var_name = 'ExistingProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    opex.append(node.entity.opex[product][year]/((1+env.WACC)**(year-node.entity.timeline[0]))*self.var_dict[var_name])
        for node in combination_entities:
            for product in node.entity.production.keys():
                for year in node.entity.production[product]['volume'].index:
                    var_name = 'NewProd' + self.separator + node.entity.moniker + self.separator + product + self.separator + str(year)
                    opex.append(node.entity.opex[product][year]/((1+env.WACC)**(year-node.entity.timeline[0]))*self.var_dict[var_name])

        relax = 0
        if env.GRANUL_RELAX:
            relax = []
            for year in model_sales_plan.index.unique():
                sales_plan = model_sales_plan[model_sales_plan.index == year]
                for product in sales_plan['Product'].unique():
                    var_name = 'Relax_DemandSatisfaction' + self.separator + product + self.separator + str(year)
                    relax.append(1000000*self.var_dict[var_name])


        capex = []
        for node in combination_entities:
            for year in node.entity.timeline:
                var_name = 'NewInvestment' + self.separator + node.entity.moniker + self.separator + str(year)
                for index in node.entity.capex.index:
                    capex.append(node.entity.capex[index]/((1+env.WACC)**((year-node.entity.timeline[0])+index))*self.var_dict[var_name])
        objective = lpSum(capex) + lpSum(opex) + lpSum(relax)
        model += lpSum(objective)

    def variables_definition(self, combination_entities, existing_entities, model_sales_plan):
        self.existing_production_definition(existing_entities)
        self.new_production_definition(combination_entities)
        self.new_investment_definition(combination_entities)
        if env.GRANUL_RELAX:
            self.demand_relaxation_definition(model_sales_plan)

    def add_constraints(self, model, sales_plan, combination_entities, existing_entities):
        self.demand_constraint_definition(model, sales_plan, combination_entities, existing_entities)
        self.existing_capacity_constraint_definition(model, existing_entities)
        self.new_capacity_constraint_definition(model, combination_entities)
        self.investment_definition(model, combination_entities)

    def launch_granulation_solver(self, tup):
        granulation_scenario = tup[0]
        ferts_sp = tup[1][tup[1].Type == 'Fertilizer'].copy()
        existing_entities = list(filter(lambda x: (x.entity.status == 'Existing'), granulation_scenario))
        new_entities = list(filter(lambda x: (x.entity.status == 'New' and x.entity.productionSite == 'Morocco'), granulation_scenario))

        model = self.create_granulation_model()
        self.variables_definition(new_entities, existing_entities, ferts_sp)
        self.add_constraints(model, ferts_sp, new_entities, existing_entities)
        self.objective_function_definition(model, new_entities, existing_entities, ferts_sp)
        model.writeLP("file.lp")
        model.solve()

        return model

    def write_optimization_results(self, model):
        entity_production = list(filter(lambda x: (x.varValue != 0 and ('ExistingProd'in x.name or 'NewProd' in x.name)), model.variables()))
        for var in entity_production:
            variable_details = var.name.split(self.separator)
            node = list(filter(lambda x: (x.entity.moniker.replace(' ','/') == variable_details[1].replace('_','/')), self.granulation_nodes))[0]
            node.entity.production[variable_details[2]]['volume'][int(variable_details[3])] = var.varValue
            logger.info('varname : ' + var.name + ' = ' + str(var.varValue))

        if not env.GRANUL_RELAX:
            return self.granulation_nodes

        relaxation_variables = list(filter(lambda x: (x.varValue != 0 and 'Relax_DemandSatisfaction'in x.name), model.variables()))
        demand_relaxation = {}
        for var in relaxation_variables:
            demand_relaxation[var.name] = var.varValue
        return demand_relaxation

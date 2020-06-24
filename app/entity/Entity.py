# -*- coding: utf-8 -*-


from app.tools import Utils
import numpy as np
from app.tools.Logger import logger_simulation as logger
import app.config.env as env
import pandas as pd
from app.tools.Utils import multidict
from copy import deepcopy


class Entity:
    """
    Class for all unit, entities
    """

    # Cache for all entities
    ENTITIES = {}

    def __init__(self, option, spec_cons_opex, capex, spec_prod, product_type, layer=env.PipelineLayer.UNDEFINED, unnamed_in_layer=False):
        """
        :param option: option series for considered option
        :param layer: layer
        """
        moniker = option.Moniker
        if moniker in self.ENTITIES:
            logger.warning("Entity {0} already exists".format(moniker))
        Entity.ENTITIES[moniker] = self

        # Attributes available in option
        self.location = option.Location if 'Location' in option else None
        self.status = option.Status
        if self.status == 'New' and unnamed_in_layer:
            """ That means that if layer contains unnamed units (PAP, GRA, and SAP so far, all new entities are 
            considered as unnamed. 
            The attribute "self.signature" will be initiated with an integer. Every entity with a not null max_number 
            attribute will have a unique signature in its corresponding layer. These signatures will be used to generate 
            the shuffles in a unique way. Example:
                - Entity1, max_number = 2, signature=0
                - Entity2, max_number = 3, signature=1
                a scenario would contain a permutation of [0, 0, 0, 1, 1]
                The inverse function to go from a given permutation to its corresponding is based on a counter 
                (cf static method Layer.mirror_counter) """

            self.max_number = option.Name
            self.signature = None
            self.name = None
        else:
            self.max_number = None
            self.signature = None
            self.name = option.Name

        self.base_entity = None

        self.nominal_capacity = float(option.Capacity)
        self.layer = layer
        self.closingDate = option['ClosingDate']
        self.startingDate = option['StartingDate']

        self.moniker = option.Moniker

        # Attributes describing option, with information available in other sheets
        self.timeline = sorted(spec_cons_opex.index.unique().tolist())
        self.capacity = Entity.get_capacities(option, self.nominal_capacity, self.timeline)
        self.capex = Entity.get_capex(capex, self.moniker)
        self.inputs = Entity.get_consumed(option, spec_cons_opex)
        self.outputs = []
        self.main_input = None
        self.specific_consumptions = None
        self.opex = None
        # Attribute containing type of different outputs, as instructed in dictionary
        # (By-product, Waste, etc)
        if product_type is not None and spec_prod is not None:
            self.secondary_products = \
                [key for key in product_type.keys() if product_type[key] in ['Waste', 'Co-product', 'By-product']]
            self.secondary_products_spec_prod = self.get_specific_productions(spec_prod)

        else:
            self.secondary_products = None

        # Constants used for reinitialization from one scenario to another
        self.zero_consumption = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.inputs}
        self.zero_production = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.zero_capacities = self.capacity
        self.zero_total_opex = pd.Series([0] * len(self.timeline), index=self.timeline)

        # Attributes to reset from one scenario to another (not exhaustive)
        self.total_capex = self.capex.copy()
        self.total_opex = self.zero_total_opex
        self.consumption = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.inputs}
        self.production = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.cost_pv = None

    def __str__(self):
        return self.moniker

    def __repr__(self):
        return str(self)

    def get_location(self):
        return self.location

    @staticmethod
    def get_products(option, spec_prod_df):
        return list(spec_prod_df[(spec_prod_df.Moniker == option.Moniker)]['Product'].unique())

    @staticmethod
    def get_main_consumed(moniker, spec_prod):
        return list(spec_prod[(spec_prod.Moniker == moniker)]["Input"].unique())[0]

    @staticmethod
    def get_consumed(option, spec_cons_df, non_consumables=tuple(['Total'])):
        consumption = list(spec_cons_df[(spec_cons_df.Moniker == option.Moniker)]['Item'].unique())
        for e in non_consumables:
            try: consumption.remove(e)
            except ValueError: pass
        return consumption

    @staticmethod
    def get_capex(capex_, moniker):
        capex = capex_[capex_.Moniker == moniker]
        if 'Total' in list(set(capex.Item)):
            c = capex[capex.Item == 'Total']
        else:
            c = capex[capex.Item != 'Total']
        s = c.CAPEX * c['capex'].replace(r'^\s*$', np.nan, regex=True).fillna(0)
        return s.groupby(s.index).sum()

    @staticmethod
    def get_capacities(option, nominal_capacity, timeline):
        starting_date = int(option["StartingDate"]) if Utils.is_numeric(option["StartingDate"]) else -float("Inf")
        closing_date = int(option["ClosingDate"]) if Utils.is_numeric(option["ClosingDate"]) else float("Inf")
        arr = nominal_capacity * (1 - np.heaviside([t - closing_date for t in timeline], 1)) * \
              np.heaviside([t - starting_date for t in timeline], 1)
        return pd.Series(arr, index=timeline)

    def get_specific_consumptions(self, spec_cons_df, option, outputs, main_inputs, items, inputs_type='uniform'):
        """ assume:
        :param outputs: to be self.outputs, list,
        :param main_inputs: to be self.main_input or self.main_inputs,
        depending on whether uniform or spec mode, as list if specific mode, str if uniform
        :param items: to be self.inputs, as list,
        :param inputs_type:
        expresses the fact that sc are specific to an input type, in which case the resulting dictionary is a three-level dict.
        :return: d={output:{input:{item:array for every item} for every input} for every output}
        """
        if inputs_type == 'uniform':
            d = multidict(outputs, [main_inputs], items,  {})
            for output in outputs:
                for item in items:
                    d[output][main_inputs][item] = self.get_specific_consumptions_in_out_item(spec_cons_df, option, output, main_inputs, item)
        else:
            d = multidict(outputs, main_inputs, items, {})
            for output in outputs:
                for input in main_inputs:
                    for item in items:
                        d[output][input][item] = self.get_specific_consumptions_in_out_item(spec_cons_df, option, output, input, item)
        return d

    def get_specific_productions(self, spec_prod_df):
        """
        :param spec_prod_df: spec prod dataframe
        :return: dict(by/co/waste/product name: pd.Series(prod_spec_per_year)
        """
        output = dict()
        spec_prod_df = spec_prod_df[spec_prod_df.Moniker == self.moniker]
        if self.secondary_products is not None:
            for product in self.secondary_products:
                if product in spec_prod_df.Product.unique():
                    output[product] = spec_prod_df[spec_prod_df['Product'] == product]['pc']
                else: pass
        return output


    @staticmethod
    def get_specific_consumptions_in_out_item(spec_cons_df, option, product, input, item):
        """
        :param spec_cons_df: assumed to be the specific consumptions df
        :param option: assumed to be the option considered
        :param input: assumed to be the name of main product input (ex. rock quality for wp)
        :param item: assumed to be the name of required item whose specific consumptions is needed
        :param product: assumed to be the name of product for whch the cs is needed
        :return: np.array(cs) for needed item and product
        """
        pass

    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, main_inputs=None):
        #TODO: take into account currencies ?
        """returns opex per ton for considered entity
        :return: dictionary {output: opex_per_ton (as time series) for every output}
        """
        pass

    def compute_by_co_waste_products_balances(self):
        main_product = list(self.specific_consumptions.keys())[0] # Assumption: only one main_product in SAP[ACS]/PAP[ACP] layers
        for product in self.production.keys():
            if product in self.secondary_products:
                self.production[product]['volume'] = self.production[main_product]['volume'] * self.secondary_products_spec_prod[product]

    def compute_inputs_balances(self):
        # update consumption for different inputs in combination
        for input_ in self.inputs:
            for produced in self.specific_consumptions.keys():
                if len(self.specific_consumptions[produced][self.main_input][input_]) > 0:
                    self.consumption[input_]['volume'] = \
                        self.consumption[input_]['volume'] + \
                        self.production[produced]['volume'] * \
                        self.specific_consumptions[produced][self.main_input][input_]

    def compute_total_opex(self):
        """ Computes total opex for a given entity"""
        if self.layer in [env.PipelineLayer.MINE, env.PipelineLayer.BENEFICIATION]:
            pass
        else:
            for produced in self.specific_consumptions.keys():
                if produced in self.production.keys() and produced in self.opex.keys():
                    self.total_opex = self.total_opex + self.production[produced]['volume'] * self.opex[produced]

    def compute_total_capex(self):
        """computes total capex for an entity"""
        # TODO: ensure case of existing is well handled (à priori needs further examination, especially for units existing but with still ongoing capex)
        # TODO: ensure sommation (capex+opex) is well handled
        first_non_zero_opex = self.total_opex.loc[self.total_opex > 0]
        prod_start = first_non_zero_opex.index[0] if not first_non_zero_opex.empty else None
        if prod_start is None:
            self.total_capex = pd.Series([])
        else:
            self.total_capex.index += prod_start
            self.total_capex = self.total_capex.loc[self.total_capex.index.isin(self.timeline)]

    def compute_cost_pv(self):
        """computes elementary cost_pv"""
        total_yearly_expenses = self.total_opex.add(self.total_capex, fill_value=0)
        return np.npv(env.WACC, total_yearly_expenses)

    def compute_metrics(self):
        """function called after the completion of a given scenario's calculation
        computes chosen/implemented metrics for the scenario on entities"""
        if self.layer not in [env.PipelineLayer.MINE, env.PipelineLayer.BENEFICIATION]:
            self.compute_inputs_balances()
            self.compute_total_opex()
        if self.secondary_products is not None:
            self.compute_by_co_waste_products_balances()
        self.compute_total_capex()
        self.cost_pv = self.compute_cost_pv()

    #@profile
    def reset(self):
        """
        Reset consumption and production based on sales plan schedule
        """
        self.consumption = deepcopy(self.zero_consumption)
        self.production = deepcopy(self.zero_production)
        self.total_opex = self.zero_total_opex.copy()
        self.total_capex = self.capex.copy()
        self.cost_pv = 0
        self.capacity = self.zero_capacities.copy()

    def get_data(self, randomize=False):
        if not randomize:
            return [{
                "Moniker": self.moniker,
                "Layer": str(self.layer).replace("PipelineLayer.", ""),
                "Name": self.name,
                "Location": self.get_location(),
                "Capacity": self.capacity,
                "Cost PV": self.cost_pv,
                "Opex": self.total_opex,
                "Capex": self.total_capex,
                "Consumption": self.consumption,
                "Production": self.production,
            }]
        # simulated data
        return [{
            "Moniker": self.moniker,
            "Layer": str(self.layer).replace("PipelineLayer.", ""),
            "Name": self.name,
            "Location": self.get_location(),
            "Capacity": Utils.simulate_series(self.capacity, 0, 1000),
            "Cost PV": Utils.simulate_range(100000, 1000000),
            "Opex": Utils.simulate_series(self.total_opex, 100, 10000),
            "Capex": Utils.simulate_series(self.total_capex, 1000, 100000),
            "Consumption": Utils.to_dict_and_simulate(self.consumption, "volume", 2, 100, 1000),
            "Production": Utils.to_dict_and_simulate(self.production, "volume", 2, 50, 500),
        }]

    def get_cost_pv(self, randomize=False):
        if not randomize:
            return self.cost_pv if self.cost_pv is not None else 0
        return Utils.simulate_range(100000, 1000000)

# -*- coding: utf-8 -*-


from app.entity.Entity import *
import app.tools.Utils as Utils
from app.entity.Capacity import *
from numpy import nan


class BeneficiationEntity(Entity):
    """
    Beneficiation class
    """
    def __init__(self, option, spec_cons_opex, capex, spec_prod, rm_prices, product_type):
        """
        Beneficiation entity class, assume:
        :param option, spec_cons_opex, capex, spec_prod: Dataframes
        """
        super().__init__(option, spec_cons_opex, capex, spec_prod, product_type, layer=env.PipelineLayer.BENEFICIATION)

        # Additional attributes available in info
        self.process = option.Process

        # Attributes describing option with information available in other sheets
        self.main_input = "Raw Rock"
        self.main_inputs = self.get_main_consumed(self.moniker, spec_prod)
        self.outputs = self.get_products(option, spec_prod)
        self.production = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.specific_consumptions = self.get_specific_consumptions(spec_cons_opex, option, self.outputs,
                                                                    self.main_inputs, self.inputs, inputs_type='specific')
        self.yields = self.get_yields(option, spec_prod, self.outputs, self.main_inputs)
        self.opex = self.calculate_opex_per_ton(option, spec_cons_opex, rm_prices, self.outputs, self.main_inputs)
        self.zero_production = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}

    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, main_inputs=None):
        opex = spec_cons_df[spec_cons_df.Moniker == option.Moniker]
        opex_per_input_per_output = Utils.multidict(outputs, main_inputs, {})
        for input in main_inputs:
            for output in outputs:
                opex_input_output = opex[(opex.InputQuality == input) & (opex.OutputQuality == output)]
                if 'Total' in list(set(opex_input_output.Item)):
                    opex_per_input_per_output[output][input] = opex_input_output[opex_input_output.Item == 'Total']['sc/opex']
                else:
                    conso_with_prices = pd.merge(opex_input_output, rm_prices,
                                                 on=['Item', 'Tenor'], how='left')
                    conso_with_prices['opex'] = conso_with_prices['sc/opex'] * conso_with_prices['price']
                    opex_per_input_per_output[output][input] = conso_with_prices.groupby('Tenor').sum()['opex']

        return opex_per_input_per_output

    @staticmethod
    def get_yields(option, spec_prod, outputs, inputs):
        yields = spec_prod[spec_prod.Moniker == option.Moniker]
        d = Utils.multidict(outputs, inputs, {})
        for product in outputs:
            for input in inputs:
                c = yields[(yields.InputQuality == input) &
                           (yields.OutputQuality == product)]
                s = c['yield']
                d[product][input] = s
        return d

    @staticmethod
    def get_products(option, spec_prod_df):
        return list(spec_prod_df[(spec_prod_df.Moniker == option.Moniker)]['OutputQuality'].unique())

    @staticmethod
    def get_main_consumed(moniker, spec_prod):
        return list(spec_prod[(spec_prod.Moniker == moniker)]["InputQuality"].unique())

    @staticmethod
    def get_specific_consumptions_in_out_item(spec_cons_df, option, product, input, item):
        return spec_cons_df[(spec_cons_df.Moniker == option.Moniker) &
                            (spec_cons_df.Item == item) &
                            (spec_cons_df.InputQuality == input) &
                            (spec_cons_df.OutputQuality == product)]['sc/opex']

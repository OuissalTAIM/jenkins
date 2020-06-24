# -*- coding: utf-8 -*-


from app.entity.Entity import *
import app.tools.Utils as Utils
from app.entity.Capacity import *
from numpy import nan


class SAPEntity(Entity):
    """
    SAP class
    """
    def __init__(self, option, spec_cons_opex, capex, spec_prod, rm_prices, product_type, unnamed_in_layer=True):
        super().__init__(option, spec_cons_opex, capex, spec_prod, product_type, layer=env.PipelineLayer.SAP, unnamed_in_layer=unnamed_in_layer)

        # Additional attributes available in info
        self.process = option.Process
        self.location = option.Location
        self.associated_pap = option.Associated_pap
        self.closing_date = option.ClosingDate

        # Attributes describing option with information available in other sheets
        self.main_input = "All"
        self.outputs = self.get_products(option, spec_prod)
        self.specific_consumptions = self.get_specific_consumptions(spec_cons_opex, option, ['ACS'], self.main_input, self.inputs)
        self.opex = self.calculate_opex_per_ton(option, spec_cons_opex, rm_prices, outputs=['ACS'])
        self.production = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.zero_production = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}


    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, inputs=None):
        opex = spec_cons_df[(spec_cons_df.Moniker == option.Moniker)]
        d = dict()
        for output in outputs:  # TODO handle byproducts
            if 'Total' in list(set(opex.Item)):
                o = opex[opex.Item == 'Total'].rename(columns={'sc/opex': 'opex'})
                s = o['opex']
                d[output] = s
            else:
                conso_with_prices = pd.merge(opex, rm_prices, on=['Item', 'Tenor'], how='left')
                conso_with_prices['opex'] = conso_with_prices['sc/opex'].astype('float32') * conso_with_prices[
                    'price'].astype('float32')
                d[output] = conso_with_prices.groupby('Tenor').sum()['opex']
        return d

    def get_specific_consumptions_in_out_item(self, spec_cons_df, option, product, input, item):
        return spec_cons_df[(spec_cons_df.Moniker == option.Moniker) &
                            (spec_cons_df.Item == item)]['sc/opex']

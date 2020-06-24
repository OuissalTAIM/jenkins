# -*- coding: utf-8 -*-


from app.entity.Entity import *
import app.tools.Utils as Utils
from app.entity.Capacity import *
from numpy import nan


class LogisticsEntity(Entity):
    def __init__(self, option, spec_cons, capex, spec_prod, raw_materials, locations):
        super().__init__(option, spec_cons, capex, spec_prod, locations, layer=env.PipelineLayer.LOGISTICS)

        # Attributes available in option
        self.upstream = option.Upstream
        self.downstream = option.Downstream
        self.method = option.Method
        self.product_class = option.Product
        self.layer2layer = option['LayerToLayer']
        self.PAPlocation = option['PAPLocation']
        self.product = option['Product']

        self.locations = locations
        # Attributes describing option with information available in other sheets
        self.main_input = self.product_class
        self.outputs = ['Rock', 'Acid', 'Fertilizer']
        self.specific_consumptions = self.get_specific_consumptions(spec_cons, option, [self.product_class], 'All', self.inputs)
        self.opex = self.calculate_opex_per_ton(option, spec_cons, raw_materials, outputs=self.product_class)
        self.production = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.zero_production = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}

    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, inputs=None):
        opex = spec_cons_df[(spec_cons_df.Moniker == option.Moniker)]
        if 'Total' in list(set(opex.Item)):
            o = opex[opex.Item == 'Total'].rename(columns={'sc/opex': 'opex'})
            return {outputs: o['opex']}
        else:
            conso_with_prices = pd.merge(opex, rm_prices, on=['Item', 'Tenor'], how='left')
            conso_with_prices['opex'] = conso_with_prices['sc/opex']*conso_with_prices['price']
            return {outputs: conso_with_prices.groupby('Tenor').sum()['opex']}

    @staticmethod
    def get_specific_consumptions_in_out_item(spec_cons_df, option, product, input, item):
        return spec_cons_df[(spec_cons_df.Moniker == option.Moniker) &
                            (spec_cons_df.Item == item)]['sc/opex']

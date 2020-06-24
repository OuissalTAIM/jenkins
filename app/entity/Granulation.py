# -*- coding: utf-8 -*-


from app.entity.Entity import *
from app.entity.Capacity import *


class GranulationEntity(Entity):
    """
    Granulation class
    """
    def __init__(self, option, spec_cons, capex, spec_prod, rm_prices, product_type):
        super().__init__(option, spec_cons, capex, spec_prod, product_type, layer=env.PipelineLayer.GRANULATION, unnamed_in_layer=True)

        # Additional attributes available in info
        self.process = option.Process
        self.productionSite = option['ProductionSite']
        self.type = option['Type']
        self.products = self.get_products(option)
        self.main_input = self.get_main_consumed(self.moniker, spec_prod)
        self.outputs = self.get_products(option)
        self.specific_consumptions = self.get_specific_consumptions(spec_cons, option, self.outputs, self.main_input, self.inputs) #TODO: correct hardcoded 'ACP29' once coproducts/byproducts correctly handled
        self.granulation_ratios = self.get_granulation_ratios(option, self.outputs, spec_prod)
        self.opex = self.calculate_opex_per_ton(option, spec_cons, rm_prices, self.outputs)
        self.production = {k: {"volume": pd.Series([0]*len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}
        self.zero_production = {k: {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""} for k in self.outputs}

    @staticmethod
    def get_products(option):
        return option['Products'].split('/')

    @staticmethod
    def get_granulation_ratios(option, outputs, spec_prod):
        gr = spec_prod[spec_prod.Moniker == option.Moniker]
        d = dict()
        for product in outputs:
            ratio = gr[gr.Product == product]
            s = ratio['ratio']
            d[product] = s
        return d

    def get_specific_consumptions_in_out_item(self, spec_cons_df, option, product, input, item):
        return spec_cons_df[(spec_cons_df.Moniker == option.Moniker) &
                            (spec_cons_df.Product == product) &
                            (spec_cons_df.Item == item)]['sc/opex']

    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, inputs=None):
        opex = spec_cons_df[(spec_cons_df.Moniker == option.Moniker)]
        d = dict()
        for output in outputs:
            opex_ = opex[opex.Product == output]
            if 'Total' in list(set(opex_.Item)):
                o = opex_[opex_.Item == 'Total'].rename(columns={'sc/opex': 'opex'})
                s = o['opex']
                d[output] = s
            else:
                conso_with_prices = pd.merge(opex_, rm_prices, on=['Item', 'Tenor'], how='left')
                conso_with_prices['opex'] = conso_with_prices['sc/opex'].astype('float32') * conso_with_prices[
                    'price'].astype('float32')
                d[output] = conso_with_prices.groupby('Tenor').sum()['opex']
        return d

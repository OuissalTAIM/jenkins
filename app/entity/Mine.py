# -*- coding: utf-8 -*-
from app.entity.Entity import *
from app.entity.Capacity import *


class MineEntity(Entity):
    """
    Mine class
    """
    def __init__(self, option, spec_cons_opex, capex, spec_prod, rm_prices, product_type):
        """
        Mine entity class, assume:
        :param option, spec_cons_opex, capex, spec_prod: Dataframes
        """
        super().__init__(option, spec_cons_opex, capex, spec_prod, product_type, layer=env.PipelineLayer.MINE)

        # Additional attributes available in info
        self.extraction = option.Extraction

        # Attributes describing option with information available in other sheets
        self.main_input = "All"
        self.outputs = self.get_products(option, spec_prod)
        self.specific_consumptions = self.get_specific_consumptions(spec_cons_opex, option, ['Raw Rock'], self.main_input, self.inputs)
        self.mine_composition = self.get_mine_composition(self.moniker, self.outputs, spec_prod)
        self.opex = self.calculate_opex_per_ton(option, spec_cons_opex, rm_prices)

        # Calculated and scenario dependent elements, to be reinitialized from one scenario to another
        self.production = {"Raw Rock": {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""}}

        # Constants used for reinitialization from one scenario to another
        self.zero_production = {"Raw Rock": {"volume": pd.Series([0] * len(self.timeline), index=self.timeline), "unit": ""}}

    @staticmethod
    def get_mine_composition(moniker, outputs, spec_prod):
        composition = spec_prod[spec_prod.Moniker == moniker]
        d = dict()
        for quality in outputs:
            c = composition[composition.Quality == quality]
            s = c['composition']
            d[quality] = s
        return d

    @staticmethod
    def calculate_opex_per_ton(option, spec_cons_df, rm_prices, outputs=None, inputs=None):
        opex = spec_cons_df[(spec_cons_df.Moniker == option.Moniker)]
        if 'Total' in list(set(opex.Item)):
            o = opex[opex.Item == 'Total'].rename(columns={'sc/opex': 'opex'})
            s = o['opex']
            return {'Raw Rock': s}
        else:
            conso_with_prices = pd.merge(opex, rm_prices, on=['Item', 'Tenor'], how='left')
            conso_with_prices['opex'] = conso_with_prices['sc/opex']*conso_with_prices['price']
            return {'Raw Rock': conso_with_prices.groupby('Tenor').sum()['opex']}

    @staticmethod
    def get_products(option, spec_prod_df):
        return list(spec_prod_df[(spec_prod_df.Moniker == option.Moniker)]['Quality'].unique())

    def get_specific_consumptions_in_out_item(self, spec_cons_df, option, product, input, item):
        return spec_cons_df[(spec_cons_df.Moniker == option.Moniker) &
                            (spec_cons_df.Item == item)]['sc/opex']

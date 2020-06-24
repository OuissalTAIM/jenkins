# -*- coding: utf-8 -*-


from app.entity.Entity import *
import app.config.env as env
import app.tools.Utils as Utils


class MineBeneficiationEntity(Entity):
    """
    Mine and Beneficiation combo class
    """
    def __init__(self, mine, beneficiation):
        """
        ctor
        :param mine: Entity
        :param beneficiation: Entity
        """
        self.mine = mine
        self.beneficiation = beneficiation
        self.name = "%s%s%s" % (mine.name, env.COMBO_NODES_SEPARATION, beneficiation.name)
        self.moniker = "%s%s%s" % (mine.moniker, env.COMBO_NODES_SEPARATION, beneficiation.moniker)
        self.layer = env.PipelineLayer.MINE_BENEFICIATION
        self.inputs = self.mine.inputs
        self.outputs = self.beneficiation.outputs
        self.raw_rock_consumption = self.get_raw_rock_consumption(self.mine, self.beneficiation)
        self.wp_equivalent_specific_consumption, self.wp_equivalent_opex = \
            self.get_wp_specific_consumptions(self.mine,
                                              self.beneficiation,
                                              self.raw_rock_consumption)

    @staticmethod
    def get_raw_rock_consumption(mine, beneficiation):
        d = dict()
        for product in beneficiation.yields.keys():
            s = 0.
            for quality in mine.mine_composition.keys():
                s = s + mine.mine_composition[quality] * beneficiation.yields[product][quality]
            # TODO: check that values are indeed non null (in reality, can't be null since connected)
            d[product] = 1. / s
        return d

    @staticmethod
    def get_wp_specific_consumptions(mine, beneficiation, raw_rock_consumption):
        """Calculates specific consumptions related to considered mine-p axis instead of perrock quality"""
        result = Utils.multidict(beneficiation.outputs, beneficiation.inputs, {})
        for product in beneficiation.outputs:
            for item in beneficiation.inputs:
                s = 0.
                for quality in beneficiation.specific_consumptions[product].keys():
                    s = s + (beneficiation.yields[product][quality] * beneficiation.specific_consumptions[product][quality][item]).fillna(0)
                    result[product][item] = raw_rock_consumption[product] * s

        #computing equivalent opex per output product with same formula
        opex = dict()
        for product in beneficiation.outputs:
            o = 0
            for quality in beneficiation.main_inputs:
                o = o + (mine.mine_composition[quality] * beneficiation.opex[product][quality]).fillna(0)
            opex[product] = o
        return result, opex

    def reset(self):
        """
        Reset consumption and production based on sales plan schedule
        """
        self.mine.reset()
        self.beneficiation.reset()

    def compute_metrics(self):
        if -1 in self.mine.total_capex: # TODO: probably better to change it later into more robust condition
            self.mine.compute_total_capex()
            self.mine.compute_metrics()
        if -1 in self.beneficiation.total_capex:
            self.beneficiation.compute_total_capex()
            self.beneficiation.compute_metrics()

    def get_data(self, randomize=False):
        mine_data = self.mine.get_data(randomize)[0]
        beneficiation_data = self.beneficiation.get_data(randomize)[0]
        return [mine_data, beneficiation_data]

    def get_cost_pv(self, randomize=False):
        return self.mine.get_cost_pv(randomize) + self.beneficiation.get_cost_pv(randomize)

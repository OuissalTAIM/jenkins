# -*- coding: utf-8 -*-


import app.config.env as env
import pandas as pd


class Capacity:
    def __init__(self, capacity=0., unit=None, tenors=[], start=-float("inf"), end=float("inf")):
        self.capacity = capacity
        self.unit = unit
        self.start = start
        self.end = end
        self.capacities = None
        capacities = []
        for tenor in tenors:
            capacities.apend(capacity if (tenor >= start and tenor < end) else 0.)
        self.capacities = pd.Series(capacities, index=tenors)

    def schedule(self, tenors):
        capacities = []
        for tenor in tenors:
            capacities.append(self.capacity if (tenor >= self.start and tenor < self.end) else 0.)
        self.capacities = pd.Series(capacities, index=tenors)

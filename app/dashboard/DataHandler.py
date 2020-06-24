# -*- coding: utf-8 -*-


from app.data.DBAccess import DBAccess
import app.config.env as env
from pymongo import ASCENDING, DESCENDING
from collections import defaultdict
from app.tools.Logger import logger_dashboard as logger
import numpy as np


class DataHandler:
    def __init__(self):
        self.db = DBAccess(env.DB_RESULT_NAME)


class CostPVDataHandler(DataHandler):
    def __init__(self):
        super().__init__()

    def get_histogram(self):
        cost_pvs = self.db.get_fields(
            env.DB_GLOBAL_RESULT_COLLECTION_NAME,
            {"Cost PV": 1, "_id": 0},
            [("Cost PV", DESCENDING)]
        )
        points = [cost_pv["Cost PV"] for cost_pv in cost_pvs]
        return points

    def get_bars_by_entity(self, scenario):
        detailed = self.db.get_records_with_mask(
            env.DB_DETAILED_RESULT_COLLECTION_NAME,
            {"Scenario": scenario},
            {"Moniker": 1, "Name": 1, "Cost PV": 1, "_id": 0}
        )
        bars = {}
        for detail in detailed:
            moniker = detail["Moniker"]
            if moniker in bars:
                logger.warning("%s already exists in scenario %s" % (moniker, scenario))
                #TODO: do not continue if entity is a clone /PAP/Safi/6.. /SAP/Safi/8..
                continue
            bars[moniker] = (detail["Name"], detail["Cost PV"])
        return bars


class OtherDataHandler(DataHandler):
    def __init__(self, items):
        super().__init__()
        self.items = items # ['Consumption', 'Raw water', 'volume']

    def get_histogram(self):
        items = self.db.get_fields(
            env.DB_DETAILED_RESULT_COLLECTION_NAME,
            {"Scenario": 1, ".".join(self.items): 1, "_id": 0},
            [],
            20000
        )
        histogram = defaultdict(lambda: 0)
        for item in items:
            data = item
            for my_item in self.items:
                if my_item not in data:
                    data = {}
                    break
                data = data[my_item]
            histogram[item["Scenario"]] += np.npv(env.WACC, list(data.values()))
        points = []
        for key in histogram:
            #print("%s:%f" % (key, histogram[key]))
            points.append(histogram[key])
        return points

    def get_bars_by_entity(self, scenario):
        items = self.db.get_records_with_mask(
            env.DB_DETAILED_RESULT_COLLECTION_NAME,
            {"Scenario": scenario},
            {"Moniker": 1, "Name": 1, ".".join(self.items): 1, "_id": 0}
        )
        bars = {}
        for item in items:
            moniker = item["Moniker"]
            if moniker in bars:
                logger.warning("%s already exists in scenario %s" % (moniker, scenario))
                #TODO: do not continue if entity is a clone /PAP/Safi/6.. /SAP/Safi/8..
                continue
            data = item
            for my_item in self.items:
                if my_item not in data:
                    data = {}
                    break
                data = data[my_item]
            bars[item["Name"]] = sum(data.values())
        return bars


def get_cost_pv_histogram():
    return CostPVDataHandler().get_histogram(), "$" #TODO: get the right unit

def get_item_histogram(path_to_item=[]):
    return OtherDataHandler(path_to_item).get_histogram(), "UNIT" #TODO: get the right unit

def get_by_entity_bar(scenario_id, path_to_item=[]):
    return OtherDataHandler(path_to_item).get_bars_by_entity(scenario_id), "UNIT" #TODO: get the right unit


if __name__ == "__main__":
    #dh = CostPVDataHandler()
    dh = OtherDataHandler(["Consumption", "Raw water", "volume"])
    #dh = OtherDataHandler(["Production", "Electricity", "volume"])
    #dh = OtherDataHandler(["Opex"])
    print("%d: %s" % (len(dh.get_histogram()), dh.get_histogram()))
    #print(dh.get_bars_by_entity(4))

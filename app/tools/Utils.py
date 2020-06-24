# -*- coding: utf-8 -*-


import json
from bson import ObjectId
import math
import numbers
from collections import Counter
from operator import add
from functools import reduce
from copy import copy
from app.config.env import PipelineLayer, MONIKER_SEPARATOR, COMBO_NODES_SEPARATION
import pandas as pd
from ast import literal_eval
from random import randrange
from collections import defaultdict


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def extract_unit(word, delimiter="["):
    return word[word.find(delimiter)+1:-1]


def get_capacity(node):
    return node.entity.capacity


def is_numeric(number):
    if number == None:
        return False
    if number.__class__ == str:
        if number.isdigit():
            return True
        if number.lstrip("+-").isdigit():
            return True
    if isinstance(number, numbers.Number):
        if math.isnan(number):
            return False
        return True
    return False


def add_cost_pvs(cost_pv1, cost_pv2):
    capex = reduce(add, (Counter(cost_pv) for cost_pv in [cost_pv1["capex"], cost_pv2["capex"]]))
    opex = reduce(add, (Counter(cost_pv) for cost_pv in [cost_pv1["opex"], cost_pv2["opex"]]))
    return {"capex": dict(capex), "opex": dict(opex)}


def from_nodes_to_names(scenario):
    names = []
    for path in scenario:
        nodes = []
        for node in path:
            nodes.append(node.name())
        names.append(nodes)
    return names


def multidict(*args):
    if len(args) == 1:
        return copy(args[0])
    out = {}
    for x in args[0]:
        out[x] = multidict(*args[1:])
    return out


def production_header(layer):
    if layer == PipelineLayer.MINE:
        return "composition"
    elif layer == PipelineLayer.BENEFICIATION:
        return "yield"
    elif layer == PipelineLayer.GRANULATION:
        return "ratio"
    return "pc"


def to_dict(time_serie, key, level=1):
    if level == 1:
        if isinstance(time_serie[key], pd.core.series.Series):
            time_serie[key] = time_serie[key].to_dict()
        return time_serie[key]
    for elt in time_serie:
        if key in time_serie[elt]:
            time_serie[elt][key] = to_dict(time_serie[elt], key, level - 1)
    return time_serie


def make_tuple(scenario_moniker):
    return literal_eval(scenario_moniker)


def make_list(scenario_moniker):
    return literal_eval(scenario_moniker)


def simulate_series(serie, min, max):
    try:
        for index, value in serie.items():
            serie[index] = value if value != 0 else simulate_range(min, max)
        return serie
    except:
        return serie


def simulate_range(min, max):
    return randrange(min, max)


def to_dict_and_simulate(dico, key, level=1, min=0, max=1000):
    if level == 1:
        if isinstance(dico[key], pd.core.series.Series):
            dico[key] = simulate_series(dico[key], min, max)
        return dico[key]
    for elt in dico:
        if key in dico[elt]:
            dico[elt][key] = to_dict_and_simulate(dico[elt], key, level - 1, min, max)
    return dico


def get_monikers_from_scenario(scenario):
    monikers_filter = []
    for option in scenario:
        for layer in option:
            for moniker in layer:
                if COMBO_NODES_SEPARATION in moniker:
                    mine_benef = moniker.split(COMBO_NODES_SEPARATION)
                    monikers_filter.append(mine_benef[0])
                    monikers_filter.append(mine_benef[1])
                else:
                    monikers_filter.append(moniker)
    return monikers_filter


def get_scenario_from_df(scenarios_df):
    scenarios_dic = {}
    for index, scenario in scenarios_df.iterrows():
        scenario_id = scenario["Scenario"]
        if isinstance(scenario["Moniker"], list):
            monikers = scenario["Moniker"]
        else:
            monikers = json.loads(json.loads(scenario["Moniker"]))
        scenario_monikers = []
        for layer in monikers:
            layer_monikers = []
            big_monikers = defaultdict(lambda: 0)
            for moniker in layer:
                tokens = moniker.split(MONIKER_SEPARATOR)
                if tokens[3][:3] == "NEW":
                    moniker_ = MONIKER_SEPARATOR.join(tokens[0:3] + ["XXX"] + tokens[4:])
                    big_monikers[moniker_] += 1
                else:
                    layer_monikers.append(moniker)
            for moniker in big_monikers:
                moniker_ = moniker.replace(MONIKER_SEPARATOR+"XXX"+MONIKER_SEPARATOR,
                                           MONIKER_SEPARATOR+str(big_monikers[moniker])+MONIKER_SEPARATOR)
                layer_monikers.append(moniker_)
            scenario_monikers.append(layer_monikers)
        scenarios_dic[scenario_id] = scenario_monikers
    return scenarios_dic

def trim_collection_name(name):
    return name.lower().replace(" ", "_").replace("/", ".").replace("&", "_")

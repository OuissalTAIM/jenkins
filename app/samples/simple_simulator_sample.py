# -*- coding: utf-8 -*-


from app.model.SimpleSimulator import *
from app.tools.Utils import from_nodes_to_names


if __name__ == "__main__":
    s = SimpleSimulator(None)
    s.build_graph()
    s.simulate([["Mine/BenGuerir", "Washplant/Youssoufia"]])
    scenarios = s.build_all_scenarios(["Mine/BenGuerir", "Mine/Youssoufia"], ["PAP/Safi"])
    for scenario in scenarios:
        s.simulate(from_nodes_to_names(scenario))
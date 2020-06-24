# -*- coding: utf-8 -*-



from app.data.DBAccess import DBAccess
from app.model.Simulator import *
import cProfile
from multiprocessing import Pool, TimeoutError, Process
from app.data.DBAccess import DBAccess
from app.model.GranulationSolver import GranulationSolver

def simulate(cycle=1, phase=0):
    db = DBAccess(env.DB_RESULT_NAME)
    db.clear_collection(env.DB_GLOBAL_RESULT_COLLECTION_NAME)
    db.clear_collection(env.DB_DETAILED_RESULT_COLLECTION_NAME)
    sim = Simulator()
    granulation_solver = GranulationSolver(sim.nodes,sim.sales_plan)
    granulation_results = granulation_solver.launch_granulation_solver()


if __name__ == "__main__":
    simulate(1, 0)


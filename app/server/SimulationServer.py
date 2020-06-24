# -*- coding: utf-8 -*-


import app.config.env as env
from app.server.Broker import Broker
import json
from app.data.DBAccess import DBAccess
import pymongo


class SimulationServer:
    """
    Class for sending tasks
    """

    def serve(self, cycle):
        """
        Crating tasks and sending to broker
        :param cycle:
        :return:
        """
        # reset scenarios table
        db = DBAccess(env.DB_RESULT_NAME)
        db.clear_collection(env.DB_GLOBAL_RESULT_COLLECTION_NAME)
        db.clear_collection(env.DB_DETAILED_RESULT_COLLECTION_NAME)
        db.clear_collection(env.DB_SENSITIVITY_COLLECTION_NAME)
        db.create_index(
            env.DB_GLOBAL_RESULT_COLLECTION_NAME,
            [("Cost PV", pymongo.DESCENDING), ("Scenario", pymongo.ASCENDING)]
        )
        db.create_index(
            env.DB_DETAILED_RESULT_COLLECTION_NAME,
            [("Scenario", pymongo.ASCENDING)]
        )
        db.save_to_db_no_check(env.DB_SENSITIVITY_COLLECTION_NAME, {"NH3": 0, "ACS": 0, "HCl": 0, "Raw water": 0,
                                                                    "Electricity": 0, "K09": 0, "Rock": 0,
                                                                    "Scenario": -1})

        data = []
        for i in range(cycle):
            data.append(json.dumps({
                "cycle": cycle,
                "phase": i,
                "db_name": env.DB_NAME,
                "logistics_lp": env.LOGISTICS_LP
            }))
        broker = Broker(env.RABBITMQ_SIMULATOR_QUEUE_NAME)
        broker.publish(data)

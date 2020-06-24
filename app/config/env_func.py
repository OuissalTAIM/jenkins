# -*- coding: utf-8 -*-


import app.config.env as env
from app.tools.Logger import logger_datamanager as logger


DATA_SERVICE_URL = "http://" + env.DATA_SERVICE_ADD + ":" + str(env.DATA_SERVICE_PORT)


def get_service_url(context):
    """
    Get url to data service
    :param context:
    :return: string
    """
    if env.DB_NAME is None:
        msg = "Database name is not defined!"
        logger.error(msg)
        raise Exception(msg)
    if context not in ["data", "results"]:
        msg = "%s is not a defined context, possible values are data or results" % context
        logger.error(msg)
        raise Exception(msg)
    return "%s/%s/%s/" % (DATA_SERVICE_URL, context, env.DB_NAME)


def reset_db_name(db_name):
    """
    Reset DB variables
    :param db_name: string
    :return: None
    """
    env.DB_NAME = db_name
    env.DB_RESULT_NAME = "%s_results" % db_name
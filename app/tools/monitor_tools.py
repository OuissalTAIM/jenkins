# -*- coding: utf-8 -*-


import http.client
import os
import subprocess

from app.data.Service import DATA_SERVICE
from app.server.ClientMemcached import memcached_client, update_cache
from app.server.SimulationWorker import SimulationWorker, logger, datetime
from pymemcache.client import base
from app.server.ResultWorker import ResultWorker
import app.config.env as env
from app.server.ManagerRabbit import ManagerRabbit
from app.config.env_func import reset_db_name


def start_data_service():
    """
    Get application of data
    :return: APPLICATION FLASK
    """
    logger.info("Start data service")
    return DATA_SERVICE.run(host=env.DATA_SERVICE_ADD, port=env.DATA_SERVICE_PORT)


def check_memcached():
    """
    Start memcachedd if not started
    :return: None
    """
    try:
        client = base.Client((env.MEMCACHED_SERVER, env.MEMCACHED_PORT))
        client.set('check', 'check')
        logger.info('memcached already started')
    except Exception as e:
        logger.warning('Start memcached server')
        subprocess.Popen(["%s\\app\\batches\\start_memcached.bat" % env.APP_FOLDER], shell=True)


def check_service_data():
    """
    Check url
    :return: string
    """
    try:
        conn = http.client.HTTPConnection(env.DATA_SERVICE_ADD, env.DATA_SERVICE_PORT)
        conn.request("GET", "/ack")
        response = conn.getresponse()
        logger.info('Check data service')
        if response.status == 200:
            return env.HTML_STATUS.OK.value
    except Exception as e:
        logger.error('Data service error: %s' % e)
        return env.HTML_STATUS.ERROR.value

def check_worker_result(q_name):
    """
    check if worker for result is already exist
    :param q_name: queue name of result (global or detailed)
    :return: Int
    """
    logger.info('Check worker if exist')
    manager_rabbit = ManagerRabbit()
    consumers_list = manager_rabbit.get_list_consumers()
    for consumer in consumers_list:
        if consumer['queue_name'] == q_name:
            return env.HTML_STATUS.OK.value

    return env.HTML_STATUS.ERROR.value


def check_max_worker(q_name):
    """
    check if number of worker equal max worker
    :param q_name: queue name of result (global or detailed)
    :return: Int
    """
    logger.info('Check max worker')
    manager_rabbit = ManagerRabbit()
    consumers_list = manager_rabbit.get_list_consumers()
    counter = 0
    for consumer in consumers_list:
        if consumer['queue_name'] == q_name:
            counter += 1

    return counter


def start_result_worker(queue_name, collecttion_name, db_name):
    """
    :param queue_name: RABBITMQ QUEUE NAME
    :param collecttion_name: COLLECTION NAME
    :return: None
    """
    logger.info('Start worker results')
    reset_db_name(db_name)
    worker = ResultWorker(queue_name, collecttion_name)
    worker.consume()


def add_worker(db_name):
    """
    add new worker and start consumer
    :return: None
    """
    logger.info('add worker')
    reset_db_name(db_name)
    worker = SimulationWorker()
    worker.consume()


def best_scenarios(step, db_name):
    """
    launch best scenario
    :param db_name: database name
    :param step: number of scenario selected by user
    :return: Int
    """
    logger.info('Launch best scenario')
    subprocess.Popen(["%s\\app\\batches\\best_scenarios.bat" % env.APP_FOLDER, "%i" % step, "%s" % db_name], shell=True)
    return env.HTML_STATUS.ERROR.value


def update_mongo_bi():
    """
    Update mongodb bi
    :return: Int
    """
    try:
        logger.info('Update mongodb bi')
        subprocess.Popen(['%s\\app\\batches\\mongodb_bi.bat' % env.APP_FOLDER], shell=True)
        # subprocess.Popen(["%s\\app\\dashboard\\tableau\\dashboard.twbx" % env.APP_FOLDER], shell=True)
        return env.HTML_STATUS.OK.value
    except Exception as e:
        logger.error("%s" % (str(e)))
        return env.HTML_STATUS.ERROR.value


def open_canvas():
    """
    Opne canvas
    :return: Int
    """
    try:
        os.system('start excel.exe "%s"' % (env.CANVAS_PATH))
        return env.HTML_STATUS.OK.value
    except Exception as e:
        logger.warning("Cannot launch canvas: %s" % (str(e)))
        return env.HTML_STATUS.ERROR.value


def purge_all():
    """
    Purge all queues
    :return: None
    """
    logger.info('Purge queues')
    list_q_name = [env.RABBITMQ_SIMULATOR_QUEUE_NAME, env.RABBITMQ_DETAILED_RESULT_QUEUE_NAME,
                   env.RABBITMQ_GLOBAL_RESULT_QUEUE_NAME]
    for q_name in list_q_name:
        manager_rabbit = ManagerRabbit()
        manager_rabbit.purge_queues(q_name)


def launch_backup():
    """
    Create backup before launch simulation
    :return: Int
    """
    try:
        logger.info("Create backup before")
        subprocess.Popen(["%s\\mongodump.exe  -d %s -o c:\\data\\backup" % (env.MONGO_SERVER_PATH, env.DB_RESULT_NAME)],
        shell=True)
        return env.HTML_STATUS.OK.value
    except Exception as e:
        logger.error("%s" % (str(e)))
        return env.HTML_STATUS.ERROR.value



def init_all_phase():
    """
    Init all phase with initial value
    :return: Int
    """
    logger.info("Init progress for all phase with initial value ")
    # for _ in range(env.RABBITMQ_MAX_WORKER):
    for phase in range(env.RABBITMQ_CYCLE):
        infos = {}
        infos[phase] = {
            "maxWorker": env.RABBITMQ_MAX_WORKER,
            'db_name': env.DB_NAME,
            'progress': '0',
            "total_scenario": "Waiting",
            "counter": "Waiting",
            'time_start': datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
        }
        update_cache("workers_info_%i" % phase, infos)
    return env.HTML_STATUS.OK.value

# -*- coding: utf-8 -*-
import time

from bson.json_util import dumps

from app.data.DBAccess import DBAccess
from app.model.Simulator import *
from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
from app.server.SimulationServer import SimulationServer
from app.config.env import DB_GLOBAL_RESULT_COLLECTION_NAME, RABBITMQ_GLOBAL_RESULT_QUEUE_NAME
from multiprocessing import Process
from app.tools.monitor_tools import *


MONITOR_SERVER = Flask(__name__)


images = ["mine.png", "beneficiation.png", "sap.png", "pap.png", "granulation.png"]


@MONITOR_SERVER.route('/')
def index():
    """
    Get dashboard  monitoring
    :return: template
    """
    assets_path = "/"
    dashboard_url = "http://127.0.0.1:5000/"
    manager_rabbit = ManagerRabbit()
    consumers = manager_rabbit.get_list_consumers()
    check_memcached()
    except_dbs = ['admin', 'config', 'local', env.MONITORING_DB_NAME]
    db_names = [database for database in DBAccess.get_dbs_names() if database not in except_dbs and '_results' not in database]
    return render_template('index.html', service_status=check_service_data(),
                           dashboard_url=dashboard_url,
                           db_names=db_names,
                           cycle=env.RABBITMQ_CYCLE, consumers=consumers,
                           images=images,
                           assets_path=assets_path,
                           nb_pr_page=env.MONITORING_NB_PAGE,
                           count_worker=check_max_worker(env.RABBITMQ_SIMULATOR_QUEUE_NAME),
                           global_result_worker=check_worker_result(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME),
                           detailed_result_worker=check_worker_result(RABBITMQ_DETAILED_RESULT_QUEUE_NAME),
                           queue_simulate=env.RABBITMQ_SIMULATOR_QUEUE_NAME,
                           canvas_url=env.CANVAS_URL,
                           logistics_lp=env.LOGISTICS_LP
                           )


@MONITOR_SERVER.route('/check-worker', methods=['POST', 'GET'])
def check_worker():
    """
    Get information for each Workers
    :return: JSON
    """
    manager_rabbit = ManagerRabbit()
    list_queues = manager_rabbit.get_list_queues()
    consumers = manager_rabbit.get_list_consumers()
    workers_info = dict()
    # get status best scenarios for current db_name
    best_scenarios_status = dict()

    except_dbs = ['admin', 'config', 'local', env.MONITORING_DB_NAME]
    db_names = [database for database in DBAccess.get_dbs_names() if
                database not in except_dbs and '_results' not in database]

    if ('db_name' in request.json) and (request.json['db_name'] is not None):
        best_scenarios_status[request.json['db_name']] = env.HTML_STATUS.OK.value
        if memcached_client.get(request.json['db_name']):
            best_scenarios_status[request.json['db_name']]=memcached_client.get(request.json['db_name'])
    else:
        return jsonify(status=env.HTML_STATUS.ERROR.value)

    # Status worker global results
    worker_global_result = check_worker_result(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME)

    # Status worker detailed results
    worker_detailed_result = check_worker_result(RABBITMQ_DETAILED_RESULT_QUEUE_NAME)


    # Count workers running
    count_worker = check_max_worker(env.RABBITMQ_SIMULATOR_QUEUE_NAME)

    for phase in range(env.RABBITMQ_CYCLE):
        if memcached_client.get("workers_info_%i" % phase):
            workers_info[phase] = memcached_client.get("workers_info_%i" % phase)[str(phase)]
    return jsonify(workersInfo=workers_info, list_queues=list_queues, consumers=consumers,
                   best_scenarios_status=best_scenarios_status, db_names=db_names,
                   worker_global_result=worker_global_result,
                   worker_detailed_result=worker_detailed_result,
                   count_worker=count_worker
                   )


@MONITOR_SERVER.route('/get-history/<context>', methods=['POST', 'GET'])
def get_history(context=None):
    """
    Get history with pagination for best scenarios and task monitor
    :param context: String (best or None)
    :return: JSON
    """
    if request.json['current_page'] and request.json['nb_pr_page']:
        db = DBAccess(env.MONITORING_DB_NAME)
        if context == 'best':
            collection = env.MONITORING_COLLECTION_HISTORY_BEST_NAME
        else:
            collection = env.MONITORING_COLLECTION_HISTORY_NAME
        list_history, total_items = db.get_records_with_pagination(collection=collection,
                                                      filter_=None,sort_key="_id", sort_direction=-1,
                                                      current_page=request.json['current_page'],
                                                      nb_pr_page=request.json['nb_pr_page'])
        return jsonify(listHistory=json.loads(dumps(list_history)), total_items=total_items)


@MONITOR_SERVER.route('/start-service', methods=['POST', 'GET'])
def start_service():
    """
    Start simulation
    :return: JSON
    """
    status = env.HTML_STATUS.ERROR.value
    try:
        if 'db_name' in request.json:
            db_name = request.json["db_name"]
            reset_db_name(db_name)
        else:
            return jsonify(status=status, mesasge="No database selected")
        # check service if already started check route /ack
        if check_service_data() == env.HTML_STATUS.ERROR.value:
            Process(target=start_data_service).start()
        status = env.HTML_STATUS.OK.value
    except Exception as inst:
        logger.warning(str(inst))

    return jsonify(status=status)


@MONITOR_SERVER.route('/start-global-result-worker', methods=['POST', 'GET'])
def start_global_result_worker_route():
    """
    Add global result worker if not exist
    :return: JSON
    """

    # check if worker already exist
    if check_worker_result(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME) == env.HTML_STATUS.OK.value:
        return jsonify(status=env.HTML_STATUS.OK.value)

    if 'db_name' in request.json:
        db_name = request.json["db_name"]
    else:
        return jsonify(status=env.HTML_STATUS.ERROR.value, mesasge="No database selected")

    Process(target=start_result_worker, args=(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME,
                                              DB_GLOBAL_RESULT_COLLECTION_NAME, db_name)).start()
    return jsonify(status=env.HTML_STATUS.OK.value, global_result_worker=check_worker_result(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME))


@MONITOR_SERVER.route('/start-detailed-result-worker', methods=['POST', 'GET'])
def start_detailed_result_worker_route():
    """
    Add detailed result worker if not exist
    :return: JSON
    """
    # check if worker already exist
    if check_worker_result(RABBITMQ_DETAILED_RESULT_QUEUE_NAME) == env.HTML_STATUS.OK.value:
        return jsonify(status=env.HTML_STATUS.OK.value)

    if 'db_name' in request.json:
        db_name = request.json["db_name"]
    else:
        return jsonify(status=env.HTML_STATUS.ERROR.value, mesasge="No database selected")

    Process(target=start_result_worker, args=(RABBITMQ_DETAILED_RESULT_QUEUE_NAME,
                                              DB_DETAILED_RESULT_COLLECTION_NAME, db_name)).start()
    return jsonify(status=env.HTML_STATUS.OK.value, detailed_result_worker=check_worker_result(RABBITMQ_DETAILED_RESULT_QUEUE_NAME))


@MONITOR_SERVER.route('/start-simulator', methods=['POST', 'GET'])
def start_simulator():
    """
    Start simulation
    :return: JSON
    """
    try:
        if 'db_name' in request.json:
            reset_db_name(request.json["db_name"])
        else:
            return jsonify(status=env.HTML_STATUS.ERROR.value, mesasge="No database selected")

        env.LOGISTICS_LP = request.json["logistics_lp"]

        # launch_backup()

        if 'cycle' in request.json:
            env.RABBITMQ_CYCLE = request.json['cycle']
            simulator_server = SimulationServer()
            simulator_server.serve(env.RABBITMQ_CYCLE)
            status = env.HTML_STATUS.OK.value
        init_all_phase()
    except Exception as inst:
        status = env.HTML_STATUS.ERROR.value
        logger.warning(str(inst))
    return jsonify(status=status)


@MONITOR_SERVER.route('/add-worker', methods=['POST', 'GET'])
def add_worker_route():
    """
    Get Status worker
    :return: JSON
    """
    if 'db_name' not in request.json:
        return jsonify(status=env.HTML_STATUS.ERROR.value, message="No database selected")

    reset_db_name(request.json["db_name"])
    count_worker = check_max_worker(env.RABBITMQ_SIMULATOR_QUEUE_NAME)
    for _ in range(env.RABBITMQ_MAX_WORKER-count_worker):
        Process(target=add_worker, args=(env.DB_NAME,)).start()
    count_worker = check_max_worker(env.RABBITMQ_SIMULATOR_QUEUE_NAME)
    if count_worker == env.RABBITMQ_MAX_WORKER:
        return jsonify(status=env.HTML_STATUS.OK.value, count_worker=count_worker)
    return jsonify(status=env.HTML_STATUS.ERROR.value, count_worker=count_worker)


@MONITOR_SERVER.route('/purge', methods=['POST', 'GET'])
def purge_queues():
    """
    Purge all messages for each queues
    :return: JSON
    """
    purge_all()
    time.sleep(5)
    return jsonify(status=env.HTML_STATUS.OK.value)


@MONITOR_SERVER.route('/best-scenarios', methods=['POST', 'GET'])
def best_scenarios_route():
    """
    start compute best scenarios
    :return: JSON
    """
    if 'db_name' in request.json and "step" in request.json:
        best_scenarios(request.json['step'], request.json['db_name'])
    else:
        return jsonify(status=env.HTML_STATUS.ERROR.value, message="No database selected")


    return jsonify(status=env.HTML_STATUS.OK.value)


@MONITOR_SERVER.route('/launch-tableau', methods=['POST', 'GET'])
def update_mongo_bi_route():
    """
    Update mongo BI
    :return: JSON
    """
    return jsonify(status=update_mongo_bi())


@MONITOR_SERVER.route('/open-canvas', methods=['POST', 'GET'])
def open_canvas_route():
    """
    Open Canvas
    :return: JSON
    """

    return send_file('%sinputs/canvas_template.xlsm' % env.APP_FOLDER, attachment_filename="canvas_template.xlsm")
    return jsonify(status=open_canvas())

@MONITOR_SERVER.route('/stop-services', methods=['POST', 'GET'])
def stop_services():
    """
    Stop worker and restart RABBITMQ
    :return: JSON
    """
    purge_all()
    time.sleep(5)
    subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, 'stop_app'], shell=True)
    time.sleep(5)
    subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, 'reset'], shell=True)
    time.sleep(5)
    subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, 'start_app'], shell=True)
    time.sleep(5)

    # Launch all workers simulate
    for _ in range(env.RABBITMQ_MAX_WORKER):
        Process(target=add_worker, args=(env.DB_NAME,)).start()

    # Launch worker global result
    Process(target=start_result_worker, args=(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME,
                                              DB_GLOBAL_RESULT_COLLECTION_NAME, request.json['db_name'])).start()
    # Launch worker detailed results
    Process(target=start_result_worker, args=(RABBITMQ_DETAILED_RESULT_QUEUE_NAME,
                                              DB_DETAILED_RESULT_COLLECTION_NAME, request.json['db_name'])).start()

    return jsonify(status=env.HTML_STATUS.OK.value)


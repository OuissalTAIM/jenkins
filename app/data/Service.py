# -*- coding: utf-8 -*-


from app.data.DBAccess import DBAccess
from flask import Flask, jsonify, request
from app.tools.Utils import JSONEncoder, trim_collection_name
import json
import app.config.env as env
from app.config.env_func import reset_db_name
from app.tools.Logger import logger_dataservice as logger


DATA_SERVICE = Flask(__name__)


def get_records_into_dics(db_name, collection):
    """
    Get records from collection and transform into dictionary
    :param db_name: name of current database
    :param collection: name
    :return: JSON
    """
    reset_db_name(db_name)
    records = DBAccess(env.DB_NAME).get_all_records(collection)
    dic_records = {}
    for record in records:
        _id = record["_id"]
        record.pop("_id", None)
        dic_records[str(_id)] = record
    return json.dumps(JSONEncoder().encode(records))


@DATA_SERVICE.route("/data/<db_name>/<collection>/")
def get_records(db_name, collection):
    """
    Get records from collection
    :param db_name: name of current database
    :param collection: name
    :return: JSON
    """
    reset_db_name(db_name)
    records, _ = DBAccess(env.DB_NAME).get_all_records(collection)
    for record in records:
        _id = record["_id"]
        record.pop("_id", None)
    return jsonify(records)


@DATA_SERVICE.route("/results/<db_name>/<collection>/")
def get_all_results(db_name, collection):
    """
    Get results from collection
    :param db_name: name of current database
    :param collection: name
    :return: JSON
    """
    reset_db_name(db_name)
    records, _ = DBAccess(env.DB_RESULT_NAME).get_all_records(collection)
    for record in records:
        _id = record["_id"]
        record.pop("_id", None)
    return jsonify(records)


@DATA_SERVICE.route("/results/<db_name>/<collection>/<scenario_id>/")
def get_results(db_name, collection, scenario_id):
    """
    Get results from collection
    :param db_name: name of current database
    :param collection: name
    :param scenario_id: scenario id
    :return: JSON
    """
    reset_db_name(db_name)

    cursor = DBAccess(env.DB_RESULT_NAME).get_records(collection, {"Scenario": int(scenario_id)})
    records = []
    for record in cursor:
        record.pop("_id", None)
        records.append(record)
    return jsonify(records)


@DATA_SERVICE.route("/result/<db_name>/<collection>/<scenario_id>/")
def get_result(db_name, collection, scenario_id):
    """
    Get results from collection
    :param db_name: name of current database
    :param collection: name
    :param scenario_id: scenario id
    :return: JSON
    """
    reset_db_name(db_name)
    record = DBAccess(env.DB_RESULT_NAME).get_one_record(collection, {"Scenario": int(scenario_id)})
    _id = record["_id"]
    record.pop("_id", None)
    return jsonify(record)


@DATA_SERVICE.route("/data/save", methods=["POST"])
def save_data():
    try:
        reset_db_name(request.json['db_name'])
        records = request.json['table']
        db = DBAccess(env.DB_NAME)
        name_ = trim_collection_name(request.json['name'])
        db.clear_collection(name_)
        db.save_to_db(name_, records)
        return jsonify(status=env.HTML_STATUS.OK)
    except Exception as e:
        logger.error("Cannot save data: %s" % e)
        return jsonify(status=env.HTML_STATUS.ERROR)


@DATA_SERVICE.route("/ack", methods=["GET", "POST"])
def ack():
    return jsonify(status=env.HTML_STATUS.OK)

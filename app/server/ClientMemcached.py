# -*- coding: utf-8 -*-
import datetime

from pymemcache.client import base
import json
import app.config.env as env
from app.data.DBAccess import DBAccess


def json_serializer(key, value):
    if type(value) == str:
        return value, 1
    return json.dumps(value), 2


def json_deserializer(key, value, flags):
   if flags == 1:
       return value
   if flags == 2:
       return json.loads(value)
   raise Exception("Unknown serialization format")



memcached_client = base.Client((env.MEMCACHED_SERVER, env.MEMCACHED_PORT),
                               serializer=json_serializer, deserializer=json_deserializer)



def update_cache(key, value):
    """
    Update cache for key
    :param key: int|String
    :param value: dict|String
    :return: None
    """
    memcached_client.set(key, value)


def delete_cache(key):
    """
    Delete key in cache
    :param key: int|String
    :return: None
    """
    memcached_client.delete(key)


def insert_history(phase, task_to_save, status, message):
    """
    Insert history for monitoring
    :param phase: Int
    :param task_to_save: Dict
    :param status: Int
    :param message: String
    :return: None
    """
    query_insert = dict()
    query_insert['phase'] = phase
    query_insert['status'] = status
    query_insert['message'] = message
    query_insert['time_start'] = task_to_save['time_start']
    query_insert['time_end'] = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
    query_insert['db_name'] = task_to_save['db_name']
    query_insert['total_scenario'] = task_to_save['total_scenario']
    db = DBAccess(env.MONITORING_DB_NAME)
    db.save_to_db_no_check(env.MONITORING_COLLECTION_HISTORY_NAME, query_insert)
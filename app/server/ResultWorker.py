# -*- coding: utf-8 -*-
import pdb

from app.model.Simulator import *
from app.server.Worker import Worker
from app.tools.Logger import logger_results as logger
from app.data.DBAccess import DBAccess
import json
from datetime import datetime


class ResultWorker(Worker):
    """
    Class for distributing tasks among result workers
    """

    def __init__(self, queue_name, collection_name):
        super().__init__(queue_name)
        self.collection_name = collection_name

    def consume(self):
        """
        Send tasks to workers
        :param data: list
        :return: None
        """
        logger.info(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.basic_qos(prefetch_count=1) # send task to available worker
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.save_results)
        self.channel.start_consuming()


    def save_results(self, ch, method, properties, body):
        """
        Callback function called for each task
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return: None
        """
        logger.info(" [*] Saving results %r" % body[0:env.HEAD_DATA_BITS])
        message = body[env.HEAD_DATA_BITS:]
        message_db = str(body[env.HEAD_DATA_BITS:env.HEAD_DATA_BITS + env.DB_NAME_BITS], 'utf-8')
        dol_index = message_db.find("$")
        db_name = message_db[0:dol_index]
        data = json.loads(json.loads(message[dol_index + 1:]))
        if isinstance(data, dict) and "timestamp" not in data:
            data["timestamp"] = datetime.now()
        DBAccess('%s_results' % db_name).save_to_db_no_check(self.collection_name, data)
        logger.info(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)

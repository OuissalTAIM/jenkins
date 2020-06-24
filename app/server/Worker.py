# -*- coding: utf-8 -*-


import pika
from app.model.Simulator import *
import json


class Worker:
    """
    Class for distributing tasks among workers
    """

    def __init__(self, queue_name):
        """
        ctor
        """
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=env.RABBITMQ_SERVER, heartbeat=0, blocked_connection_timeout=600))
        self.channel = self.connection.channel()
        self.queue = queue_name
        self.channel.queue_declare(queue=self.queue, durable=True)

    def consume(self):
        """
        Send tasks to workers
        :param data: list
        :return: None
        """
        logger.info(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.basic_qos(prefetch_count=1) # send task to available worker
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.callback)
        self.channel.start_consuming()



    def callback(self, ch, method, properties, body):
        """
        Callback function called for each task
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return: None
        """
        logger.info(" [x] Received %r" % body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

# -*- coding: utf-8 -*-


import pika
import app.config.env as env
from app.tools.Logger import logger_simulation as logger


class Broker:
    """
    Class for distributing tasks among workers
    """

    def __init__(self, queue_name):
        """
        ctor
        """
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(env.RABBITMQ_SERVER))
        self.channel = self.connection.channel()
        self.queue = queue_name
        self.channel.queue_declare(queue=self.queue, durable=True, arguments={'queue-mode': 'lazy'})

    def publish(self, data, close_connection=True, head_data=False):
        """
        Send tasks to workers
        :param data: list
        :param close_connection: boolean
        :return: None
        """
        for message in data:
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2
                ))
            if head_data:
                logger.info(" [x] Sent %r" % message[0:env.HEAD_DATA_BITS])
            else:
                logger.info(" [x] Sent %r" % message)
        if close_connection:
            self.close()

    def close(self):
        self.connection.close()
        logger.warning(" [x] RabbitMQ Broker: connection closed")

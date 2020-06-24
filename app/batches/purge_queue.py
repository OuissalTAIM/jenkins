# -*- coding: utf-8 -*-


import pika
import sys
import app.config.env as env


if __name__ == "__main__":
    connection = pika.BlockingConnection(pika.ConnectionParameters(env.RABBITMQ_SERVER))
    ch = connection.channel()
    for queue_name in sys.argv[1:]:
        ch.queue_purge(queue_name)

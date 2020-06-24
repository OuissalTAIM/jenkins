# -*- coding: utf-8 -*-


from app.config.env_func import reset_db_name
from app.model.Simulator import *
import json
from app.server.Worker import Worker
from app.server.Broker import Broker
from app.graph.Node import NodeJSONEncoder
from app.tools.Logger import logger_simulation as logger


class SimulationWorker(Worker):
    """
    Class for distributing tasks among simulation workers
    """

    def __init__(self):
        super().__init__(env.RABBITMQ_SIMULATOR_QUEUE_NAME)

    def consume(self):
        """
        Send tasks to workers
        :param data: list
        :return: None
        """
        logger.info(' [*] Waiting for messages. To exit press CTRL+C')
        self.channel.basic_qos(prefetch_count=1) # send task to available worker
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.simulate)
        self.channel.start_consuming()

    def simulate(self, ch, method, properties, body):
        """
        Callback function called for each task
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return: None
        """
        logger.info(" [*] Running simulation %r" % body)

        data = json.loads(body)

        cycle = data["cycle"]
        phase = data["phase"]
        time_start = datetime.datetime.now().strftime("%d/%m/%y %H:%M:%S")
        if "db_name" in data:
            reset_db_name(data['db_name'])
        if "logistics_lp" in data:
            env.LOGISTICS_LP = data["logistics_lp"]
        detailed_publisher = ResultSaver(env.RABBITMQ_DETAILED_RESULT_QUEUE_NAME, env.RESULT_BATCHES_SIZE)
        global_publisher = ResultSaver(env.RABBITMQ_GLOBAL_RESULT_QUEUE_NAME, env.RESULT_BATCHES_SIZE)

        try:
            s = Simulator()
            s.simulate(cycle, phase, {"details": detailed_publisher, "global": global_publisher}, monitor=True,
                       logistics_lp=env.LOGISTICS_LP)

            detailed_publisher.close()
            global_publisher.close()
            logger.info(" [x] Done")
        except Exception as e:
            task_to_save = dict()
            task_to_save['db_name'] = env.DB_NAME
            task_to_save['time_start'] = time_start
            task_to_save['total_scenario'] = 0
            message = "Worker failed: %s" % (str(e))
            logger.warning("Worker failed: %s" % (str(e)))
            insert_history(phase=phase, task_to_save=task_to_save, status=env.HTML_STATUS.ERROR.value, message=message)
            global_publisher.close()
            detailed_publisher.close()
            logger.info(" [x] Done with error")
        ch.basic_ack(delivery_tag=method.delivery_tag)


class ResultSaver:
    """
    Helper class for saving results
    """

    def __init__(self, queue_name, db_batch_size):
        self.broker = Broker(queue_name)
        self.db_batch_size = db_batch_size
        self.datas = []
        self.counter = 0


    def save(self, data, task_id):
        self.counter += 1
        head_data = ("TASK {0:0" + str(env.HEAD_DATA_BITS - 5) + "d}").format(task_id)
        json_data = ''.join([head_data, env.DB_NAME, "$", json.dumps(NodeJSONEncoder().encode(data))])
        self.datas.append(json_data)
        if self.counter == self.db_batch_size or len(self.datas) <= self.db_batch_size:
            self.counter = 0
            self.broker.publish(self.datas, False, True)
            self.datas.clear()

    def close(self):
        self.broker.close()

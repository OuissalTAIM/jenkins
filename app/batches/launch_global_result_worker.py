# -*- coding: utf-8 -*-


from app.server.ResultWorker import ResultWorker
from app.config.env import DB_GLOBAL_RESULT_COLLECTION_NAME, RABBITMQ_GLOBAL_RESULT_QUEUE_NAME


if __name__ == "__main__":
    worker = ResultWorker(RABBITMQ_GLOBAL_RESULT_QUEUE_NAME, DB_GLOBAL_RESULT_COLLECTION_NAME)
    worker.consume()

# -*- coding: utf-8 -*-


import subprocess
import app.config.env as env


class ManagerRabbit:
    def __init__(self):
        self.queues = {}
        self.list_consumers = []

    def get_list_consumers(self):
        res = subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, "list_consumers"],
                               shell=True, stdout=subprocess.PIPE)
        list_consumers, _ = res.communicate()
        list_consumers = str(list_consumers, encoding="utf-8").replace('\t', '#').splitlines()[2:]
        for cs in list_consumers:
            cs_tokens = cs.split("#")
            len_tokens = len(cs_tokens)
            consumer = {
                'queue_name': cs_tokens[0] if len_tokens > 1 else '',
                'channel_pid': cs_tokens[1] if len_tokens > 2 else '',
                'consumer_tag': cs_tokens[2] if len_tokens > 3 else '',
                'ack_required': cs_tokens[3] if len_tokens > 4 else '',
                'prefetch_count': cs_tokens[4] if len_tokens > 5 else '',
                'active': cs_tokens[5] if len_tokens > 6 else '',
                'arguments': cs_tokens[6] if len_tokens > 7 else ''
            }
            self.list_consumers.append(consumer)
        return self.list_consumers

    def get_list_queues(self):
        res = subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, "list_queues"],
                               shell=True, stdout=subprocess.PIPE)
        lists_msgs_and_q_name, _ = res.communicate()
        lists_msgs_and_q_name = str(lists_msgs_and_q_name, encoding="utf-8").replace('\t', '#').splitlines()[3:]

        for name_mg in lists_msgs_and_q_name:
            item_split = name_mg.split("#")
            q_name = item_split[0]
            q_msg_number = item_split[1]
            self.queues[q_name] = q_msg_number
        return self.queues

    def purge_queues(self, q_name):
        subprocess.Popen(["%s\\rabbitmqctl.bat" % env.RABBITMQ_PATH, "purge_queue", q_name],
                         shell=True, stdout=subprocess.PIPE)
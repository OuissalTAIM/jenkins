# -*- coding: utf-8 -*-

import requests

from app.config.env_func import get_service_url


class Driver:
    @staticmethod
    def get_data(name):
        data_service_url = get_service_url(context="data")
        url = "%s%s" % (data_service_url, name)
        return requests.get(url).json()

    @staticmethod
    def get_results(collection, filter=None):
        results_service_url = get_service_url(context="results")
        if filter == None:
            url = "%s%s" % (results_service_url, collection)
        else:
            url = "%s%s/%s" % (results_service_url, collection, filter)
        return requests.get(url).json()

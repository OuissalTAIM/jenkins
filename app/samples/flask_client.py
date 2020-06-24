# -*- coding: utf-8 -*-


import requests
from app.config.env import DATA_SERVICE_URL


def get_collection():
    response = requests.get(DATA_SERVICE_URL + "mining_options")
    return response.text


if __name__ == "__main__":
    print(get_collection())
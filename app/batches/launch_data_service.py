# -*- coding: utf-8 -*-


from app.data.Service import DATA_SERVICE
import app.config.env as env


if __name__ == "__main__":
    DATA_SERVICE.run(host=env.DATA_SERVICE_ADD, port=env.DATA_SERVICE_PORT, debug=env.MODE_DEBUG)

# -*- coding: utf-8 -*-
import os


from app.dashboard.Monitor import MONITOR_SERVER
from app.config import env
import webbrowser

from app.data.DBAccess import DBAccess
from app.tools.monitor_tools import update_mongo_bi

if __name__ == '__main__':

    # os.environ["FLASK_ENV"] = env.MODE_APP
    DBAccess("dummy").clear_collection('dummy')
    DBAccess("dummy").save_to_db_no_check("dummy", [{"dummy": "dummy"}])
    webbrowser.open_new_tab("http://%s:%s" % (env.MONITORING_SERVER, env.MONITORING_PORT))
    MONITOR_SERVER.run(host=env.MONITORING_SERVER, port=env.MONITORING_PORT, debug=env.MODE_DEBUG)


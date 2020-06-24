# -*- coding: utf-8 -*-

import subprocess
import app.config.env as env


# Launch mongodb-bi
subprocess.Popen(['%s\\app\\batches\\mongodb_bi.bat' % env.APP_FOLDER], shell=True)


# Launch RabbitMQ
subprocess.Popen(['%s\\app\\batches\\rabbitmqctl.bat' % env.APP_FOLDER], shell=True)


# Launch Monitor
subprocess.Popen(["%s\\app\\batches\\monitor.bat" % env.APP_FOLDER], shell=True)
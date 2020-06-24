# -*- coding: utf-8 -*-


import logging
import app.config.env as env
import time
import os


def create_logger(name, log_level_file, log_level_console):
    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(env.LOG_LEVEL_FILE)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(env.LOG_FOLDER + ("%s_%s.log" % (name, time.strftime("%Y%m%d-%H%M%S"))))
    c_handler.setLevel(log_level_console)
    f_handler.setLevel(log_level_file)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    logger.propagate = False

    return logger


# Create log directory
if not os.path.exists(env.LOG_FOLDER):
    os.makedirs(env.LOG_FOLDER)

logger_simulation = create_logger("simulation", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_results = create_logger("results", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_dashboard = create_logger("dashboard", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_datamanager = create_logger("datamanager", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_sensitivity = create_logger("sensitivity", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_best = create_logger("best", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
logger_dataservice = create_logger("dataservice", env.LOG_LEVEL_FILE, env.LOG_LEVEL_CONSOLE)
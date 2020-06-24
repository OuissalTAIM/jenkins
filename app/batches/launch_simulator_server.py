# -*- coding: utf-8 -*-


from app.server.SimulationServer import SimulationServer
import app.config.env as env


if __name__ == "__main__":
    server = SimulationServer()
    server.serve(env.RABBITMQ_CYCLE)

from app.data.DBAccess import DBAccess
from app.model.Simulator import *
import cProfile
from multiprocessing import Pool, TimeoutError, Process
from app.data.DBAccess import DBAccess
from flask import Response, render_template

from flask import Flask
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

server = Flask(__name__)
db = DBAccess(env.DB_RESULT_NAME)
db.clear_collection(env.DB_GLOBAL_RESULT_COLLECTION_NAME)
db.clear_collection(env.DB_DETAILED_RESULT_COLLECTION_NAME)
simulator = Simulator()
@server.route('/')
def inddex():
    return 'Test'

app = dash.Dash(__name__,
                server=server,
                routes_pathname_prefix='/dash/',
                external_stylesheets=[dbc.themes.BOOTSTRAP]
                )

app.layout = html.Div(
    [
        dbc.Progress(id="progress", value=0, striped=True, animated=True),
        dcc.Interval(id="interval", interval=250, n_intervals=0),
    ]
)
#
# app.layout = html.Div(
#     html.H2("Progress"),
#     # progress
# )
def progress_worker(cycle, phase):
    for counter in simulator.simulate(cycle, phase, None, None, True):
        yield counter
        print("run", counter)
@app.callback(Output("progress", "value"), [Input("interval", "n_intervals")])
def advance_progress(n):
    cycle = 1
    phase = 0
    print(n)

    return next(progress_worker(cycle, phase))
    # print("n:", n)


    #     print(counter)
    #     return counter
    return min(n % 110, 100)

if __name__ == '__main__':
    cycle = 1
    phase = 0
    # counter = next()
    # progress_worker(cycle, phase)

    app.run_server(debug=True)


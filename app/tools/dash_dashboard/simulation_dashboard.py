import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import plotly.figure_factory as ff
import pandas as pd
import plotly.graph_objs as go
from app.data.DBAccess import DBAccess
from app.config import env
from flask_caching import Cache


#########################
# Dashboard Layout / View
#########################


def generate_table(dataframe, max_rows=10):
    '''Given dataframe, return template generated using Dash components'''
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))]
    )


# Set up Dashboard and create layout
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', 'https://codepen.io/chriddyp/pen/brPBPO.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})


def get_sales_plan():
    '''Returns all the scenario results that are stored in the database'''
    records = DBAccess(env.DB_NAME).get_all_records('sales_plan')
    # records = DBAccess(env.DB_RESULT_NAME).get_records("scenarios")
    records.pop("_id", None)
    return records


def load_simulation_options():
    opt_list = ['sales_plan', 'raw_materials']
    simul_options = (
        [{'label': scenario_key, 'value': scenario_key}
         for scenario_key in opt_list]
    )
    return simul_options


app.layout = html.Div([

    # Page Header
    html.Div([
        html.H2('JESA Mine2Land', ),
        html.H4('Scenario simulation program', )
    ]),

    dcc.Markdown('''
        ####     

        *Dashboard for simulation*

        *Choose siumlation parameters and launch*                   
        '''),

    # Dropdown Grid
    html.Div([
        html.Div([
            # Select scenario dropdown
            html.Div([
                html.Div('Select simulation options', className='three columns'),
                html.Div(dcc.Dropdown(id='simuloption-selector', options=load_simulation_options()),
                         className='nine columns'),
            ], style={'marginBottom': 50, 'marginTop': 25}),

        ], className='six columns'),

        # Empty
        html.Div(className='six columns'),
    ], className='twelve columns'),
    # Scenario summary Grid
    html.Div([

        # scenario results Table
        html.Div(
            dcc.Graph(id='option-results'),
            className='six columns', style={'marginBottom': 50, 'marginTop': 25}
        ),

    ]),
    ])

# Load Scenario results
@app.callback(
    Output(component_id='option-results', component_property='figure'),
    [
        Input(component_id='simuloption-selector', component_property='value')
    ]
)
def load_simul_option_from_db(simuloption):
    table = []
    # reading option current values from database
    records, ncol = DBAccess(env.DB_NAME).get_all_records(simuloption)
    records.pop("_id", None)
    table = ff.create_table(records, index=True, index_title=simuloption + ' current values', height_constant=20)
    table.layout.width = 650

    return table


# start Flask server
if __name__ == '__main__':
    app.run_server(host='127.0.0.1', port=5002, debug=True)

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


TIMEOUT = 0


#@cache.memoize(timeout=TIMEOUT)
def get_all_records():
    '''Returns all the scenario results that are stored in the database'''
    records = {}
    all_records, nb_docs = DBAccess(env.DB_RESULT_NAME).get_all_records("scenarios")
    for i in range(nb_docs):
        records.update(all_records[i])
        records.pop("_id", None)
    #records = DBAccess(env.DB_RESULT_NAME).get_records("scenarios")

    return records


def load_scenario_options():
    '''Actions to perform upon initial page load'''

    scenario_options = (
        [{'label': scenario_key, 'value': scenario_key}
         for scenario_key in list(get_all_records().keys())]
    )
    return scenario_options


app.layout = html.Div([

    # Page Header
    html.Div([
        html.H2('JESA Mine2Land', ),
        html.H4('Scenario simulation details', )
    ]),

    dcc.Markdown('''
        ####     

        *Visualisation of scenario metrics in details and summary*

        *The graph displays the evolution and comparaison between metrics*                   
        '''),

    # Dropdown Grid
    html.Div([
        html.Div([
            # Select scenario dropdown
            html.Div([
                html.Div('Select Scenario', className='three columns'),
                html.Div(dcc.Dropdown(id='scenario-selector', options=load_scenario_options()),
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
            dcc.Graph(id='scenario-results'),
            className='six columns', style={'marginBottom': 50, 'marginTop': 25}
        ),

        # Season Summary Table and Graph
        html.Div([
            # summary table
            dcc.Graph(id='scenario-summary'),

            # graph
            dcc.Graph(id='scenario-graph')
            # style={},

        ], className='six columns', style={'marginBottom': 50, 'marginTop': 25})
    ]),
])


###########################
# Data Manipulation / Model
###########################


def get_scenario_details(records, scenario_key):
    '''Returns multiple dicos : 1 dico for each relevant data'''
    raw_water_dic = {}
    elec_dic = {}
    K09_dic = {}
    ACP29_dic = {}
    # if scenario_key is None:
    #    scenario_key = list(records.keys())[0]

    # if scenario_key is not None:
    data_dic = records[scenario_key]
    k1 = list(data_dic.keys())[0]
    k2 = list(data_dic[k1]['PipelineLayer_PAP'].keys())[0]
    raw_water_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['Raw water']['consommation']
    elec_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['Electricity']['consommation']
    K09_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['K09']['consommation']
    ACP29_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['ACP29']['production']

    return raw_water_dic, elec_dic, K09_dic, ACP29_dic


def get_scenario_details_df(raw_water_dic, elec_dic, K09_dic, ACP29_dic):
    raw_water_df = pd.DataFrame.from_dict(raw_water_dic)
    elec_df = pd.DataFrame.from_dict(elec_dic)
    K09_df = pd.DataFrame.from_dict(K09_dic)
    ACP29_df = pd.DataFrame.from_dict(ACP29_dic)

    scenario_details_df = pd.concat([raw_water_df, elec_df, K09_df, ACP29_df], axis=1)
    scenario_details_df.columns = ['raw water', 'elec', 'K09', 'ACP29']
    return scenario_details_df


def calculate_scenario_summary(raw_water_dic, elec_dic, K09_dic, ACP29_dic):
    raw_water_df = pd.DataFrame.from_dict(raw_water_dic).sum()
    elec_df = pd.DataFrame.from_dict(elec_dic).sum()
    K09_df = pd.DataFrame.from_dict(K09_dic).sum()
    ACP29_df = pd.DataFrame.from_dict(ACP29_dic).sum()

    summary = pd.concat([raw_water_df, elec_df, K09_df, ACP29_df], axis=1)
    summary.columns = ['raw water', 'elec', 'K09', 'ACP29']
    summary.index = ['Total']
    return summary


# def draw_scenario_points_graph(results):
#     dates = results.index
#
#     figure = go.Figure(
#         data=[
#             go.Scatter(
#                 x=dates,
#                 y=results[i],
#                 mode='lines+markers',
#                 marker={
#                     'size': 15,
#                     'line': {'width': 0.5, 'color': 'white'}
#                 },
#                 name=i
#             ) for i in list(results.keys())
#         ],
#         layout=go.Layout(
#             title='Global Consumption & Production',
#             showlegend=True
#         )
#
#     )
#
#     return figure


def draw_scenario_points_graph(results):
    dates = results.index

    figure = go.Figure(
        data=[
            go.Bar(
                x=dates,
                y=results[i],
                name=i,
                opacity=0.75
            ) for i in list(results.keys())
        ],
        layout=go.Layout(
            title='Global Consumption & Production',
            showlegend=True,
            xaxis_title_text='Year',  # xaxis label
            yaxis_title_text='Volume',  # yaxis label
            bargap=0.2,  # gap between bars of adjacent location coordinates
            bargroupgap=0.1  # gap between bars of the same location coordinates
        )
    )
    return figure


#############################################
# Interaction Between Components / Controller
#############################################

# Load Scenario results
@app.callback(
    Output(component_id='scenario-results', component_property='figure'),
    [
        Input(component_id='scenario-selector', component_property='value')
    ]
)
def load_scenario_results(scenario):
    table = []

    # if scenario is not None:
    raw_water_dic, elec_dic, K09_dic, ACP29_dic = get_scenario_details(get_all_records(), scenario)
    if len(raw_water_dic) > 0:
        results = get_scenario_details_df(raw_water_dic, elec_dic, K09_dic, ACP29_dic)
        # table = generate_table(results, max_rows=20)
        table = ff.create_table(results, index=True, index_title='Scenario Results', height_constant=20)
        table.layout.width = 650

    return table


# Update Scenario Summary Table
@app.callback(
    Output(component_id='scenario-summary', component_property='figure'),
    [
        Input(component_id='scenario-selector', component_property='value')
    ]
)
def load_scenario_summary(scenario):
    table = []

    # if scenario is not None:
    raw_water_dic, elec_dic, K09_dic, ACP29_dic = get_scenario_details(get_all_records(), scenario)

    if len(raw_water_dic) > 0:
        summary = calculate_scenario_summary(raw_water_dic, elec_dic, K09_dic, ACP29_dic)
        table = ff.create_table(summary, index=True, index_title='Scenario Summary', height_constant=20)
        table.layout.width = 650

    return table


# Update Graph
@app.callback(
    Output(component_id='scenario-graph', component_property='figure'),
    [
        Input(component_id='scenario-selector', component_property='value')
    ]
)
def load_scenario_graph(scenario):
    figure = []
    # if scenario is not None :
    raw_water_dic, elec_dic, K09_dic, ACP29_dic = get_scenario_details(get_all_records(), scenario)

    results = get_scenario_details_df(raw_water_dic, elec_dic, K09_dic, ACP29_dic)

    if len(results) > 0:
        figure = draw_scenario_points_graph(results)

    return figure


# start Flask server
if __name__ == '__main__':
    app.run_server(host='127.0.0.1', port=5005, debug=True)

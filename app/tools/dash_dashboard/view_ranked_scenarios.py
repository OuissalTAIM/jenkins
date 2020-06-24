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
import dash_table

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
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']#, 'https://codepen.io/chriddyp/pen/brPBPO.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})


#TIMEOUT = 0


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

def load_func_options():
    rkg_functions = ['raw water', 'elec', 'K09', 'ACP29']
    return [
        {'label': rkg_fct, 'value': rkg_fct}
        for rkg_fct in rkg_functions
    ]


app.layout = html.Div([

    # Dropdown Grid
    html.Div([
        html.Div([

            html.H2('JESA Mine2Land',),
            html.H4('Scenario ranking',)
        ],

            className='eight columns'
        ),
        html.Div([
            dcc.Markdown('''
            ####         
                        
            *Visualisation tool that reads the whole set of scenarios stored in database and ranks them based on user's ranking choice.* 
            
            *Possible ranking functions are WATER, ELEC, K09 and ACP29*                   
            '''),

            # Select disc. func 1 dropdown
            html.Div([
                html.Div('Select ranking function #1: ', className='three columns'),
                html.Div(dcc.Dropdown(id='function1-selector', options=load_func_options()),
                         className='nine columns')
            ], style={'marginBottom': 50, 'marginTop': 25}),

            # Select disc. func 2 dropdown
            html.Div([
                html.Div('Select ranking function #2: ', className='three columns'),
                html.Div(dcc.Dropdown(id='function2-selector', options=load_func_options()),
                         className='nine columns')
            ], style={'marginBottom': 50, 'marginTop': 25}),
        ], className='six columns'),

        # Empty
        html.Div(className='six columns'),
    ], className='twelve columns'),

    # Ranked scenarios grid
    html.Div([

        # scenario results Table
        html.Div(
            dcc.Graph(id='scenario-results'),
            className='six columns'
        ),
    ]),
])


###########################
# Data Manipulation / Model
###########################

def get_all_scenario_details(records):
    '''Return a single dico with keys = metrics'''
    raw_water_dic = {}
    elec_dic = {}
    K09_dic = {}
    ACP29_dic = {}
    for scenario_key in list(records.keys()):
        data_dic = records[scenario_key]
        k1 = list(data_dic.keys())[0]
        k2 = list(data_dic[k1]['PipelineLayer_PAP'].keys())[0]
        raw_water_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['Raw water']['consommation']
        elec_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['Electricity']['consommation']
        K09_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['K09']['consommation']
        ACP29_dic[scenario_key] = data_dic[k1]['PipelineLayer_PAP'][k2]['ACP29']['production']

    return {'raw water': raw_water_dic, 'elec': elec_dic, 'K09': K09_dic, 'ACP29': ACP29_dic}


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


# Load functions in Dropdown
@app.callback(
    Output(component_id='function2-selector', component_property='options'),
    [
        Input(component_id='function1-selector', component_property='value')
    ]
)
def populate_function_selector(func1):
    rkg_functions = ['raw water', 'elec', 'K09', 'ACP29']
    if func1 in rkg_functions:
        rkg_functions.remove(func1)
    return [
        {'label': rkg_fct, 'value': rkg_fct}
        for rkg_fct in rkg_functions
    ]


# Rank all scenarios
@app.callback(
    Output(component_id='scenario-results', component_property='figure'),
    [
        Input(component_id='function1-selector', component_property='value'),
        Input(component_id='function2-selector', component_property='value')
    ]
)
def load_scenario_results(function1, function2):
    all_scenarios_metrics_dic = get_all_scenario_details(get_all_records())
    table = []
    #if function1 is not None and function2 is not None:
    func1_dic = all_scenarios_metrics_dic[function1]
    func1_df = pd.DataFrame.from_dict(func1_dic).sum()

    func2_dic = all_scenarios_metrics_dic[function2]
    func2_df = pd.DataFrame.from_dict(func2_dic).sum()
    metrics_df = pd.concat([func1_df, func2_df], axis=1)
    metrics_df.columns = [function1, function2]
    metrics_df = metrics_df.sort_values(by=[function1, function2], ascending=False)

    if len(metrics_df) > 0:
        table = ff.create_table(metrics_df, index=True, index_title='Ranked scenarios', height_constant=20)
        table.layout.width = 650

    return table



# df = load_scenario_results('raw water', 'elec')
# app.layout = dash_table.DataTable(
#     id='table',
#     columns=[{"name": i, "id": i} for i in df.columns],
#     data=df.to_dict("rows"),
# )


# start Flask server
if __name__ == '__main__':
    app.run_server(host='127.0.0.1', port=5000, debug=True)

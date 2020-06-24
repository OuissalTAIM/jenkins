# -*- coding: utf-8 -*-


import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import app.config.env as env
import pandas as pd
from dash.dependencies import Input, Output
from app.data.DataManager import DataManager
from app.graph.NodeFactory import NodeFactory
from functools import lru_cache
import json
import plotly.graph_objs as go
import app.dashboard.DataHandler as dh
from app.data.Client import Driver
from app.tools.Utils import make_list
from app.risk.RiskEngine import RiskEngine
import locale
import app.tools.Utils as Utils
locale.setlocale(locale.LC_ALL, 'German')

# Data
if env.DB_LOAD_FROM_SERVICE:
    scenarios_df = pd.DataFrame(Driver().get_results(env.DB_GLOBAL_BEST_RESULT_COLLECTION_NAME))
    scenario_detailed_df = pd.DataFrame(Driver().get_results(env.DB_DETAILED_BEST_RESULT_COLLECTION_NAME))
else:
    scenarios_df = pd.read_csv(env.APP_FOLDER + "outputs/global.csv")
scenarios_df.sort_values("Cost PV", inplace=True, ascending=True)
scenarios_ids = scenarios_df["Scenario"].tolist()

dm = DataManager()
dm.load_data()
nodes, _, _ = NodeFactory.load_entities(dm, None)
years_list = ["2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"]


def get_capex_Opex(scenario_id, year_id):
    capex_value = 0
    opex_value = 0
    water = 0
    electricity = 0
    gypsum = 0
    water_unit = ""
    electricity_unit = ""
    gypsum_unit = ""
    scenario = scenario_detailed_df[scenario_detailed_df["Scenario"] == scenario_id]
    for scenario_item in range(0, len(scenario)):
        try:
            capex_value += scenario.iloc[scenario_item]["Capex"][year_id]
        except:
            capex_value += 0
        try:
            opex_value += scenario.iloc[scenario_item]["Opex"][year_id]
        except:
            opex_value += 0
        try:
            water += scenario.iloc[scenario_item]["Consumption"]["Raw water"]["volume"][year_id]
            water_unit = scenario.iloc[scenario_item]["Consumption"]["Raw water"]["Unit"]
        except:
            water += 0
        try:
            electricity += scenario.iloc[scenario_item]["Consumption"]["Electricity"]["volume"][year_id]
            electricity_unit = scenario.iloc[scenario_item]["Consumption"]["Electricity"]["Unit"]
        except:
            electricity += 0
        try:
            gypsum += scenario.iloc[scenario_item]["Production"]["Gypsum"]["volume"][year_id]
            gypsum_unit = scenario.iloc[scenario_item]["Production"]["Gypsum"]["Unit"]
        except:
            gypsum += 0
    return capex_value, opex_value, water, electricity, gypsum, water_unit, electricity_unit, gypsum_unit


# raw_material_sensitivity


raw_materials_df = Driver().get_data("raw_materials")
raw_material_list = [line["Item"]for line in raw_materials_df]


def get_raw_material_sensitivity(scenario_id):
    shocks = {}
    for raw_material in raw_materials_df:
        item = raw_material["Item"]
        shocks[item] = 1
    risk_engine = RiskEngine()
    scenario = scenarios_df[scenarios_df["Scenario"] == scenario_id]
    scenarios_dic = Utils.get_scenario_from_df(scenario)
    deltas = risk_engine.compute_delta(scenarios_dic[scenario_id], shocks)
    return deltas



# Layers
dico = {
    "Mine": {
        "enum": env.PipelineLayer.MINE,
        "principal_color": "#DBB84D",
        "secondary_color": "#CC9900",
        "title": "Mining",
        "image": "mine.png",
        "box": None,
    },
    "WP": {
        "enum": env.PipelineLayer.BENEFICIATION,
        "principal_color": "#B89471",
        "secondary_color": "#996633",
        "title": "Beneficiation",
        "image": "beneficiation.png",
        "box": None,
    },
    "SAP": {
        "enum": env.PipelineLayer.SAP,
        "principal_color": "#DBDB4D",
        "secondary_color": "#CCCC00",
        "title": "SAP",
        "image": "sap.png",
        "box": None,
    },
    "PAP": {
        "enum": env.PipelineLayer.PAP,
        "principal_color": "#88A872",
        "secondary_color": "#548235",
        "title": "PAP",
        "image": "pap.png",
        "box": None,
    },
    "Granulation": {
        "enum": env.PipelineLayer.GRANULATION,
        "principal_color": "#C0C0C0",
        "secondary_color": "#A5A5A5",
        "title": "Granulation",
        "image": "granulation.png",
        "box": None,
    },
}

# App
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

scenarios_app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
scenarios_app.css.config.serve_locally = False

scenarios_app.css.append_css({"external_url": "https://fonts.googleapis.com/css?family=Roboto&display=swap"})


# Helpers
def create_card(title, contents, color):
    lignes = []
    for content in contents:
        lignes.append(html.P(children=[
            # html.Span(content['name'] + ': ', className="content_name"),
            html.Span(content['value'] if content['value'] else 'N/A', className="scen-content_name")
        ], style={'margin-bottom': '0.1em'}))
    card_contents = [
        html.H4(title, className="scen-card-title"),
        html.Div(children=lignes)
    ]
    card = dbc.Card(
        dbc.CardBody(
            card_contents
        ),
        style={'background-color': color, 'padding': '0'}, inverse=True
    )
    return (card)


def section_card(title, path_image, color):
    card = dbc.Card(
        dbc.CardBody(
            [
                html.Div(html.Img(src=scenarios_app.get_asset_url(path_image), className='section_image'),
                         className="card_image"),
                html.H4(title, className='section_card-title'),
            ], className="section_card"
        ),
        style={'backgroundColor': color}, inverse=True
    )
    return (card)


def get_supply_chain_layers():
    layers_layout = []
    for layer_str, layer_dico in dico.items():
        layers_layout.append(
            dbc.Col(
                children=[
                    section_card(layer_dico["title"], "%s" % layer_dico["image"], layer_dico["principal_color"])
                ],
                md=2, style={'padding': '0.5em', 'margin-top': '0.2em'}
            )
        )
    return tuple(layers_layout)


dico["Mine"]["box"], \
dico["WP"]["box"], \
dico["SAP"]["box"], \
dico["PAP"]["box"], \
dico["Granulation"]["box"] = get_supply_chain_layers()


# Scenarios helpers
def get_scenario_ids():
    return zip(scenarios_ids, list(range(1, len(scenarios_ids)+1)))


def get_moniker(scenario_id):
    scenario = scenarios_df[scenarios_df["Scenario"] == scenario_id]
    if scenario.empty:
        return ""
    moniker = scenario["Moniker"].iloc[0]
    return json.loads(json.loads(moniker))


def get_scenario(scenario_id):
    return scenarios_df[scenarios_df["Scenario"] == scenario_id]


@lru_cache(maxsize=128, typed=True)
def get_node(layer, moniker):
    for node in nodes[layer]:
        if node.moniker() == moniker:
            return node
    return None


def create_costpv_histogram():
    data, unit = dh.get_cost_pv_histogram()
    trace = go.Histogram(x=data, opacity=0.7, name="Cost PV",
                         # marker={"line": {"color": "#C2FF33", "width": 1000000}},
                         xbins={"size": 200000}, customdata=data, )
    layout = go.Layout(title=f"Cost PV Distribution", xaxis={"title": "Cost PV (%s)" % unit, "showgrid": False},
                       yaxis={"title": "Count", "showgrid": False},
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    return {"data": [trace], "layout": layout}


def create_rawwater_histogram():
    data, unit = dh.get_item_histogram(["Consumption", "Raw water", "volume"])
    trace = go.Histogram(x=data, opacity=0.7, name="Raw Water",
                         # marker={"line": {"color": "#C2FF33", "width": 10000}},
                         xbins={"size": 200}, customdata=data, )
    layout = go.Layout(title=f"Raw Water Distribution", xaxis={"title": "Raw Water (%s)" % unit, "showgrid": False},
                       yaxis={"title": "Count", "showgrid": False},
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    return {"data": [trace], "layout": layout}


def create_gypsum_histogram():
    data, unit = dh.get_item_histogram(["Production", "Gypsum", "volume"])
    trace = go.Histogram(x=data, opacity=0.7, name="Gypsum",
                         # marker={"line": {"color": "#C2FF33", "width": 1000}},
                         xbins={"size": 50}, customdata=data, )
    layout = go.Layout(title=f"Gypsum Distribution",
                       xaxis={"title": "Gypsum (%s)" % unit, "showgrid": False},
                       yaxis={"title": "Count", "showgrid": False},
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    return {"data": [trace], "layout": layout}


# Run

styles = {
    'mine-layer': {
        'border': '1px solid #ffdb58',
        'overflowX': 'scroll',
        'color': 'white',
        'background-color': '#ffdb58'
    },
    'beneficiation-layer': {
        'border': '1px solid brown',
        'overflowX': 'scroll',
        'color': 'white',
        'background-color': 'brown'
    },
    'sap-layer': {
        'border': '1px solid yellowgreen',
        'overflowX': 'scroll',
        'color': 'white',
        'background-color': 'yellowgreen'
    },
    'pap-layer': {
        'border': '1px solid lightgreen',
        'overflowX': 'scroll',
        'color': 'white',
        'background-color': 'lightgreen'
    },
    'granulation-layer': {
        'border': '1px solid grey',
        'overflowX': 'scroll',
        'color': 'white',
        'background-color': 'grey'
    }
}

scenarios_app.layout = html.Div(children=[

    html.Div([
        dbc.Row(
            children=[
                dbc.Row(
                    html.H1(children='Mine2Farm Dashboard', className='header'), style={'width': '100%'}
                ),
                dbc.Row(
                    html.Div(children=[
                        html.Div(
                            html.Img(src=scenarios_app.get_asset_url(dico[layer]["image"]), className='header-img',
                                     style={'background-color': dico[layer]['principal_color']}),
                            className='header-img-container')
                        for layer in
                        ["Mine", "WP", "SAP", "PAP", "Granulation"]
                    ], style={'margin-left': 'auto', 'margin-right': 'auto'}), style={'width': '100%'}
                )

            ], style={'background-color': 'rgb(53, 105, 117)',
                      'color': '#fafafa',
                      'font-family': 'sans-serif'}
        ),
        dbc.Row(
            children=[
                dbc.Col(dcc.Graph(
                    id="cost-pv-hist-graph",
                    figure=create_costpv_histogram(),
                ), md=4, style={'background-color': '#fafafa'}),
                dbc.Col(dcc.Graph(
                    id="raw-water-hist-graph",
                    figure=create_rawwater_histogram(),
                ), md=4, style={'background-color': '#fafafa'}),
                dbc.Col(dcc.Graph(
                    id="gypsum-hist-graph",
                    figure=create_gypsum_histogram(),
                ), md=4, style={'background-color': '#fafafa'}),

            ]
        ),
        dbc.Row(
            children=[
                dbc.Col(
                    children=[
                        dbc.Row(
                            id=layer_div_id,
                            children=[],
                            style={'padding': '1em'}
                        ) for layer_div_id in
                        ['mine-layer', 'beneficiation-layer', 'sap-layer', 'pap-layer', 'granulation-layer']
                    ], style={'padding': '1em', 'border': '3px solid black'}, md=6
                ),
                dbc.Col(
                    children=[
                        dbc.Row(
                            children=[
                                dbc.Col(children=[
                                    dbc.Row(
                                        html.H3(children='Money:'),
                                        style={'width': '100%'}
                                    ),
                                    dbc.Row(
                                            html.Table([
                                                html.Tr(id='cost-pv'),
                                                html.Tr(id='capex'),
                                                html.Tr(id='opex'),
                                                html.Tr(id='water-balance'),
                                                html.Tr(id='electricity-balance'),
                                                html.Tr(id='gypsum'),
                                            ], style={'width': '100%', 'font-family': 'serif','font-size': '1.2em'}),
                                    ),
                                    dbc.Row(
                                        html.H3(children='Raw materials:'),
                                        style={'width': '100%'}
                                    ),
                                    dbc.Row(
                                            html.Table([
                                                html.Tr(id=raw_material_id)
                                                for raw_material_id in raw_material_list
                                            ], style={'width': '100%', 'font-family': 'serif','font-size': '1.2em'})
                                            )

                                ],
                                            md=10),
                                dbc.Col(
                                    children=[
                                        html.Label('Scenarios Ranking'),
                                        dcc.Dropdown(
                                            options=[
                                                {'label': "%s" % ranking, 'value': scenario}
                                                for scenario, ranking in get_scenario_ids()
                                            ],
                                            value='0',
                                            id='scenario-id'
                                        ),
                                        html.Label('Year'),
                                        dcc.Dropdown(
                                            options=[
                                                {'label': years_element, 'value': years_element}
                                                for years_element in years_list
                                            ],
                                            value='0',
                                            id='year_id'
                                        ),
                                    ], md=2
                                )]

                        ),

                    ], style={'padding': '2em'}, md=6
                ),
            ]

        ),
        dbc.Row(
            children=[
                dbc.Col(
                    children=[
                        html.Div([dcc.Graph(
                            id="rawwater-entity-consumption-bar-graph",
                            figure={'data': []},
                        )], style={'background-color': '#fafafa', 'margin-top': '4em'})]),
                dbc.Col(
                    children=[
                        html.Div([dcc.Graph(
                            id="electricity-entity-production-bar-graph",
                            figure={'data': []},
                        )], style={'background-color': '#fafafa', 'margin-top': '4em'})
                    ])
        ])
    ], style={'backgroundColor': 'white', 'padding': '2em'}),

])


@scenarios_app.callback(
    [Output('mine-layer', 'children'),
     Output('beneficiation-layer', 'children'),
     Output('sap-layer', 'children'),
     Output('pap-layer', 'children'),
     Output('granulation-layer', 'children')],
    [Input(component_id='scenario-id', component_property='value')])
def display_supply_chain(scenario_id):
    scenario = []
    try:
        scenario_id = int(scenario_id)
        if scenario_id > 0:
            scenario = get_moniker(scenario_id)
    except:
        pass
    layers = {}
    for layer in scenario:
        for entity in layer:
            entities = [entity]
            if env.COMBO_NODES_SEPARATION in entity:
                entities = entity.split(env.COMBO_NODES_SEPARATION)
            for entity_ in entities:
                layer_id = entity_.split(env.MONIKER_SEPARATOR)[1]
                if layer_id not in layers:
                    layers[layer_id] = []
                layers[layer_id].append(entity_)
    all_layouts = []
    for layer_str, layer_dico in dico.items():
        cards_layout = [layer_dico["box"]]
        if layer_str not in layers:
            all_layouts.append(cards_layout)
            continue
        for moniker in layers[layer_str]:
            entity = get_node(layer_dico["enum"], moniker).entity
            card_layout = dbc.Col(
                create_card(
                    entity.get_location(),
                    [{'name': 'Name', 'value': entity.name}, {'name': 'Cost PV', 'value': entity.cost_pv}],
                    layer_dico["secondary_color"],
                ), md=1, style={'padding': '0.2em', 'padding-top': '0.5em', 'margin-top': '0.2em', 'font-size': '1.5em'}
            )
            cards_layout.append(card_layout)
        all_layouts.append([cards_layout[0]] + [dbc.Col(dbc.Row(cards_layout[1:]), md=10)])
    return tuple(all_layouts)


@scenarios_app.callback(
    [Output('cost-pv', 'children'),
     Output('capex', 'children'),
     Output('opex', 'children'),
     Output('water-balance', 'children'),
     Output('electricity-balance', 'children'),
     Output('gypsum', 'children')],
    [Input(component_id='scenario-id', component_property='value'),
     Input(component_id='year_id', component_property='value')])
def display_moneys(scenario_id, year_id):
    try:
        scenario = get_scenario(int(scenario_id))
        year = year_id
        if scenario.empty and year == 0:
            return [html.Td('Cost PV'), html.Td('NA')], \
                   [html.Td('CAPEX'), html.Td('NA')], \
                   [html.Td('OPEX'), html.Td('NA')], \
                   [html.Td('Water Balance'), html.Td('NA')], \
                   [html.Td('Electricity Balance'), html.Td('NA')], \
                   [html.Td('Gypsum'), html.Td('NA')],
        elif year == 0:
            return [html.Td('Cost PV'), html.Td(str(locale.format('%.2f', scenario['Cost PV'].iloc[0], True).replace('.', ' ')) + ' ' + scenario['Unit'].iloc[0])], \
                   [html.Td('CAPEX'), html.Td('NA')], \
                   [html.Td('OPEX'), html.Td('NA')], \
                   [html.Td('Water Balance'), html.Td('NA')], \
                   [html.Td('Electricity Balance'), html.Td('NA')], \
                   [html.Td('Gypsum'), html.Td('NA')],

        capex_value, opex_value, water, electricity, gypsum, water_unit, electricity_unit, gypsum_unit = get_capex_Opex(scenario_id, year_id)
        return [html.Td('Cost PV'), html.Td(str(locale.format('%.2f', scenario['Cost PV'].iloc[0], True).replace('.', ' ')) + ' ' + scenario['Unit'].iloc[0])], \
               [html.Td('CAPEX'), html.Td(str(locale.format('%.2f', capex_value, True).replace('.', ' ')))], \
               [html.Td('OPEX'), html.Td(str(locale.format('%.2f', opex_value, True).replace('.', ' ')))], \
               [html.Td('Water Balance'), html.Td(str(locale.format('%.2f', water, True).replace('.', ' ')) + ' ' + water_unit)], \
               [html.Td('Electricity Balance'), html.Td(str(locale.format('%.2f', electricity, True).replace('.', ' ')) + ' ' + electricity_unit)], \
               [html.Td('Gypsum'), html.Td(str(locale.format('%.2f', gypsum, True).replace('.', ' ')) + ' ' + gypsum_unit)],
    except:
        return [html.Td('Cost PV'), html.Td('NA')], \
               [html.Td('CAPEX'), html.Td('NA')], \
               [html.Td('OPEX'), html.Td('NA')], \
               [html.Td('Water Balance'), html.Td('NA')], \
               [html.Td('Electricity Balance'), html.Td('NA')], \
               [html.Td('Gypsum'), html.Td('NA')],


@scenarios_app.callback(
    [Output(raw_material_id, 'children') for raw_material_id in raw_material_list],
    [Input(component_id='scenario-id', component_property='value')])
def display_raw_materials(scenario_id):
    try:
        if scenario_id == 0:
            return [[html.Td(raw_material_id), html.Td('NA')] for raw_material_id in raw_material_list]
        raw_material_sensitivity = get_raw_material_sensitivity(scenario_id)
        return [[html.Td(raw_material_id), html.Td(next(str(locale.format('%.2f', raw_material_sensitivity[item], True).replace('.', ' '))+' '+[raw_materials_df[i]['Unit'] for i in range(0,len(raw_materials_df)) if raw_materials_df[i]['Item'] == item][0] for item in raw_material_sensitivity if item == raw_material_id))]for raw_material_id in raw_material_list]
    except:
        return [[html.Td(raw_material_id), html.Td('NA')] for raw_material_id in raw_material_list]


@scenarios_app.callback(
    Output('rawwater-entity-consumption-bar-graph', 'figure'),
    [Input(component_id='scenario-id', component_property='value')])
def create_raw_water_by_entity(scenario_id):
    if scenario_id == '':
        return ''
    data, unit = dh.get_by_entity_bar(scenario_id, ["Consumption", "Raw water", "volume"])
    trace = go.Bar(x=list(data.keys()), y=list(data.values()), name="Raw Water")
    layout = go.Layout(title=f"Raw Water Consumption by Entity",
                       xaxis={"title": "Entity", "showgrid": False},
                       yaxis={"title": "%s" % unit, "showgrid": False},
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    return {"data": [trace], "layout": layout}


@scenarios_app.callback(
    Output('electricity-entity-production-bar-graph', 'figure'),
    [Input(component_id='scenario-id', component_property='value')])
def create_electricity_by_entity(scenario_id):
    if scenario_id == '':
        return ''
    data, unit = dh.get_by_entity_bar(scenario_id, ["Production", "Electricity", "volume"])
    trace = go.Bar(x=list(data.keys()), y=list(data.values()), name="Electricity")
    layout = go.Layout(title=f"Electricity Production by Entity",
                       xaxis={"title": "Entity", "showgrid": False},
                       yaxis={"title": "%s" % unit, "showgrid": False},
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)')
    return {"data": [trace], "layout": layout}
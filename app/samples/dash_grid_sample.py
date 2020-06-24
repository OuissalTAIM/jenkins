import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import json
from functools import lru_cache
import app.config.env as env
from app.data.DataManager import DataManager
from app.graph.NodeFactory import NodeFactory

scenarios_df = pd.read_csv(env.APP_FOLDER + "outputs/global.csv")
values_df = pd.read_csv(env.APP_FOLDER + "inputs/metrics.csv")
dm = DataManager()
dm.load_data()
nodes, _, _ = NodeFactory.load_entities(dm, None)

dico = {
    "Mine": {
        "enum": env.PipelineLayer.MINE,
        "principal_color": "#DBB84D",
        "secondary_color": "#CC9900",
        "title": "Mining",
        "image": "mine.png",
        "box": None,
    },
    "Beneficiation": {
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


def get_scenario_ids():
    return scenarios_df["Scenario"].tolist()


def get_moniker(scenario_id):
    scenario = scenarios_df[scenarios_df["Scenario"] == scenario_id]
    if scenario.empty:
        return ""
    moniker = scenario["Moniker"].iloc[0]
    return json.loads(moniker)


def get_scenario(scenario_id):
    return scenarios_df[scenarios_df["Scenario"] == scenario_id]


@lru_cache(maxsize=128, typed=True)
def get_node(layer, moniker):
    for node in nodes[layer]:
        if node.moniker() == moniker:
            return node
    return None


external_stylesheets = [dbc.themes.BOOTSTRAP]
dg_app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


def create_card(title, contents, color):
    lignes = []
    for content in contents:
        lignes.append(html.P(children=[html.Span(content['name'] + ': ', className="content_name"),
                                       html.Span(content['value'], className="content_value")]))
    card_contents = [
        html.H4(title, className="card-title"),
        html.Br(),
        html.Div(children=lignes)
    ]
    card = dbc.Card(
        dbc.CardBody(
            card_contents
        ),
        style={'background-color': color}, inverse=True
    )
    return (card)


def section_card(title, path_image, color):
    card = dbc.Card(
        dbc.CardBody(
            [
                html.Div(html.Img(src=dg_app.get_asset_url(path_image), className='section_image'),
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


# Initialisation
dico["Mine"]["box"], \
dico["Beneficiation"]["box"], \
dico["SAP"]["box"], \
dico["PAP"]["box"], \
dico["Granulation"]["box"] = get_supply_chain_layers()

# App
dg_app.layout = html.Div(children=[
    html.H1(children='Mine2Farm Dashboard'),

    html.Label('List of scenarios'),
    dcc.Dropdown(
        options=[
            {'label': "%s" % scenario, 'value': scenario}
            for scenario in get_scenario_ids()
        ],
        value='0',
        id='scenario-id'
    ),

    html.Div([
        dbc.Row(
            children=[
                dbc.Col(
                    children=[
                        dbc.Row(
                            id=layer_div_id,
                            children=[],
                            style={'padding': '1em'}
                        )
                    ], style={'padding': '0.5em'}, md=6
                ),
                dbc.Col(
                    children=[

                    ], style={'padding': '0.5em'}, md=6
                ),
            ]

        )
        for layer_div_id in ['mine-layer', 'beneficiation-layer', 'sap-layer', 'pap-layer', 'granulation-layer']
    ], style={'backgroundColor': 'white', 'padding': '2em'}),

    html.Div([dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization'
            }
        }
    )])
])


@dg_app.callback(
    [Output('mine-layer', 'children'),
     Output('beneficiation-layer', 'children'),
     Output('sap-layer', 'children'),
     Output('pap-layer', 'children'),
     Output('granulation-layer', 'children')],
    [Input(component_id='scenario-id', component_property='value')])
def display_supply_chain(scenario_id):
    scenario = get_moniker(int(scenario_id))
    if scenario == '':
        scenario = []
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
            card_layout = dbc.Col(create_card(
                entity.get_location(),
                [{'name': 'Name', 'value': entity.name}, {'name': 'Cost PV', 'value': entity.cost_pv}],
                layer_dico["secondary_color"],
            ), md=2, style={'padding': '0.5em', 'margin-top': '0.2em'})
            cards_layout.append(card_layout)
        all_layouts.append(cards_layout)
    return tuple(all_layouts)


# Main
if __name__ == '__main__':
    dg_app.run_server(debug=True)

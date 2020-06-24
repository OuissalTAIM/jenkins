import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


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
                html.Div(html.Img(src=app.get_asset_url(path_image), className='section_image'),
                         className="card_image"),
                html.H4(title, className='section_card-title'),
            ], className="section_card"
        ),
        style={'backgroundColor': color}, inverse=True
    )
    return (card)


mining_cards = [
]

mining_cards_layout = []
section_card1 = section_card('Mining', 'mine.png', '#CC9900')
mining_cards_layout.append(dbc.Col(children=[section_card1], md=2, style={'padding': '0.3em'}))
for card in mining_cards:
    card_layout = create_card(card['title'],
                              card['values'],
                              card['color'])
    mining_cards_layout.append(dbc.Col(children=[card_layout], md=2))

beneficiatio_cards = [
]

beneficiatio_cards_layout = []
section_card1 = section_card('Beneficiatio', 'beneficiation.png', '#996633')
beneficiatio_cards_layout.append(dbc.Col(children=[section_card1], md=2, style={'padding': '0.3em'}))
for card in beneficiatio_cards:
    card_layout = create_card(card['title'],
                              card['values'],
                              card['color'])
    beneficiatio_cards_layout.append(dbc.Col(children=[card_layout], md=2, style={'padding': '0.5em'}))
graphRow0 = \
    dbc.Row(
        children=[
            dbc.Col(
                children=[
                    dbc.Row(
                        children=mining_cards_layout,
                        style={'padding': '1em'}
                    ),
                    dbc.Row(
                        children=beneficiatio_cards_layout,
                        style={'padding': '1em'}
                    )
                ], md=8
            )
        ]
    )
app.layout = html.Div([graphRow0], style={'backgroundColor': 'white'})
if __name__ == '__main__':
    app.run_server(debug=True)

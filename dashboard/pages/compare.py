# pages/compare.py
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash import dash_table

dash.register_page(__name__, path='/compare', name='Compare with Real Data', order=2, icon='bi bi-bar-chart-line')

def layout():
    real_entry = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Enter Real Observations")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(dcc.DatePickerSingle(id='real-date', date=None, display_format='YYYY-MM-DD', placeholder='YYYY-MM-DD')),
                            dbc.Col(dcc.Input(id='real-value', type='number', placeholder='Nilai Real', className='form-control'), md=4),
                            dbc.Col(dbc.Button("Add Data", id='add-real-btn', n_clicks=0, color='success'), md=2),
                        ],
                        className="g-2"
                    ),
                    html.Div(id='forecast-alert', style={'marginTop': 8})
                ]
            )
        ],
        className="mb-3"
    )

    table_card = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Real vs Forecast Table")),
            dbc.CardBody(
                [
                    dash_table.DataTable(
                        id='real-data-table',
                        columns=[
                            {"name": "Date", "id": "date"},
                            {"name": "Value", "id": "value"},
                            {"name": "Forecast", "id": "forecast"},
                            {"name": "Error", "id": "error"},
                            {"name": "Anomaly", "id": "anomaly"}
                        ],
                        data=[],
                        page_size=8,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '8px'},
                        style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                        style_data_conditional=[],
                        style_as_list_view=True
                    )
                ]
            )
        ],
        className="mb-3"
    )

    chart_card = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Compare Chart")),
            dbc.CardBody([dcc.Graph(id='compare-chart', style={'height': '480px'})])
        ],
        style={'borderRadius': 10}
    )

    return dbc.Container(
        [
            dbc.Row([dbc.Col(real_entry, md=4), dbc.Col(table_card, md=8)], className="g-3"),
            dbc.Row([dbc.Col(chart_card, md=12)], className="g-3 mt-2")
        ],
        fluid=True,
        style={"paddingTop":"18px"}
    )

layout = layout

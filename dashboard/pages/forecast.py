# pages/forecast.py
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/forecasting', name='Forecasting', order=1, icon='bi bi-graph-up')

def layout():


    controls_card = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Upload & Forecast Settings")),
            dbc.CardBody(
                [
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            html.I(className="bi bi-upload me-2"),
                            html.Strong("Drag & Drop or "),
                            html.A("Select CSV File")
                        ]),
                        style={
                            'width': '100%', 'height': '56px', 'lineHeight': '56px',
                            'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '8px',
                            'textAlign': 'center', 'marginBottom': '10px', 'background': '#fbfcfd'
                        },
                        multiple=False
                    ),
                    html.Div([
                            dcc.Store(id='upload-memory', storage_type='local'),

                             # ✅ Store untuk hasil forecasting
                            dcc.Store(id='forecast-memory', storage_type='local'),

                            dcc.Store(id='forecast-metadata', storage_type='local'),
                   

                            # ✅ Store untuk UI state (dropdown, pred_len, dsb)
                            dcc.Store(id='ui-memory', storage_type='local'),


                        html.Label('Pilih Model Chronos:'),
                        dcc.Dropdown(
                            id='chronos-model',
                            options=[
                                {'label': 'Chronos T5 Tiny', 'value': 'amazon/chronos-t5-tiny'},
                                {'label': 'Chronos T5 Mini', 'value': 'amazon/chronos-t5-mini'},
                                {'label': 'Chronos T5 Small', 'value': 'amazon/chronos-t5-small'},
                                {'label': 'Chronos T5 Base', 'value': 'amazon/chronos-t5-base'},
                                {'label': 'Chronos Bolt Tiny', 'value': 'amazon/chronos-bolt-tiny'},
                                {'label': 'Chronos Bolt Mini', 'value': 'amazon/chronos-bolt-mini'},
                                {'label': 'Chronos Bolt Small', 'value': 'amazon/chronos-bolt-small'},
                                {'label': 'Chronos Bolt Base', 'value': 'amazon/chronos-bolt-base'},
                                # {'label': 'Lag-Llama (zero-shot)', 'value': 'lag-llama'},
                            ],
                            value='amazon/chronos-t5-tiny',
                            clearable=False,
                            style={'marginTop': 6}
                        )
                    ], style={'marginBottom': 12}),
                    html.Div(id='select-columns'),
                    # html.Div(id='model-params', style={'marginTop': 8}), 
                    # di forecast.py
                    html.Div([
                        dcc.Input(id='pred-len', type='number', value=7, min=1)
                    ], style={'display': 'none'}),

                    html.Div(className="d-flex justify-content-between", children=[
                        html.Button('Forecast', id='forecast-btn', n_clicks=0, className="btn btn-primary"),
                        dbc.Button("Reset Upload", id="reset-upload", color="secondary", outline=True, className="ms-2")
                    ]),
                    html.Div(id="upload-hint", className="mt-2 text-muted", style={'fontSize': 12})
                ]
            )
        ],
        className="mb-3",
        style={'borderRadius': 10}
    )

    preview_card = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Preview Data")),
            dbc.CardBody([html.Div(id='preview-data')])
        ],
        className="mb-3"
    )

    result_card = dbc.Card(
        [
            dbc.CardHeader(html.Strong("Forecast Output")),
            dbc.CardBody([
                dcc.Loading(
                    id='loading-forecast',
                    type='circle',
                    children=[
                        html.Pre(id='forecast-log', style={'fontSize': '12px', 'whiteSpace': 'pre-wrap', 'background': '#f7f7f9', 'padding': '8px', 'borderRadius': '8px', 'minHeight': '54px'}),
                        html.Div(id='forecast-result', className='mt-3'),
                        dcc.Graph(id='forecast-chart', config={'displayModeBar': True}, style={'height': '420px', 'marginTop': 12}),
                        # dbc.Button("💾 Save Forecast",id="save-forecast-btn",color="success",className="mt-3",n_clicks=0 )

                        
                    ]
                )
            ])
        ],
        style={'borderRadius': 10}
    )

    return dbc.Container(
        [   
                dcc.Interval(
                            id='page-load-trigger',
                            interval=500,      # 0.5 detik
                            n_intervals=0,
                            max_intervals=1    # hanya jalan sekali setiap load
                                    ),

            dbc.Row([dbc.Col(controls_card, md=4), dbc.Col([preview_card, result_card], md=8)], className="g-3")
        ],
        fluid=True,
        style={"paddingTop":"18px"}
    )

layout = layout

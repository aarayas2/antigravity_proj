import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dash_table.Format import Format, Scheme
import pandas as pd
from utils import stats_manager

layout = html.Div([
    html.H2("Strategy Statistics", className="mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Minimum Win Rate Filter (%)"),
            dcc.Slider(
                id='win-rate-slider',
                min=0,
                max=100,
                step=5,
                value=50,
                marks={i: f'{i}%' for i in range(0, 101, 10)}
            )
        ], md=6)
    ], className="mb-4"),
    html.Div(id='stats-table-container')
])

@callback(
    Output('stats-table-container', 'children'),
    Input('win-rate-slider', 'value')
)
def update_stats_table(min_win_rate):
    data = stats_manager._storage.read()

    rows = []
    for entry in data:
        for ticker, stats in entry.items():
            date_begin = stats.get('date-begin', 'N/A')
            date_end = stats.get('date-end', 'N/A')

            for strategy, metrics in stats.items():
                if strategy in ['date-begin', 'date-end']:
                    continue

                win_rate_str = metrics.get('Win Rate', '0%')
                try:
                    win_rate_val = float(win_rate_str.strip('%')) / 100.0
                except ValueError:
                    win_rate_val = 0.0

                if (win_rate_val * 100) > min_win_rate:
                    
                    avg_return_str = metrics.get('Average Return', '0%')
                    try:
                        avg_return_val = float(avg_return_str.strip('%')) / 100.0
                    except ValueError:
                        avg_return_val = 0.0
                        
                    rows.append({
                        "Ticker": ticker,
                        "Date Begin": date_begin,
                        "Date End": date_end,
                        "Strategy": strategy,
                        "Total Return": metrics.get('Total Return', 'N/A'),
                        "Average Return": avg_return_val,
                        "Number of Trades": metrics.get('Number of Trades', 'N/A'),
                        "Win Rate": win_rate_val
                    })

    if not rows:
        return dbc.Alert("No data available or no strategies meet the filter criteria.", color="info")

    df = pd.DataFrame(rows)

    table = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[
            {"name": "Ticker", "id": "Ticker"},
            {"name": "Date Begin", "id": "Date Begin"},
            {"name": "Date End", "id": "Date End"},
            {"name": "Strategy", "id": "Strategy"},
            {"name": "Total Return", "id": "Total Return"},
            {"name": "Average Return", "id": "Average Return", "type": "numeric", "format": Format(precision=2, scheme=Scheme.percentage)},
            {"name": "Number of Trades", "id": "Number of Trades"},
            {"name": "Win Rate", "id": "Win Rate", "type": "numeric", "format": Format(precision=2, scheme=Scheme.percentage)}
        ],
        sort_action='native',
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#343a40',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data={
            'backgroundColor': '#2c3e50',
            'color': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#34495e'
            }
        ]
    )

    return table

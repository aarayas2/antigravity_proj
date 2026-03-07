import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
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
        ], md=6),
        dbc.Col([
            dbc.Label("Tickers"),
            dbc.InputGroup([
                dbc.Input(id="tickers-input", type="text", readonly=True),
                dbc.InputGroupText(
                    dcc.Clipboard(
                        target_id="tickers-input",
                        title="Copy to clipboard",
                        style={"cursor": "pointer"}
                    )
                )
            ])
        ], md=6)        
    ], className="mb-4"),
    html.Div(id='stats-table-container')
])

@callback(
    Output('stats-table-container', 'children'),
    Input('win-rate-slider', 'value')
)
def update_stats_table(min_win_rate):
    """
    Reads strategy statistics, filters by the minimum win rate, 
    and returns a formatted, sortable Dash DataTable.
    """
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
                        "Strategy": strategy,
                        "Total Return": metrics.get('Total Return', 'N/A'),
                        "Average Return": avg_return_val,
                        "Number of Trades": metrics.get('Number of Trades', 'N/A'),
                        "Win Rate": win_rate_val,
                        "Date Begin": date_begin,
                        "Date End": date_end
                    })

    if not rows:
        return html.Div([
            dbc.Alert("No data available or no strategies meet the filter criteria.", color="info"),
            # Empty table required so the virtualRowData callback doesn't fail on missing ID
            dag.AgGrid(id='stats-table', rowData=[], columnDefs=[])
        ])

    df = pd.DataFrame(rows)

    columnDefs = [
        {"field": "Ticker"},
        {"field": "Strategy"},
        {"field": "Total Return"},
        {
            "field": "Average Return",
            "valueFormatter": {"function": "d3.format('.2%')(params.value)"}
        },
        {"field": "Number of Trades"},
        {
            "field": "Win Rate",
            "valueFormatter": {"function": "d3.format('.2%')(params.value)"}
        },
        {"field": "Date Begin"},
        {"field": "Date End"}
    ]

    row_data = df.to_dict('records')
    dynamic_height = min(1200, 50 + len(row_data) * 50)

    table = dag.AgGrid(
        id='stats-table',
        rowData=row_data,
        columnDefs=columnDefs,
        dashGridOptions={"defaultColDef": {"sortable": True}},
        className="ag-theme-quartz-dark",
        style={"height": dynamic_height, "width": "100%"},
        getRowStyle={
            "styleConditions": [
                {
                    "condition": "params.node.rowIndex % 2 === 0",
                    "style": {"backgroundColor": "#222222", "color": "#f8f9fa"}
                },
                {
                    "condition": "params.node.rowIndex % 2 !== 0",
                    "style": {"backgroundColor": "#333333", "color": "#f8f9fa"}
                }
            ]
        }
    )

    return table


@callback(
    Output('tickers-input', 'value'),
    Input('stats-table', 'virtualRowData'),
    Input('stats-table', 'rowData')
)
def update_tickers_input(virtualRowData, rowData):
    """
    Updates the tickers input field based on the currently visible 
    and sorted rows in the data table.
    """
    # virtualRowData is None when the table is first initialized or not sorted/filtered.
    # We fallback to the full data if virtualRowData is not available.
    current_data = virtualRowData if virtualRowData is not None else rowData
    
    if not current_data:
        return ""
        
    unique_tickers = ";".join(list(dict.fromkeys(row.get("Ticker", "") for row in current_data if row.get("Ticker"))))
    return unique_tickers

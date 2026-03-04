import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import datetime
import os
from utils import load_data, apply_strategy, calculate_metrics
from strategy import STRATEGIES
from charting import create_strategy_chart
from persistence import StatsManager, JsonStatsStorage

# Initialize Persistence Layer
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
stats_manager = StatsManager(JsonStatsStorage(STATS_FILE))

# Dash App Initialization
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

app.title = "Interactive Stock Analysis"

# Default dates
max_date = datetime.date.today()
min_date = max_date - datetime.timedelta(days=365 * 5)
default_start = max_date - datetime.timedelta(days=365)

# Convert dates to ordinal for slider
min_date_ord = min_date.toordinal()
max_date_ord = max_date.toordinal()
default_start_ord = default_start.toordinal()
step_ord = 180 # ~6 months interval

# Layout
app.layout = dbc.Container([
    dcc.Store(id='mru-store', storage_type='local', data=[]),
    html.Datalist(id='mru-tickers'),

    html.H1("📈 Interactive Stock Strategy Analysis", className="mt-4 mb-4 text-center"),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("Stock Ticker Symbol"),
            dbc.Input(
                id="ticker-input", 
                type="text", 
                value="AAPL", 
                style={'textTransform': 'uppercase'},
                list="mru-tickers",
                autocomplete="off"
            )
        ], md=4),
        
        dbc.Col([
            dbc.Label(id="date-range-label", children="Date Range"),
            html.Div([
                dcc.RangeSlider(
                    id='date-range-slider',
                    min=min_date_ord,
                    max=max_date_ord,
                    step=step_ord,
                    value=[default_start_ord, max_date_ord],
                    marks={
                        min_date_ord: min_date.strftime('%Y-%m-%d'),
                        max_date_ord: max_date.strftime('%Y-%m-%d')
                    },
                    updatemode='drag'
                )
            ], style={'padding-top': '10px'})
        ], md=6),
        
        dbc.Col([
            dbc.Label("\u00A0"), # Non-breaking space for alignment
            dbc.Button("Compute Analysis", id="compute-btn", color="primary", className="w-100", n_clicks=0)
        ], md=2)
    ], className="mb-4 align-items-end"),

    dbc.Spinner(
        html.Div(id="output-container")
    )
], fluid=True, className="p-4")

@callback(
    Output("date-range-label", "children"),
    Input("date-range-slider", "value")
)
def update_date_label(value):
    start_date = datetime.date.fromordinal(value[0])
    end_date = datetime.date.fromordinal(value[1])
    return f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

@callback(
    Output("mru-tickers", "children"),
    Input("mru-store", "data")
)
def update_datalist(mru_data):
    if not mru_data:
        return []
    return [html.Option(value=ticker) for ticker in mru_data]

@callback(
    Output("output-container", "children"),
    Output("mru-store", "data"),
    Input("compute-btn", "n_clicks"),
    State("ticker-input", "value"),
    State("date-range-slider", "value"),
    State("mru-store", "data")
)
def update_analysis(n_clicks, ticker, date_range, mru_data):
    if not ticker or not date_range:
        return html.Div("Please provide ticker and date range."), dash.no_update

    ticker = ticker.upper()
    start_date_obj = datetime.date.fromordinal(date_range[0])
    end_date_obj = datetime.date.fromordinal(date_range[1])

    df = load_data(ticker, start_date_obj, end_date_obj)

    if df is None or df.empty:
        return dbc.Alert(f"Failed to load data for {ticker}. Please check the ticker symbol and try again.", color="danger"), dash.no_update
    
    # Update MRU data
    if mru_data is None:
        mru_data = []
    
    if ticker in mru_data:
        mru_data.remove(ticker)
    mru_data.insert(0, ticker)
    
    # Keep only the last 20 searched tickers
    mru_data = mru_data[:20]

    output_sections = []
    strategies_metrics = {}
    
    for strategy in STRATEGIES.keys():
        df_with_signals = apply_strategy(df.copy(), strategy)
        metrics = calculate_metrics(df_with_signals, strategy)

        # Collect metrics for persistence
        strategies_metrics[strategy] = {
            "Total Return": metrics["Total Return"],
            "Average Return": metrics["Average Return"],
            "Number of Trades": metrics["Number of Trades"],
            "Win Rate": metrics["Win Rate"]
        }

        # Metrics Section
        metrics_row = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Total Return", className="card-title"),
                html.H3(metrics["Total Return"], className="text-success" if float(metrics["Total Return"].strip('%')) >= 0 else "text-danger")
            ])), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Average Return", className="card-title"),
                html.H3(metrics["Average Return"], className="text-success" if float(metrics["Average Return"].strip('%')) >= 0 else "text-danger")
            ])), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Number of Trades", className="card-title"),
                html.H3(metrics["Number of Trades"], className="text-info")
            ])), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Win Rate", className="card-title"),
                html.H3(metrics["Win Rate"], className="text-warning")
            ])), md=3),
        ], className="mb-4")

        # Generate the Plotly figure
        fig = create_strategy_chart(df_with_signals, strategy, metrics)
        chart_section = dcc.Graph(figure=fig)

        section = html.Div([
            html.H3(f"Strategy Performance: {strategy} ({ticker})", className="mb-3"),
            metrics_row,
            html.Hr(),
            html.H3("Price Chart & Indicators", className="mb-3"),
            chart_section,
            html.Hr(style={'margin-top': '40px', 'margin-bottom': '40px', 'border-top': '2px solid white'})
        ])
        output_sections.append(section)

    # Trigger save logic if on Maximum date range
    if date_range[0] == min_date_ord and date_range[1] == max_date_ord:
        date_begin_str = start_date_obj.strftime('%Y-%m-%d')
        date_end_str = end_date_obj.strftime('%Y-%m-%d')
        stats_manager.save_stats(ticker, date_begin_str, date_end_str, strategies_metrics)

    return html.Div(output_sections), mru_data

if __name__ == '__main__':
    app.run(debug=True, port=8050)

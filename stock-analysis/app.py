import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import load_data, apply_strategy, calculate_metrics
from strategy import STRATEGIES
import pandas as pd

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
        ], md=3),
        
        dbc.Col([
            dbc.Label("Trading Strategy"),
            dcc.Dropdown(
                id="strategy-dropdown",
                options=[{"label": k, "value": k} for k in STRATEGIES.keys()],
                value="SMA Crossover",
                clearable=False,
                style={"color": "black"} # Ensure dropdown text is visible in dark mode
            )
        ], md=3),
        
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
        ], md=4),
        
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
    State("strategy-dropdown", "value"),
    State("date-range-slider", "value"),
    State("mru-store", "data")
)
def update_analysis(n_clicks, ticker, strategy, date_range, mru_data):
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

    df_with_signals = apply_strategy(df, strategy)
    metrics = calculate_metrics(df_with_signals, strategy)

    # Metrics Section
    metrics_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Total Return", className="card-title"),
            html.H3(metrics["Total Return"], className="text-success" if float(metrics["Total Return"].strip('%')) >= 0 else "text-danger")
        ])), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Number of Trades", className="card-title"),
            html.H3(metrics["Number of Trades"], className="text-info")
        ])), md=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Win Rate", className="card-title"),
            html.H3(metrics["Win Rate"], className="text-warning")
        ])), md=4),
    ], className="mb-4")

    # Plotly Figure
    needs_subplots = False
    if strategy in STRATEGIES:
        needs_subplots = STRATEGIES[strategy]["needs_subplots"]()

    if needs_subplots:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            row_heights=[0.7, 0.3],
                            vertical_spacing=0.08)
        main_row = 1
        sub_row = 2
    else:
        fig = go.Figure()
        # Dummy subplots interface compatibility
        class MockFig:
            def __init__(self, fig): self.fig = fig
            def add_trace(self, trace, row=None, col=None): self.fig.add_trace(trace)
            def update_layout(self, **kwargs): self.fig.update_layout(**kwargs)
            def add_vrect(self, **kwargs): self.fig.add_vrect(**kwargs)
            def add_hline(self, **kwargs): self.fig.add_hline(**kwargs)
        fig_wrapper = MockFig(fig)
        fig = fig_wrapper.fig # Overwrite for simplicity in charting later
        main_row = None
        sub_row = None

    # Main Candlestick Chart
    candlestick = go.Candlestick(x=df_with_signals.index,
                                 open=df_with_signals['Open'],
                                 high=df_with_signals['High'],
                                 low=df_with_signals['Low'],
                                 close=df_with_signals['Close'],
                                 name="Price")
    if main_row:
        fig.add_trace(candlestick, row=main_row, col=1)
    else:
        fig.add_trace(candlestick)

    # Add Strategy Traces
    if strategy in STRATEGIES:
        STRATEGIES[strategy]["add_traces"](fig, df_with_signals, main_row, sub_row)

    # Plot Buy/Sell signals on main chart
    buy_signals = pd.DataFrame()
    sell_signals = pd.DataFrame()
    if strategy in STRATEGIES:
        buy_signals, sell_signals = STRATEGIES[strategy]["get_signals"](df_with_signals)
    
    if not buy_signals.empty:
        trace = go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98,
                           mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'),
                           name='Buy Signal')
        if main_row: fig.add_trace(trace, row=main_row, col=1)
        else: fig.add_trace(trace)
        
    if not sell_signals.empty:
        trace = go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02,
                           mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'),
                           name='Sell Signal')
        if main_row: fig.add_trace(trace, row=main_row, col=1)
        else: fig.add_trace(trace)

    # Draw trade duration windows
    trades_history = metrics.get("Trades History", [])
    for trade in trades_history:
        # Green window for profitable trades, red for unprofitable
        color = "green" if trade['profit'] > 0 else "red"
        if main_row:
            fig.add_vrect(
                x0=trade['entry_date'], x1=trade['exit_date'],
                fillcolor=color, opacity=0.2,
                layer="below", line_width=0,
                row=main_row, col=1
            )
        else:
            fig.add_vrect(
                x0=trade['entry_date'], x1=trade['exit_date'],
                fillcolor=color, opacity=0.2,
                layer="below", line_width=0
            )

    # Layout updates
    fig.update_layout(height=700, template="plotly_dark",
                      xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=0, t=30, b=0))
    if main_row:
         fig.update_xaxes(rangeslider_visible=False) # Ensure rangeslider off for all subplots

    chart_section = dcc.Graph(figure=fig)

    return html.Div([
        html.H3(f"Strategy Performance: {strategy} ({ticker})", className="mb-3"),
        metrics_row,
        html.Hr(),
        html.H3("Price Chart & Indicators", className="mb-3"),
        chart_section
    ]), mru_data

if __name__ == '__main__':
    app.run(debug=True, port=8050)

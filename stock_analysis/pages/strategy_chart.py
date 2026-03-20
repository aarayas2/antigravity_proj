"""
Strategy Chart Page
Provides the layout and callbacks for analyzing and charting various trading strategies.
"""
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import datetime
import concurrent.futures

from utils import load_data, apply_strategy, calculate_metrics, stats_manager
from utils import get_date_ranges
from strategy import STRATEGIES
from charting import create_strategy_chart

def run_analysis_for_ticker(
    ticker: str,
    start_date_obj: datetime.date,
    end_date_obj: datetime.date,
    is_batch_mode: bool = False
):
    """
    Executes core analysis logic for a single ticker.
    Returns a dictionary of metrics if successful, or None if data could not be loaded.
    In batch mode, it bypasses generating Plotly figures and HTML components.
    """
    df = load_data(ticker, start_date_obj, end_date_obj)

    if df is None or df.empty:
        return None

    strategies_metrics = {}
    output_sections = []
    buy_signals = []

    def process_strategy(strategy):
        df_with_signals = apply_strategy(df, strategy)
        metrics = calculate_metrics(df_with_signals, strategy)

        strategy_metric = {
            "Total Return": metrics["Total Return"],
            "Average Return": metrics["Average Return"],
            "Number of Trades": metrics["Number of Trades"],
            "Win Rate": metrics["Win Rate"]
        }

        section = None
        has_buy_signal = False
        if is_batch_mode:
            if not df_with_signals.empty and 'Signal' in df_with_signals.columns:
                if df_with_signals.iloc[-1]['Signal'] == 1.0:
                    has_buy_signal = True

        if not is_batch_mode:
            # Metrics Section
            metrics_row = dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Total Return", className="card-title"),
                    html.H3(
                        f"{metrics['Total Return']:.2%}",
                        className=(
                            "text-success" if metrics["Total Return"] >= 0 else "text-danger"
                        )
                    )
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Average Return", className="card-title"),
                    html.H3(
                        f"{metrics['Average Return']:.2%}",
                        className=(
                            "text-success" if metrics["Average Return"] >= 0 else "text-danger"
                        )
                    )
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Number of Trades", className="card-title"),
                    html.H3(metrics["Number of Trades"], className="text-info")
                ])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H5("Win Rate", className="card-title"),
                    html.H3(f"{metrics['Win Rate']:.2%}", className="text-warning")
                ])), md=3),
            ], className="mb-4")

            # Generate the Plotly figure
            fig = create_strategy_chart(df_with_signals, strategy, metrics)
            chart_section = dcc.Graph(figure=fig, style={'width': '100%', 'height': '700px'})

            section = html.Div([
                html.H3(f"Strategy Performance: {strategy} ({ticker})", className="mb-3"),
                metrics_row,
                html.Hr(),
                html.H3("Price Chart & Indicators", className="mb-3"),
                chart_section,
                html.Hr(
                    style={
                        'margin-top': '40px',
                        'margin-bottom': '40px',
                        'border-top': '2px solid white'
                    }
                )
            ])

        return strategy, strategy_metric, section, has_buy_signal

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_strategy, STRATEGIES.keys()))

    for strategy, strategy_metric, section, has_buy_signal in results:
        strategies_metrics[strategy] = strategy_metric
        if section is not None:
            output_sections.append(section)
        if has_buy_signal:
            buy_signals.append(strategy)

    return {"metrics": strategies_metrics, "sections": output_sections, "buy_signals": buy_signals}

def layout():
    """
    Returns the Dash layout for the strategy chart page.
    """
    date_ranges = get_date_ranges()

    return html.Div([
        dcc.Store(id='mru-store', storage_type='local', data=[]),
        dcc.Store(id='initial-load', data=True),
        html.Datalist(id='mru-tickers'),

        dbc.Row([
            dbc.Col([
                dbc.Label("Stock Ticker Symbol"),
                dbc.Input(
                    id="ticker-input",
                    type="text",
                    value="AAPL",
                    style={'textTransform': 'uppercase'},
                    list="mru-tickers",
                    autocomplete="off",
                    debounce=False # Allow 'n_submit' to work smoothly
                )
            ], md=4),

            dbc.Col([
                dbc.Label(id="date-range-label", children="Date Range"),
                html.Div([
                    dcc.RangeSlider(
                        id='date-range-slider',
                        min=date_ranges['min_date_ord'],
                        max=date_ranges['max_date_ord'],
                        step=date_ranges['step_ord'],
                        value=[date_ranges['default_start_ord'], date_ranges['max_date_ord']],
                        marks={
                            date_ranges['min_date_ord']:
                                date_ranges['min_date'].strftime('%Y-%m-%d'),
                            date_ranges['max_date_ord']:
                                date_ranges['max_date'].strftime('%Y-%m-%d')
                        },
                        updatemode='drag'
                    )
                ], style={'padding-top': '10px'})
            ], md=6),

            dbc.Col([
                dbc.Label("\u00A0"), # Non-breaking space for alignment
                dbc.Button(
                    "Compute Analysis",
                    id="compute-btn",
                    color="primary",
                    className="w-100",
                    n_clicks=0
                )
            ], md=2)
        ], className="mb-4 align-items-end"),

        dbc.Spinner(
            html.Div(id="output-container")
        )
    ])

@callback(
    Output("date-range-label", "children"),
    Input("date-range-slider", "value")
)
def update_date_label(value):
    """
    Updates the date range label based on the slider value.
    """
    start_date = datetime.date.fromordinal(value[0])
    end_date = datetime.date.fromordinal(value[1])
    return f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

@callback(
    Output("mru-tickers", "children"),
    Input("mru-store", "data")
)
def update_datalist(mru_data):
    """
    Updates the options in the Most Recently Used (MRU) datalist.
    """
    if not mru_data:
        return []
    return [html.Option(value=ticker) for ticker in mru_data]

@callback(
    Output("output-container", "children"),
    Output("mru-store", "data"),
    Input("compute-btn", "n_clicks"),
    Input("ticker-input", "n_submit"),
    State("ticker-input", "value"),
    State("date-range-slider", "value"),
    State("mru-store", "data")
)
def update_analysis(n_clicks, n_submit, ticker, date_range, mru_data):
    """
    Handles computation of analysis and returns updated UI components and MRU list.
    """
    if not ticker or not date_range:
        return html.Div("Please provide ticker and date range."), dash.no_update

    ticker = ticker.upper()
    start_date_obj = datetime.date.fromordinal(date_range[0])
    end_date_obj = datetime.date.fromordinal(date_range[1])

    result = run_analysis_for_ticker(ticker, start_date_obj, end_date_obj, is_batch_mode=False)

    if result is None:
        return (
            dbc.Alert(
                f"Failed to load data for {ticker}. Please check the ticker symbol and try again.",
                color="danger"
            ),
            dash.no_update
        )

    # Update MRU data
    if mru_data is None:
        mru_data = []

    if ticker in mru_data:
        mru_data.remove(ticker)
    mru_data.insert(0, ticker)

    # Keep only the last 20 searched tickers
    mru_data = mru_data[:20]

    output_sections = result["sections"]
    strategies_metrics = result["metrics"]

    # Trigger save logic if on Maximum date range
    date_ranges = get_date_ranges()
    if (date_range[0] == date_ranges['min_date_ord'] and
            date_range[1] == date_ranges['max_date_ord']):
        date_begin_str = start_date_obj.strftime('%Y-%m-%d')
        date_end_str = end_date_obj.strftime('%Y-%m-%d')
        stats_manager.save_stats(ticker, date_begin_str, date_end_str, strategies_metrics)

    return html.Div(output_sections), mru_data




from urllib.parse import parse_qs

@callback(
    Output("ticker-input", "value"),
    Output("url", "search"),
    Output("initial-load", "data"),
    Output("compute-btn", "n_clicks"),
    Input("url", "search"),
    Input("ticker-input", "value"),
    State("initial-load", "data"),
    State("compute-btn", "n_clicks")
)
def sync_ticker(search, ticker, is_initial_load, n_clicks):
    """
    Synchronizes the ticker input value with the URL search parameters.
    """
    n_clicks = n_clicks or 0
    import dash
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else None

    parsed = parse_qs((search or "").lstrip('?'))
    url_ticker = parsed.get('ticker', [None])[0]

    # If it is the first time this callback fires
    if is_initial_load:
        if url_ticker:
            # URL takes precedence
            return url_ticker.upper(), dash.no_update, False, n_clicks + 1

        # Update URL with default input value if not present
        if ticker and ticker != "AAPL":
            return dash.no_update, f"?ticker={ticker}", False, n_clicks + 1
        return dash.no_update, dash.no_update, False, n_clicks + 1

    # Afterwards, normal sync
    if trigger == 'ticker-input.value':
        if ticker and ticker != url_ticker:
            return dash.no_update, f"?ticker={ticker}", False, dash.no_update
    elif trigger == 'url.search':
        if url_ticker and url_ticker != ticker:
            return url_ticker.upper(), dash.no_update, False, n_clicks + 1

    return dash.no_update, dash.no_update, False, dash.no_update

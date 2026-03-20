from .sma import apply_strategy as sma_apply, needs_subplots as sma_needs_subplots, add_traces as sma_add_traces, get_signals as sma_get_signals
from .BollingerBands import apply_strategy as bb_apply, needs_subplots as bb_needs_subplots, add_traces as bb_add_traces, get_signals as bb_get_signals
from .RSI import apply_strategy as rsi_apply, needs_subplots as rsi_needs_subplots, add_traces as rsi_add_traces, get_signals as rsi_get_signals
from .MACD import apply_strategy as macd_apply, needs_subplots as macd_needs_subplots, add_traces as macd_add_traces, get_signals as macd_get_signals

STRATEGIES = {
    "RSI": {
        "apply_strategy": rsi_apply,
        "needs_subplots": rsi_needs_subplots,
        "add_traces": rsi_add_traces,
        "get_signals": rsi_get_signals
    },
    "Bollinger Bands": {
        "apply_strategy": bb_apply,
        "needs_subplots": bb_needs_subplots,
        "add_traces": bb_add_traces,
        "get_signals": bb_get_signals
    },
    "MACD": {
        "apply_strategy": macd_apply,
        "needs_subplots": macd_needs_subplots,
        "add_traces": macd_add_traces,
        "get_signals": macd_get_signals
    },
    "SMA Crossover": {
        "apply_strategy": sma_apply,
        "needs_subplots": sma_needs_subplots,
        "add_traces": sma_add_traces,
        "get_signals": sma_get_signals
    }
}

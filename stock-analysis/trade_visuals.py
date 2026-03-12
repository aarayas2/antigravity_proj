"""
Trade Visualization Module
==========================

Architectural Overview:
-----------------------
This module introduces the Factory design pattern (via `TradeTooltipFactory`) to
encapsulate the complex logic required for generating interactive trade
duration windows with rich tooltips.

Refactoring Decision:
Plotly's `add_vrect` does not support interactive hover tooltips natively.
To achieve the required functionality, we use a shaded `go.Scatter` trace
with `fill='toself'`. Doing this inline would severely bloat the UI code.
By extracting this logic into a dedicated Factory, we achieve:
1. Separation of Concerns
2. Testability
3. Scalability

Error Handling and Robustness:
------------------------------
The factory includes safeguards against malformed or missing data:
- Missing Dates
- Missing Prices
- Division by Zero
- Type Hinting
"""

from typing import Dict, Any, Optional

import pandas as pd
import plotly.graph_objects as go  # pylint: disable=import-error


class TradeTooltipFactory:  # pylint: disable=too-few-public-methods
    """
    Factory class responsible for generating Plotly Scatter traces representing
    trade duration windows with interactive hover tooltips.
    """

    def __init__(self, y_min: float, y_max: float):
        """
        Initializes the factory with the vertical bounds for the shaded areas.

        Args:
            y_min (float): The lower bound for the shaded box on the Y-axis.
            y_max (float): The upper bound for the shaded box on the Y-axis.
        """
        self.y_min = y_min
        self.y_max = y_max
        self._y_coords = (y_min, y_max, y_max, y_min, y_min)

    def create_trace(self, trade: Dict[str, Any]) -> Optional[go.Scatter]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """
        Creates a go.Scatter trace for a single trade.

        Args:
            trade (Dict[str, Any]): A dictionary containing trade details
                (entry_date, exit_date, entry_price, exit_price, profit).

        Returns:
            Optional[go.Scatter]: The configured Scatter trace, or None if the
                trade data is critically invalid.
        """
        try:  # pylint: disable=broad-exception-caught
            # 1. Extract and Validate Dates
            entry_date = trade.get('entry_date')
            exit_date = trade.get('exit_date')

            if entry_date is None or pd.isna(entry_date):
                return None  # Cannot plot without a start date

            # Handle open trades (no exit date yet)
            is_open = False
            if pd.isna(exit_date) or exit_date is None:
                is_open = True
                # If we don't have a fallback in the dictionary (e.g., 'fallback_exit_date'),
                # we can't draw the rectangle. The caller should ensure a fallback date
                # if they want open trades drawn.
                fallback_exit_date = trade.get('fallback_exit_date')
                if fallback_exit_date is not None and not pd.isna(fallback_exit_date):
                    exit_date = fallback_exit_date
                else:
                    return None

            # 2. Extract and Validate Prices
            entry_price = trade.get('entry_price')
            exit_price = trade.get('exit_price')

            # Default missing prices to None for the template
            if pd.isna(entry_price):
                entry_price = None
            if pd.isna(exit_price):
                exit_price = None

            # 3. Calculate Percentage Gain
            pct_gain = 0.0
            pct_gain_str = "N/A"
            if entry_price is not None and exit_price is not None:
                if entry_price > 0:
                    pct_gain = ((exit_price - entry_price) / entry_price) * 100
                    pct_gain_str = f"{pct_gain:+.2f}%"
                else:
                    pct_gain_str = "N/A (Entry=0)"

            # 4. Determine Color
            profit = trade.get('profit', 0)
            if is_open:
                color = "rgba(128, 128, 128, 0.2)" # Gray for open
                hover_bg = "gray"
            else:
                color = "rgba(0, 128, 0, 0.2)" if profit > 0 else "rgba(255, 0, 0, 0.2)"
                hover_bg = "green" if profit > 0 else "red"

            # 5. Format Tooltip Strings
            date_format = "%Y-%m-%d"
            try:  # pylint: disable=broad-exception-caught
                if hasattr(entry_date, 'strftime'):
                    start_str = entry_date.strftime(date_format)
                else:
                    start_str = str(entry_date)
            except Exception:  # pylint: disable=broad-exception-caught
                start_str = "Unknown"

            try:  # pylint: disable=broad-exception-caught
                if is_open:
                    end_str = "Open"
                else:
                    if hasattr(exit_date, 'strftime'):
                        end_str = exit_date.strftime(date_format)
                    else:
                        end_str = str(exit_date)
            except Exception:  # pylint: disable=broad-exception-caught
                end_str = "Unknown"

            entry_p_str = f"${entry_price:.2f}" if entry_price is not None else "N/A"
            if exit_price is not None:
                exit_p_str = f"${exit_price:.2f}"
            else:
                exit_p_str = "Open" if is_open else "N/A"

            hover_text = (
                f"<b>Trade Duration</b><br>"
                f"Start: {start_str}<br>"
                f"End: {end_str}<br>"
                f"Entry Price: {entry_p_str}<br>"
                f"Exit Price: {exit_p_str}<br>"
                f"Return: {pct_gain_str}"
            )

            # 6. Construct the Polygon for the shaded area
            # We draw a rectangle using 4 points:
            # (start, ymin), (start, ymax), (end, ymax), (end, ymin), (start, ymin) to close
            x_coords = (entry_date, entry_date, exit_date, exit_date, entry_date)

            trace = go.Scatter(
                x=x_coords,
                y=self._y_coords,
                fill='toself',
                fillcolor=color,
                line={"width": 0},
                mode='lines',
                name='Trade',
                showlegend=False,
                hoveron='fills',
                hoverinfo='text',
                text=hover_text,
                hoverlabel={"bgcolor": hover_bg, "font_size": 12, "font_family": "Arial"}
            )

            return trace

        except Exception:  # pylint: disable=broad-exception-caught
            # In a production app, we would log this error.
            # print(f"Error generating trade tooltip trace: {e}")
            return None

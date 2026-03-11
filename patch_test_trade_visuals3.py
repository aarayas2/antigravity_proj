with open("stock-analysis/tests/test_trade_visuals.py", "r") as f:
    content = f.read()

# Let's write the class properly indented into the TestTradeTooltipFactoryAdditionalEdgeCases
if "def test_plotly_shape_generation_native_exception" not in content:
    with open("stock-analysis/tests/test_trade_visuals.py", "w") as f:
        # We need to insert it inside TestTradeTooltipFactoryAdditionalEdgeCases
        # We can just replace the last line "if __name__ == '__main__':"
        replacement = """
    def test_plotly_shape_generation_native_exception(self):
        \"\"\"Test native Plotly exception handling without mocking go.Scatter.\"\"\"
        class ExplosiveCoordinate:
            def __bool__(self):
                return True
            def __str__(self):
                return "2023-01-01"
            # Passing a string for profit triggers a TypeError when evaluating `profit > 0`
            # or we can pass a mocked object that raises an Exception when plotly interacts with it.
            # But wait, TypeError is an Exception!

        trade_bad_profit = {
            'entry_date': pd.Timestamp('2023-01-01'),
            'exit_date': pd.Timestamp('2023-01-02'),
            'entry_price': 100.0,
            'exit_price': 110.0,
            'profit': "10.0" # This string triggers TypeError during color determination `profit > 0` which goes to except Exception
        }

        # This will trigger an Exception natively inside create_trace without mocking go.Scatter
        trace = self.factory.create_trace(trade_bad_profit)
        self.assertIsNone(trace)

if __name__ == '__main__':
"""
        new_content = content.replace("if __name__ == '__main__':", replacement)
        f.write(new_content)

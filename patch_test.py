def test_native_plotly_shape_generation_exception(self):
    """Test native Plotly exception handling without mocking go.Scatter."""
    class ExplosiveCoordinate:
        def __bool__(self):
            return True
        def __str__(self):
            return "2023-01-01"
        def __format__(self, format_spec):
            raise TypeError("Plotly cannot format this")

    trade_bad_coords = {
        'entry_date': ExplosiveCoordinate(),
        'exit_date': ExplosiveCoordinate(),
        'entry_price': 100.0,
        'exit_price': 110.0,
        'profit': 10.0
    }
    trace = self.factory.create_trace(trade_bad_coords)
    self.assertIsNone(trace)

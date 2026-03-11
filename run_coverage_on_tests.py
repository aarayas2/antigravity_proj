import sys
import os
import coverage

def main():
    cov = coverage.Coverage(source=['stock-analysis/trade_visuals.py'])
    cov.start()

    import unittest
    # Dynamically import the test module
    sys.path.insert(0, os.path.abspath('stock-analysis'))
    import tests.test_trade_visuals

    # Run the specific test class
    suite = unittest.TestLoader().loadTestsFromModule(tests.test_trade_visuals)
    unittest.TextTestRunner(verbosity=2).run(suite)

    cov.stop()
    cov.save()
    cov.report(show_missing=True)

if __name__ == '__main__':
    main()

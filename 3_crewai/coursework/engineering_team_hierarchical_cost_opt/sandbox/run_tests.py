import unittest
import sys

# Load and run tests
loader = unittest.TestLoader()
suite = loader.discover('.', pattern='test_backend.py')
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)

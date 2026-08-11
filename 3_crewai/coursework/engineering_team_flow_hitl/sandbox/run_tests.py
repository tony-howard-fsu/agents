import unittest
import sys

# Load the test module
loader = unittest.TestLoader()
suite = loader.discover('.', pattern='test_backend.py')

# Run with verbose output
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Summary
print(f"\n{'='*70}")
print(f"Tests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Skipped: {len(result.skipped)}")

if result.failures:
    for test, traceback in result.failures:
        print(f"\nFAILURE: {test}")
        print(traceback)

if result.errors:
    for test, traceback in result.errors:
        print(f"\nERROR: {test}")
        print(traceback)

sys.exit(0 if result.wasSuccessful() else 1)

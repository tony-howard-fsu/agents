import unittest
import sys

# Import the test module
import test_backend

# Create a test suite
loader = unittest.TestLoader()
suite = loader.loadTestsFromModule(test_backend)

# Run with verbosity and capture output
stream = sys.stderr
runner = unittest.TextTestRunner(stream=stream, verbosity=2)
result = runner.run(suite)

# Print summary
print(f"\n\nTests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Skipped: {len(result.skipped)}")
print(f"Was successful: {result.wasSuccessful()}")

if result.failures:
    print("\n=== FAILURES ===")
    for test, traceback in result.failures:
        print(f"\n--- {test} ---")
        print(traceback)

if result.errors:
    print("\n=== ERRORS ===")
    for test, traceback in result.errors:
        print(f"\n--- {test} ---")
        print(traceback)

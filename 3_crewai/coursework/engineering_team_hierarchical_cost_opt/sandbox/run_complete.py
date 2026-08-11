import sys
print("STARTING_TEST_RUN", flush=True)

import unittest

# Import the test module
import test_backend

loader = unittest.TestLoader()
suite = loader.loadTestsFromModule(test_backend)

# Redirect stderr to stdout so we capture everything
import io
buf = io.StringIO()
runner = unittest.TextTestRunner(stream=buf, verbosity=2)
result = runner.run(buf)

output = buf.getvalue()
sys.stdout.write(output)
sys.stdout.flush()

print(f"\n\nTests_run: {result.testsRun}", flush=True)
print(f"Failures: {len(result.failures)}", flush=True)
print(f"Errors: {len(result.errors)}", flush=True)

if result.failures:
    print("\n=== FAILURES ===", flush=True)
    for test, traceback in result.failures:
        sys.stdout.write(f"\n--- {test} ---\n")
        sys.stdout.write(traceback)
        sys.stdout.flush()

if result.errors:
    print("\n=== ERRORS ===", flush=True)
    for test, traceback in result.errors:
        sys.stdout.write(f"\n--- {test} ---\n")
        sys.stdout.write(traceback)
        sys.stdout.flush()

print("\nDONE", flush=True)

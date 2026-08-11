import sys
import unittest
import test_backend

# Write everything to a file
with open("test_results.txt", "w") as f:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_backend)
    runner = unittest.TextTestRunner(stream=f, verbosity=2)
    result = runner.run(suite)

    f.write(f"\n\nTests run: {result.testsRun}\n")
    f.write(f"Failures: {len(result.failures)}\n")
    f.write(f"Errors: {len(result.errors)}\n")
    f.write(f"Was successful: {result.wasSuccessful()}\n")

    if result.failures:
        f.write("\n=== FAILURES ===\n")
        for test, traceback in result.failures:
            f.write(f"\n--- {test} ---\n")
            f.write(traceback)

    if result.errors:
        f.write("\n=== ERRORS ===\n")
        for test, traceback in result.errors:
            f.write(f"\n--- {test} ---\n")
            f.write(traceback)

print("Tests completed. See test_results.txt")

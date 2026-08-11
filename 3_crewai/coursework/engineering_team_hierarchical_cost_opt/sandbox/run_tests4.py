import unittest
import sys

# Run tests and capture output
loader = unittest.TestLoader()
suite = loader.discover('.', pattern='test_backend.py')
runner = unittest.TextTestRunner(verbosity=2, stream=open('/tmp/test_output.txt', 'w'))
result = runner.run(suite)

with open('/tmp/test_output.txt', 'r') as f:
    content = f.read()
print(content)
print("---SUMMARY---")
print(f"Tests run: {result.testsRun}")
print(f"Errors: {len(result.errors)}")
print(f"Failures: {len(result.failures)}")
for test, tb in result.errors:
    print(f"ERROR: {test}")
    print(tb)
for test, tb in result.failures:
    print(f"FAILURE: {test}")
    print(tb)

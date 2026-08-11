import sys
import io
from unittest import main, TestLoader, TextTestRunner

# Capture all output
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

loader = TestLoader()
suite = loader.discover('.', pattern='test_backend.py')
runner = TextTestRunner(verbosity=2, stream=sys.stdout)
result = runner.run(suite)

stdout_output = sys.stdout.getvalue()
stderr_output = sys.stderr.getvalue()

sys.stdout = old_stdout
sys.stderr = old_stderr

# Write results to a file
with open('test_results.txt', 'w') as f:
    f.write(stdout_output)
    f.write('\n')
    if stderr_output:
        f.write('STDERR:\n')
        f.write(stderr_output)
    f.write(f'\nTests run: {result.testsRun}\n')
    f.write(f'Failures: {len(result.failures)}\n')
    f.write(f'Errors: {len(result.errors)}\n')
    f.write(f'Was successful: {result.wasSuccessful()}\n')

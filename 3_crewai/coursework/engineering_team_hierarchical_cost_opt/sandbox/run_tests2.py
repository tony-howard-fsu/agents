import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "unittest", "test_backend.py", "-v"],
    capture_output=True,
    text=True,
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print(f"Return code: {result.returncode}")

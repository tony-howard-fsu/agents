import subprocess
import sys

result = subprocess.run(
    [sys.executable, "_validate.py"],
    capture_output=True,
    text=True,
    timeout=60,
)
print("=== STDOUT ===")
print(result.stdout)
print("=== STDERR ===")
print(result.stderr)
print("=== RETURN CODE ===")
print(result.returncode)

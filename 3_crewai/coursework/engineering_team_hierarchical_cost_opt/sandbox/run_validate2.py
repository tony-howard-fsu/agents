import subprocess
import sys

result = subprocess.run(
    ["uv", "run", "python", "_validate.py"],
    capture_output=True,
    text=True,
    timeout=120,
)
print("=== STDOUT ===", flush=True)
print(result.stdout, flush=True)
print("=== STDERR ===", flush=True)
print(result.stderr, flush=True)
print("=== RETURN CODE ===", flush=True)
print(result.returncode, flush=True)

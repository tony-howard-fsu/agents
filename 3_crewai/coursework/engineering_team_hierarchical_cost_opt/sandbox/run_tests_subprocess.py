import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "unittest", "test_backend.py", "-v"],
    capture_output=True,
    text=True,
    timeout=120,
)

# Write results to file
with open("test_results.txt", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn code: {result.returncode}")

# Also print so the harness can capture
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print(f"Return code: {result.returncode}")

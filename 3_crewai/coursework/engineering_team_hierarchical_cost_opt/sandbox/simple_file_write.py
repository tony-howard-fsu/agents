import sys

# Write directly to a file to capture everything
with open('/tmp/test_out.txt', 'w') as f:
    f.write("hello world\n")
    f.write(f"Python: {sys.version}\n")

print("done")

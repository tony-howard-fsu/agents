import sys
with open("/tmp/debug_out.txt", "w") as f:
    f.write("hello from test_minimal\n")
sys.stdout.write("hello from stdout\n")
sys.stderr.write("hello from stderr\n")

import sys
print("ALIVE", flush=True)
sys.stdout.write("ALSO_ALIVE\n")
sys.stdout.flush()
sys.stderr.write("ERR_TEST\n")
sys.stderr.flush()

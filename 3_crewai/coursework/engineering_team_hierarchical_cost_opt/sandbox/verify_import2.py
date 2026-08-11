import sys
sys.stdout = open("/tmp/stdout_log.txt", "w")
sys.stderr = open("/tmp/stderr_log.txt", "w")
print("Starting...")
try:
    import app
    print("PASS: app.py imported successfully")
    print(f"  manager exists: {hasattr(app, 'manager')}")
    print(f"  app object exists: {hasattr(app, 'app')}")
    print(f"  app title: {app.app.title}")
except Exception as e:
    import traceback
    print(f"FAIL: {e}")
    traceback.print_exc()
sys.stdout.close()
sys.stderr.close()

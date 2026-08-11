"""Minimal validation - prints directly."""
import sys
print("Starting validation...")
sys.stdout.flush()
try:
    import app
    print("PASS: app.py imported successfully")
    print(f"App title: {app.app.title}")
    print(f"Children count: {len(app.app.blocks)}")
except Exception as e:
    import traceback
    print(f"FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)
print("Done.")

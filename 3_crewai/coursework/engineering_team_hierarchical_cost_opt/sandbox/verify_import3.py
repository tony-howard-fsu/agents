"""Verify app.py imports correctly - writing results to file."""
import traceback

result = []

try:
    import app  # noqa: F401
    result.append("PASS: app.py imported successfully")
    result.append(f"  manager exists: {hasattr(app, 'manager')}")
    result.append(f"  app object exists: {hasattr(app, 'app')}")
    result.append(f"  app title: {app.app.title}")
except Exception as e:
    result.append(f"FAIL: {e}")
    result.append(traceback.format_exc())

# Write to file
with open("/tmp/verify_result.txt", "w") as f:
    f.write("\n".join(result))

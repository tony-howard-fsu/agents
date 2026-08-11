"""Quick test to verify app.py constructs without error."""
import sys
with open("/tmp/import_result.txt", "w") as f:
    f.write("Starting import test...\n")
    try:
        import app  # noqa: F401
        f.write("SUCCESS: app.py imported without errors.\n")
        f.write(f"Has 'app' attribute: {hasattr(app, 'app')}\n")
        f.write(f"Has 'manager' attribute: {hasattr(app, 'manager')}\n")
        f.write(f"App title: {app.app.title}\n")
        f.write("All checks passed!\n")
    except Exception as e:
        import traceback
        f.write(f"FAILED: {e}\n")
        f.write(traceback.format_exc())

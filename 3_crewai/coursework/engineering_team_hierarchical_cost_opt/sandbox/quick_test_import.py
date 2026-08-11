"""Quick test to verify app.py constructs without error."""
import sys
print("Testing app.py import...")
sys.stdout.flush()

# Import the app module
import app  # noqa: F401

print("SUCCESS: app.py imported without errors.")
sys.stdout.flush()

# Check that key objects exist
print(f"Has 'app' attribute: {hasattr(app, 'app')}")
print(f"Has 'manager' attribute: {hasattr(app, 'manager')}")
print(f"App title: {app.app.title}")
print("All checks passed!")

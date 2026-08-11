"""Quick environment check."""
import sys
print("Python:", sys.version, flush=True)
print("Executable:", sys.executable, flush=True)

try:
    import gradio
    print("gradio version:", gradio.__version__, flush=True)
except Exception as e:
    print("gradio import error:", e, flush=True)

try:
    from backend import AccountManager
    print("backend import OK", flush=True)
except Exception as e:
    print("backend import error:", e, flush=True)

try:
    from app import app
    print("app import OK", flush=True)
    print("app type:", type(app).__name__, flush=True)
except Exception as e:
    import traceback
    print("app import error:", e, flush=True)
    traceback.print_exc()

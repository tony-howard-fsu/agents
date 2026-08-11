import sys

# Write to a file to verify execution
with open("_output.txt", "w") as f:
    f.write("Script is running!\n")
    f.write(f"Python version: {sys.version}\n")
    f.flush()

# Try importing
try:
    import gradio as gr
    with open("_output.txt", "a") as f:
        f.write(f"gradio version: {gr.__version__}\n")
        f.flush()
except Exception as e:
    with open("_output.txt", "a") as f:
        f.write(f"gradio import error: {e}\n")
        f.flush()

try:
    from app import app
    with open("_output.txt", "a") as f:
        f.write(f"app type: {type(app).__name__}\n")
        if isinstance(app, gr.Blocks):
            f.write("SUCCESS: app is gr.Blocks\n")
            f.write(f"Title: {app.title}\n")
        else:
            f.write("FAILURE: not gr.Blocks\n")
        f.flush()
except Exception as e:
    import traceback
    with open("_output.txt", "a") as f:
        f.write(f"app import error: {e}\n")
        f.write(traceback.format_exc())
        f.flush()

print("DONE", flush=True)

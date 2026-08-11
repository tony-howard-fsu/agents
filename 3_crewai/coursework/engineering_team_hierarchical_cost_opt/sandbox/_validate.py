"""Validate that the Gradio Blocks UI in app.py constructs without error."""

import sys
print("Starting validation...", flush=True)

import gradio as gr
print("Imported gradio", flush=True)

# Import app from app.py — this triggers the `with gr.Blocks(...) as app:` block
# at module level, constructing the Blocks object.
from app import app
print("Imported app", flush=True)

# Verify that app is a gr.Blocks instance
if isinstance(app, gr.Blocks):
    msg = f"✅ SUCCESS: app is a gr.Blocks instance (type: {type(app).__name__})"
    print(msg, flush=True)
    print(f"   Title: {app.title}", flush=True)
    sys.exit(0)
else:
    msg = f"❌ FAILURE: app is not a gr.Blocks instance (type: {type(app).__name__})"
    print(msg, flush=True)
    sys.exit(1)

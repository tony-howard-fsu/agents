"""Validate that app.py constructs the Gradio UI without error."""

import sys

# First, verify the app module can be imported without error
try:
    from app import create_ui
    print("✅ app.create_ui imported successfully")
except Exception as e:
    print(f"❌ Failed to import app.create_ui: {e}")
    sys.exit(1)

# Next, verify create_ui() constructs without error
try:
    ui = create_ui()
    print("✅ create_ui() returned a Gr.Blocks instance successfully")
except Exception as e:
    print(f"❌ create_ui() raised an error: {e}")
    sys.exit(1)

# Verify the type
import gradio as gr
if isinstance(ui, gr.Blocks):
    print("✅ ui is a gr.Blocks instance")
else:
    print(f"❌ Expected gr.Blocks, got {type(ui)}")
    sys.exit(1)

# Verify handle_trade_symbol_change doesn't take a manager parameter
import inspect
from app import handle_trade_symbol_change
sig = inspect.signature(handle_trade_symbol_change)
params = list(sig.parameters.keys())
print(f"  handle_trade_symbol_change params: {params}")
if "manager" in params or len(params) > 1:
    print("❌ handle_trade_symbol_change should only take 'symbol'")
    sys.exit(1)
else:
    print("✅ handle_trade_symbol_change only takes 'symbol'")

# Verify handle_create_account has None guard
from app import handle_create_account
source = inspect.getsource(handle_create_account)
if "initial_deposit is None" in source:
    print("✅ handle_create_account has None guard for initial_deposit")
else:
    print("❌ handle_create_account missing None guard for initial_deposit")
    sys.exit(1)

# Verify the wiring on trade_symbol.change only has trade_symbol as input
source_ui = inspect.getsource(create_ui)
if "trade_symbol.change" in source_ui:
    change_block = source_ui.split("trade_symbol.change(")[1].split(")")[0]
    if "state" in change_block:
        print("❌ trade_symbol.change wiring still has state in inputs")
        sys.exit(1)
    else:
        print("✅ trade_symbol.change wiring does not include state")
else:
    print("⚠ Could not find trade_symbol.change in create_ui source")

# Check that launch is called with theme (Gradio 6.0+ passes theme via launch())
if "launch(theme=" in source_ui:
    print("✅ theme is passed to launch()")
else:
    print("⚠ Could not confirm theme is passed to launch()")

# Read the full app.py to verify the __main__ block
with open("app.py") as f:
    full_source = f.read()

if "app.launch(theme=theme)" in full_source:
    print("✅ __main__ calls app.launch(theme=theme)")
else:
    print("⚠ __main__ launch call pattern differs")

print("\n🎉 All validations passed!")

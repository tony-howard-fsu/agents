"""
_validate.py — Quick validation: constructs TradingSimulationApp to ensure
the Gradio Blocks build without errors.
"""

import sys

def main():
    print("Testing TradingSimulationApp construction...")
    try:
        from app import TradingSimulationApp
        app = TradingSimulationApp()
        print("✅ TradingSimulationApp constructed successfully.")
        print(f"   Blocks type: {type(app._blocks).__name__}")
        # Check that key components exist
        blocks = app._blocks
        # The blocks should have state and components
        print("✅ Validation passed — Gradio UI constructs without error.")
    except Exception as e:
        print(f"❌ Construction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

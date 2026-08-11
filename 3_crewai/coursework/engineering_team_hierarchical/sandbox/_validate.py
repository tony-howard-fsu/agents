import app

assert hasattr(app, "demo"), "app.demo is missing"
ui = app.build_ui()
assert ui is not None, "build_ui() returned None"
assert type(ui).__name__ == type(app.demo).__name__, "build_ui() did not construct a Blocks object"
print(type(app.demo).__name__)
print(type(ui).__name__)
print("validation ok")

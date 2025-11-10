"""
Functions Exercise 4 (functions4.py)
This exercise builds on the previous one by exploring default parameter values and their interaction with type hints.
"""

# TODO: Define a function that accepts an optional string `name` (default "Guest")
# It should return "Welcome, NAME!"
def welcome(name: str = "Guest") -> str:
    return f"Welcome, {name}!"

# === TESTS ===
import inspect

sig = inspect.signature(welcome)
params = sig.parameters

assert list(params.keys()) == ["name"], f"[FAIL] Function should have one parameter named 'name', got {list(params.keys())}"
assert params["name"].annotation == str, f"[FAIL] 'name' should be of type str, but got {params['name'].annotation}"
assert params["name"].default == "Guest", f"[FAIL] 'name' should default to 'Guest', got {params['name'].default}"
assert sig.return_annotation == str, f"[FAIL] Function should return a string"

assert welcome("Graham") == "Welcome, Graham!", f"[FAIL] Incorrect message when name is provided"
assert welcome() == "Welcome, Guest!", f"[FAIL] Incorrect default message"

print(welcome("Graham"))
print(welcome())
"""
Welcome to the Pylings variable exercise!
Your goal is to practice working with variables in Python.

"""

# TODO: Assign the name of your operating system to the variable 'MY_OS'
MY_OS = 

# TODO: Assign a whole NUMBER to the variable `NUMBER`.
NUMBER = 

# TODO: Assign a float value to the `FRACTIONAL` variable
FRACTIONAL =

# TODO: Create a new variable 'IS_LEARNING_PYTHON' and set it to True.
IS_LEARNING_PYTHON = 

# TODO: Finish definition of 'NUMBER_INCREMENTED' by incrementing `NUMBER` by 1.
NUMBER_INCREMENTED = 

# === TESTS ===
# DO NOT TOUCH
assert isinstance(MY_OS, str), f"Expected a string, but got {type(MY_OS).__name__}"
assert isinstance(NUMBER, int), f"Expected an integer, but got {type(NUMBER).__name__}"
assert isinstance(FRACTIONAL, float), f"Expected a float, but got {type(FRACTIONAL).__name__}"
assert isinstance(IS_LEARNING_PYTHON, bool), f"Expected a boolean, but got {type(IS_LEARNING_PYTHON).__name__}"
assert IS_LEARNING_PYTHON is True, f"Expected True, but got {IS_LEARNING_PYTHON}"
assert NUMBER_INCREMENTED == NUMBER + 1, f"Expected {NUMBER + 1}, but got {NUMBER_INCREMENTED}"

# Print the variables to see their values.
print("My Operating System is:", MY_OS)
print("This is a whole NUMBER:", NUMBER)
print("This is a FRACTIONAL NUMBER:", FRACTIONAL)
print("Am I learning Python?", IS_LEARNING_PYTHON)
print("The NUMBER has been increased:", NUMBER_INCREMENTED)
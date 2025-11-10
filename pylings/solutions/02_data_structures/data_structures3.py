"""
In this exercise, we are going to introduce the concept of dictionaries.

In Python, a dictionary is an unordered collection of key-value pairs:

- A dictionary is defined using curly braces `{}` with key-value pairs separated by colons `:`.

- Keys must be unique and immutable (e.g., strings, numbers, tuples).

- Values can be of any data type and can be duplicated.

- Dictionaries allow fast access to values when you know the key.

"""

# TODO: Initialize a dictionary with programming book titles as keys and a dictionary of details (author, year, price) as values:
books = {
    "Clean Code": {"author": "Robert C. Martin", "year": 2008, "price": 30},
    "The Pragmatic Programmer": {"author": "Andrew Hunt and David Thomas", "year": 1999, "price": 25},
    "Introduction to Algorithms": {"author": "Cormen, Leiserson, Rivest, and Stein", "year": 2009, "price": 100},
    "Python Crash Course": {"author": "Eric Matthes", "year": 2015, "price": 40}
}

# DO NOT TOUCH
assert books == {
    "Clean Code": {"author": "Robert C. Martin", "year": 2008, "price": 30},
    "The Pragmatic Programmer": {"author": "Andrew Hunt and David Thomas", "year": 1999, "price": 25},
    "Introduction to Algorithms": {"author": "Cormen, Leiserson, Rivest, and Stein", "year": 2009, "price": 100},
    "Design Patterns": {"author": "Erich Gamma et al.", "year": 1994, "price": 50}
}, f"Expected correct dictionary, but got {books}"
print(f"Books: {books}")

# TODO: Access the author of "Clean Code" from the dictionary
clean_code_author = books["Clean Code"]["author"]

# DO NOT TOUCH
assert clean_code_author == "Robert C. Martin", f"Expected 'Robert C. Martin', but got {clean_code_author}"
print(f"Author of Clean Code: {clean_code_author}")

# TODO: Add a new book "Design Patterns" with author "Erich Gamma et al.", year 1994, and price 50
books["Design Patterns"] = {"author": "Erich Gamma et al.", "year": 1994, "price": 50}

# DO NOT TOUCH
assert books["Design Patterns"] == {"author": "Erich Gamma et al.", "year": 1994, "price": 50}, f"Expected 'Erich Gamma et al.', but got {books.get('Design Patterns')}"
print(f"Updated books: {books}")

# TODO: Remove the entry for "Python Crash Course" and store it in `removed_book`
removed_book = books.pop("Python Crash Course")

# DO NOT TOUCH
assert removed_book == {"author": "Eric Matthes", "year": 2015, "price": 40}, f"Expected 'Eric Matthes', but got {removed_book}"
assert "Python Crash Course" not in books, "Python Crash Course should be removed from the dictionary"
print(f"Books after removal: {books}")

# TODO: Update the author of "Introduction to Algorithms" to 'CLRS'
books["Introduction to Algorithms"]["author"] = "CLRS"

# DO NOT TOUCH
assert books["Introduction to Algorithms"]["author"] == "CLRS", f"Expected 'CLRS', but got {books['Introduction to Algorithms']['author']})"
print(f"Books after update: {books}")
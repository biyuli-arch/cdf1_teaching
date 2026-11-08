"""Datatypes and assignment"""

# This file demonstrates the use of different data types in Python.

# Assign a value of each type.

a = "Hello"          # String
b = 42               # Integer
c = 3.14             # Float
d = True             # Boolean

# Print the values.
print(a, b, c, d)

# Print their types.
print(type(a), type(b), type(c), type(d))

# ----------------------------------------------

"""Lists and dictionaries"""

# Make a list of five numbers and one string.
my_list = [1, 2, 3, 4, 5, "Hello"]  # List

# Print the length of the list.
print(len(my_list))

# Make a dictionary with three key-value pairs.
my_dict = {"name": "Alice", "age": 20, "student": True}  # Dictionary

# Print its keys, values, and key-value pairs.
print(my_dict.keys())
print(my_dict.values())
print(my_dict.items())

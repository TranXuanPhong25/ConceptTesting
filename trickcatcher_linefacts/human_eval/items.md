# 30 mục đánh giá fact v3 (DEV)

## H01 — task 110

### Đặc tả (docstring)

```text
In this problem, you will implement a function that takes two lists of numbers,
and determines whether it is possible to perform an exchange of elements
between them to make lst1 a list of only even numbers.
There is no limit on the number of exchanged elements between lst1 and lst2.
If it is possible to exchange elements between the lst1 and lst2 to make
all the elements of lst1 to be even, return "YES".
Otherwise, return "NO".
For example:
exchange([1, 2, 3, 4], [1, 2, 3, 4]) => "YES"
exchange([1, 2, 3, 4], [1, 5, 3, 4]) => "NO"
It is assumed that the input lists will be non-empty.
```

### PUT

```python

def exchange(lst1, lst2):
    """In this problem, you will implement a function that takes two lists of numbers,
    and determines whether it is possible to perform an exchange of elements
    between them to make lst1 a list of only even numbers.
    There is no limit on the number of exchanged elements between lst1 and lst2.
    If it is possible to exchange elements between the lst1 and lst2 to make
    all the elements of lst1 to be even, return "YES".
    Otherwise, return "NO".
    For example:
    exchange([1, 2, 3, 4], [1, 2, 3, 4]) => "YES"
    exchange([1, 2, 3, 4], [1, 5, 3, 4]) => "NO"
    It is assumed that the input lists will be non-empty.
    """
    # Write your code here
    if len(lst1) != len(lst2):
        return "NO"
    for i in range(len(lst1)):
        if lst1[i] % 2 != 0:
            for j in range(len(lst2)):
                if lst2[j] % 2 == 0:
                    lst1[i], lst2[j] = lst2[j], lst1[i]
                    break
            else:
                return "NO"
    return "YES"
```

### Fact

Branch coverage (C2): the True branch of `len(lst1) != len(lst2)` (line 16) is never taken by the existing tests.

## H02 — task 59

### Đặc tả (docstring)

```text
Return the largest prime factor of n. Assume n > 1 and is not a prime.
>>> largest_prime_factor(13195)
29
>>> largest_prime_factor(2048)
2
```

### PUT

```python


def largest_prime_factor(n: int):
    """Return the largest prime factor of n. Assume n > 1 and is not a prime.
    >>> largest_prime_factor(13195)
    29
    >>> largest_prime_factor(2048)
    2
    """
    largest = 1
    while n % 2 == 0:
        largest = 2
        n = n // 2
    # n is odd at this point.
    while n % 3 == 0:
        largest = 3
        n = n // 3
    while n % 5 == 0:
        largest = 5
        n = n // 5
    # n is not a multiple of 2, 3, or 5 at this point.
    while n % 6 == 0:
        largest = 6
        n = n // 6
    while n % 7 == 0:
        largest = 7
        n = n // 7
    while n % 9 == 0:
        largest = 9
        n = n // 9
    # n is not a multiple of 2, 3, 5, 6, 7, or 9 at this point.
    while n % 11 == 0:
        largest = 11
        n = n // 11
    while n % 13 == 0:
        largest = 13
        n = n // 13
    while n % 17 == 0:
        largest = 17
        n = n // 17
    while n % 19 == 0:
        largest = 19
        n = n // 19
    # n is not a multiple of 2, 3, 5, 6, 7, 9, 11, 13, 17, or 19 at this point.
    # If n is greater than 1, it is a prime greater than largest.
    if n > 1:
        return n
    return largest
```

### Fact

Statement coverage (C1): lines 42-43 (starting with `largest = 19`) are never executed by the existing tests.

## H03 — task 59

### Đặc tả (docstring)

```text
Return the largest prime factor of n. Assume n > 1 and is not a prime.
>>> largest_prime_factor(13195)
29
>>> largest_prime_factor(2048)
2
```

### PUT

```python


def largest_prime_factor(n: int):
    """Return the largest prime factor of n. Assume n > 1 and is not a prime.
    >>> largest_prime_factor(13195)
    29
    >>> largest_prime_factor(2048)
    2
    """
    largest = 1
    while n % 2 == 0:
        largest = 2
        n = n // 2
    # n is odd at this point.
    while n % 3 == 0:
        largest = 3
        n = n // 3
    while n % 5 == 0:
        largest = 5
        n = n // 5
    # n is not a multiple of 2, 3, or 5 at this point.
    while n % 6 == 0:
        largest = 6
        n = n // 6
    while n % 7 == 0:
        largest = 7
        n = n // 7
    while n % 9 == 0:
        largest = 9
        n = n // 9
    # n is not a multiple of 2, 3, 5, 6, 7, or 9 at this point.
    while n % 11 == 0:
        largest = 11
        n = n // 11
    while n % 13 == 0:
        largest = 13
        n = n // 13
    while n % 17 == 0:
        largest = 17
        n = n // 17
    while n % 19 == 0:
        largest = 19
        n = n // 19
    # n is not a multiple of 2, 3, 5, 6, 7, 9, 11, 13, 17, or 19 at this point.
    # If n is greater than 1, it is a prime greater than largest.
    if n > 1:
        return n
    return largest
```

### Fact

Mutation (CRP constant): the mutant `n // 17` -> `n // 18` at line 40 survives: no existing test distinguishes them.

## H04 — task 12

### Đặc tả (docstring)

```text
Out of list of strings, return the longest one. Return the first one in case of multiple
strings of the same length. Return None in case the input list is empty.
>>> longest([])

>>> longest(['a', 'b', 'c'])
'a'
>>> longest(['a', 'bb', 'ccc'])
'ccc'
```

### PUT

```python
from typing import List, Optional


def longest(strings: List[str]) -> Optional[str]:
    """ Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    >>> longest([])

    >>> longest(['a', 'b', 'c'])
    'a'
    >>> longest(['a', 'bb', 'ccc'])
    'ccc'
    """
    if len(strings) == 0:
        return None
    strings = [s.lower() for s in strings]
    strings = [s for s in strings if len(s) > 0]
    strings = [s for s in strings if s]
    return max(strings, key=len)
```

### Fact

Boundary value: at line 14, `len(strings)` was never equal to 1 (next to the constant 0 in `len(strings) == 0`).

## H05 — task 5

### Đặc tả (docstring)

```text
Insert a number 'delimeter' between every two consecutive elements of input list `numbers'
>>> intersperse([], 4)
[]
>>> intersperse([1, 2, 3], 4)
[1, 4, 2, 4, 3]
```

### PUT

```python
from typing import List


def intersperse(numbers: List[int], delimeter: int) -> List[int]:
    """ Insert a number 'delimeter' between every two consecutive elements of input list `numbers'
    >>> intersperse([], 4)
    []
    >>> intersperse([1, 2, 3], 4)
    [1, 4, 2, 4, 3]
    """

    numbers.insert(0, 0)
    numbers.append(0)
    result = []

    for i in range(len(numbers) - 1):
        if numbers[i] != 0:
            result.append(numbers[i])
        if numbers[i] != 0 and numbers[i + 1] != 0:
            result.append(delimeter)

    return result
```

### Fact

Equivalence class: in the existing tests, parameter `delimeter` of `intersperse` was never zero.

## H06 — task 162

### Đặc tả (docstring)

```text
Given a string 'text', return its md5 hash equivalent string.
If 'text' is an empty string, return None.

>>> string_to_md5('Hello world') == '3e25960a79dbc69b674cd4ec67a72c62'
```

### PUT

```python

def string_to_md5(text):
    """
    Given a string 'text', return its md5 hash equivalent string.
    If 'text' is an empty string, return None.

    >>> string_to_md5('Hello world') == '3e25960a79dbc69b674cd4ec67a72c62'
    """
    import hashlib
    text = text.strip()
    if len(text) == 0:
        return None
    h = hashlib.md5()
    h.update(text.encode('utf-8'))
    return h.hexdigest()
```

### Fact

Mutation (call-result removal): the mutant `text.strip()` -> `text` at line 10 survives: no existing test distinguishes them.

## H07 — task 73

### Đặc tả (docstring)

```text
Given an array arr of integers, find the minimum number of elements that
need to be changed to make the array palindromic. A palindromic array is an array that
is read the same backwards and forwards. In one change, you can change one element to any other element.

For example:
smallest_change([1,2,3,5,4,7,9,6]) == 4
smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1
smallest_change([1, 2, 3, 2, 1]) == 0
```

### PUT

```python

def smallest_change(arr):
    """
    Given an array arr of integers, find the minimum number of elements that
    need to be changed to make the array palindromic. A palindromic array is an array that
    is read the same backwards and forwards. In one change, you can change one element to any other element.

    For example:
    smallest_change([1,2,3,5,4,7,9,6]) == 4
    smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1
    smallest_change([1, 2, 3, 2, 1]) == 0
    """
    if not arr:
        return 0

    # Find the first occurrence of each element in the array
    first_occurrence = {}
    for i in range(len(arr)):
        if arr[i] not in first_occurrence:
            first_occurrence[arr[i]] = i

    # Find the number of elements that need to be changed
    num_changes = 0
    for i in range(len(arr) // 2):
        if arr[i] != arr[len(arr) - 1 - i]:
            if arr[i] in first_occurrence and first_occurrence[arr[i]] == len(arr) - 1 - i:
                # The element is already at the correct position
                num_changes += 1
                del first_occurrence[arr[i]]
            else:
                # The element is not at the correct position
                if arr[i] in first_occurrence:
                    num_changes += 1
                    del first_occurrence[arr[i]]
                else:
                    num_changes += 2

    return num_changes
```

### Fact

Def-use pair (all-uses, c-use): the value assigned to `num_changes` at line 36 never reaches its use at line 38 in the existing tests.

## H08 — task 29

### Đặc tả (docstring)

```text
Filter an input list of strings only for ones that start with a given prefix.
>>> filter_by_prefix([], 'a')
[]
>>> filter_by_prefix(['abc', 'bcd', 'cde', 'array'], 'a')
['abc', 'array']
```

### PUT

```python
from typing import List


def filter_by_prefix(strings: List[str], prefix: str) -> List[str]:
    """ Filter an input list of strings only for ones that start with a given prefix.
    >>> filter_by_prefix([], 'a')
    []
    >>> filter_by_prefix(['abc', 'bcd', 'cde', 'array'], 'a')
    ['abc', 'array']
    """
    if not prefix:
        return strings

    return [s for s in strings if s.startswith(prefix)]
```

### Fact

Branch coverage (C2): the True branch of `not prefix` (line 11) is never taken by the existing tests.

## H09 — task 79

### Đặc tả (docstring)

```text
You will be given a number in decimal form and your task is to convert it to
binary format. The function should return a string, with each character representing a binary
number. Each character in the string will be '0' or '1'.

There will be an extra couple of characters 'db' at the beginning and at the end of the string.
The extra characters are there to help with the format.

Examples:
decimal_to_binary(15)   # returns "db1111db"
decimal_to_binary(32)   # returns "db100000db"
```

### PUT

```python

def decimal_to_binary(decimal):
    """You will be given a number in decimal form and your task is to convert it to
    binary format. The function should return a string, with each character representing a binary
    number. Each character in the string will be '0' or '1'.

    There will be an extra couple of characters 'db' at the beginning and at the end of the string.
    The extra characters are there to help with the format.

    Examples:
    decimal_to_binary(15)   # returns "db1111db"
    decimal_to_binary(32)   # returns "db100000db"
    """
    if decimal >= 0 and decimal <= 255:
        binary = bin(decimal)[2:]
        return "db"+binary+"db"

    raise ValueError("The number must be in the range [0, 255]")
```

### Fact

Statement coverage (C1): line 18 (starting with `raise ValueError("The number must be in the range [0, 255]")`) is never executed by the existing tests.

## H10 — task 110

### Đặc tả (docstring)

```text
In this problem, you will implement a function that takes two lists of numbers,
and determines whether it is possible to perform an exchange of elements
between them to make lst1 a list of only even numbers.
There is no limit on the number of exchanged elements between lst1 and lst2.
If it is possible to exchange elements between the lst1 and lst2 to make
all the elements of lst1 to be even, return "YES".
Otherwise, return "NO".
For example:
exchange([1, 2, 3, 4], [1, 2, 3, 4]) => "YES"
exchange([1, 2, 3, 4], [1, 5, 3, 4]) => "NO"
It is assumed that the input lists will be non-empty.
```

### PUT

```python

def exchange(lst1, lst2):
    """In this problem, you will implement a function that takes two lists of numbers,
    and determines whether it is possible to perform an exchange of elements
    between them to make lst1 a list of only even numbers.
    There is no limit on the number of exchanged elements between lst1 and lst2.
    If it is possible to exchange elements between the lst1 and lst2 to make
    all the elements of lst1 to be even, return "YES".
    Otherwise, return "NO".
    For example:
    exchange([1, 2, 3, 4], [1, 2, 3, 4]) => "YES"
    exchange([1, 2, 3, 4], [1, 5, 3, 4]) => "NO"
    It is assumed that the input lists will be non-empty.
    """
    # Write your code here
    if len(lst1) != len(lst2):
        return "NO"
    for i in range(len(lst1)):
        if lst1[i] % 2 != 0:
            for j in range(len(lst2)):
                if lst2[j] % 2 == 0:
                    lst1[i], lst2[j] = lst2[j], lst1[i]
                    break
            else:
                return "NO"
    return "YES"
```

### Fact

Mutation (AOR): the mutant `lst1[i] % 2` -> `lst1[i] // 2` at line 19 survives: no existing test distinguishes them.

## H11 — task 72

### Đặc tả (docstring)

```text
Write a function that returns True if the object q will fly, and False otherwise.
The object q will fly if it's balanced (it is a palindromic list) and the sum of its elements is less than or equal the maximum possible weight w.

Example:
will_it_fly([1, 2], 5) ➞ False 
# 1+2 is less than the maximum possible weight, but it's unbalanced.

will_it_fly([3, 2, 3], 1) ➞ False
# it's balanced, but 3+2+3 is more than the maximum possible weight.

will_it_fly([3, 2, 3], 9) ➞ True
# 3+2+3 is less than the maximum possible weight, and it's balanced.

will_it_fly([3], 5) ➞ True
# 3 is less than the maximum possible weight, and it's balanced.
```

### PUT

```python

def will_it_fly(q,w):
    '''
    Write a function that returns True if the object q will fly, and False otherwise.
    The object q will fly if it's balanced (it is a palindromic list) and the sum of its elements is less than or equal the maximum possible weight w.

    Example:
    will_it_fly([1, 2], 5) ➞ False 
    # 1+2 is less than the maximum possible weight, but it's unbalanced.

    will_it_fly([3, 2, 3], 1) ➞ False
    # it's balanced, but 3+2+3 is more than the maximum possible weight.

    will_it_fly([3, 2, 3], 9) ➞ True
    # 3+2+3 is less than the maximum possible weight, and it's balanced.

    will_it_fly([3], 5) ➞ True
    # 3 is less than the maximum possible weight, and it's balanced.
    '''
    if len(q) == 1:
        return True
    if q[0] == q[-1] and sum(q) <= w:
        return True
    return False
```

### Fact

Boundary value: at line 20, `len(q)` was never equal to 0 (next to the constant 1 in `len(q) == 1`).

## H12 — task 76

### Đặc tả (docstring)

```text
Your task is to write a function that returns true if a number x is a simple
power of n and false in other cases.
x is a simple power of n if n**int=x
For example:
is_simple_power(1, 4) => true
is_simple_power(2, 2) => true
is_simple_power(8, 2) => true
is_simple_power(3, 2) => false
is_simple_power(3, 1) => false
is_simple_power(5, 3) => false
```

### PUT

```python

def is_simple_power(x, n):
    """Your task is to write a function that returns true if a number x is a simple
    power of n and false in other cases.
    x is a simple power of n if n**int=x
    For example:
    is_simple_power(1, 4) => true
    is_simple_power(2, 2) => true
    is_simple_power(8, 2) => true
    is_simple_power(3, 2) => false
    is_simple_power(3, 1) => false
    is_simple_power(5, 3) => false
    """
    if x == 1:
        return True
    if n == 1:
        return False
    if x % n == 0:
        return is_simple_power(x / n, n)
    else:
        return False
```

### Fact

Equivalence class: in the existing tests, parameter `x` of `is_simple_power` was never negative.

## H13 — task 99

### Đặc tả (docstring)

```text
Create a function that takes a value (string) representing a number
and returns the closest integer to it. If the number is equidistant
from two integers, round it away from zero.

Examples
>>> closest_integer("10")
10
>>> closest_integer("15.3")
15

Note:
Rounding away from zero means that if the given number is equidistant
from two integers, the one you should return is the one that is the
farthest from zero. For example closest_integer("14.5") should
return 15 and closest_integer("-14.5") should return -15.
```

### PUT

```python

def closest_integer(value):
    '''
    Create a function that takes a value (string) representing a number
    and returns the closest integer to it. If the number is equidistant
    from two integers, round it away from zero.

    Examples
    >>> closest_integer("10")
    10
    >>> closest_integer("15.3")
    15

    Note:
    Rounding away from zero means that if the given number is equidistant
    from two integers, the one you should return is the one that is the
    farthest from zero. For example closest_integer("14.5") should
    return 15 and closest_integer("-14.5") should return -15.
    '''
    if '.' in value:
        value = float(value)
        if value % 1 == 0.5:
            if value > 0:
                return int(value + 1)
            else:
                return int(value - 1)
        else:
            return int(round(value))
    else:
        return int(value)
```

### Fact

Mutation (call-result removal): the mutant `round(value)` -> `value` at line 28 survives: no existing test distinguishes them.

## H14 — task 89

### Đặc tả (docstring)

```text
Create a function encrypt that takes a string as an argument and
returns a string encrypted with the alphabet being rotated. 
The alphabet should be rotated in a manner such that the letters 
shift down by two multiplied to two places.
For example:
encrypt('hi') returns 'lm'
encrypt('asdfghjkl') returns 'ewhjklnop'
encrypt('gf') returns 'kj'
encrypt('et') returns 'ix'
```

### PUT

```python

def encrypt(s):
    """Create a function encrypt that takes a string as an argument and
    returns a string encrypted with the alphabet being rotated. 
    The alphabet should be rotated in a manner such that the letters 
    shift down by two multiplied to two places.
    For example:
    encrypt('hi') returns 'lm'
    encrypt('asdfghjkl') returns 'ewhjklnop'
    encrypt('gf') returns 'kj'
    encrypt('et') returns 'ix'
    """
    result = ""
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for char in s:
        result += alphabet[(alphabet.index(char.lower()) + 2*2) % 26]
    return result
```

### Fact

Def-use pair (all-uses, c-use): the value assigned to `result` at line 13 never reaches its use at line 17 in the existing tests.

## H15 — task 109

### Đặc tả (docstring)

```text
We have an array 'arr' of N integers arr[1], arr[2], ..., arr[N].The
numbers in the array will be randomly ordered. Your task is to determine if
it is possible to get an array sorted in non-decreasing order by performing 
the following operation on the given array:
    You are allowed to perform right shift operation any number of times.

One right shift operation means shifting all elements of the array by one
position in the right direction. The last element of the array will be moved to
the starting position in the array i.e. 0th index. 

If it is possible to obtain the sorted array by performing the above operation
then return True else return False.
If the given array is empty then return True.

Note: The given list is guaranteed to have unique elements.

For Example:

move_one_ball([3, 4, 5, 1, 2])==>True
Explanation: By performin 2 right shift operations, non-decreasing order can
             be achieved for the given array.
move_one_ball([3, 5, 4, 1, 2])==>False
Explanation:It is not possible to get non-decreasing order for the given
            array by performing any number of right shift operations.
            
```

### PUT

```python

def move_one_ball(arr):
    """We have an array 'arr' of N integers arr[1], arr[2], ..., arr[N].The
    numbers in the array will be randomly ordered. Your task is to determine if
    it is possible to get an array sorted in non-decreasing order by performing 
    the following operation on the given array:
        You are allowed to perform right shift operation any number of times.
    
    One right shift operation means shifting all elements of the array by one
    position in the right direction. The last element of the array will be moved to
    the starting position in the array i.e. 0th index. 

    If it is possible to obtain the sorted array by performing the above operation
    then return True else return False.
    If the given array is empty then return True.

    Note: The given list is guaranteed to have unique elements.

    For Example:
    
    move_one_ball([3, 4, 5, 1, 2])==>True
    Explanation: By performin 2 right shift operations, non-decreasing order can
                 be achieved for the given array.
    move_one_ball([3, 5, 4, 1, 2])==>False
    Explanation:It is not possible to get non-decreasing order for the given
                array by performing any number of right shift operations.
                
    """
    if len(arr) == 0:
        return True
    if len(arr) == 1:
        return True
    if arr[0] > arr[1]:
        return False
    if arr[0] == arr[1]:
        return move_one_ball(arr[1:])
    else:
        return move_one_ball(arr[1:]) or move_one_ball(arr[2:])
```

### Fact

Branch coverage (C2): the True branch of `arr[0] == arr[1]` (line 35) is never taken by the existing tests.

## H16 — task 67

### Đặc tả (docstring)

```text
In this task, you will be given a string that represents a number of apples and oranges 
that are distributed in a basket of fruit this basket contains 
apples, oranges, and mango fruits. Given the string that represents the total number of 
the oranges and apples and an integer that represent the total number of the fruits 
in the basket return the number of the mango fruits in the basket.
for examble:
fruit_distribution("5 apples and 6 oranges", 19) ->19 - 5 - 6 = 8
fruit_distribution("0 apples and 1 oranges",3) -> 3 - 0 - 1 = 2
fruit_distribution("2 apples and 3 oranges", 100) -> 100 - 2 - 3 = 95
fruit_distribution("100 apples and 1 oranges",120) -> 120 - 100 - 1 = 19
```

### PUT

```python

def fruit_distribution(s,n):
    """
    In this task, you will be given a string that represents a number of apples and oranges 
    that are distributed in a basket of fruit this basket contains 
    apples, oranges, and mango fruits. Given the string that represents the total number of 
    the oranges and apples and an integer that represent the total number of the fruits 
    in the basket return the number of the mango fruits in the basket.
    for examble:
    fruit_distribution("5 apples and 6 oranges", 19) ->19 - 5 - 6 = 8
    fruit_distribution("0 apples and 1 oranges",3) -> 3 - 0 - 1 = 2
    fruit_distribution("2 apples and 3 oranges", 100) -> 100 - 2 - 3 = 95
    fruit_distribution("100 apples and 1 oranges",120) -> 120 - 100 - 1 = 19
    """
    try:
        if not s or len(s) < 1:
            return "invalid input"
        if n < 1:
            return "invalid input"
        number = int(s.split("and")[0].strip().split()[0]) + int(s.split("and")[1].strip().split()[0])
        return n - number
    except:
        return "invalid input"
```

### Fact

Statement coverage (C1): line 23 (starting with `return "invalid input"`) is never executed by the existing tests.

## H17 — task 142

### Đặc tả (docstring)

```text
"
This function will take a list of integers. For all entries in the list, the function shall square the integer entry if its index is a 
multiple of 3 and will cube the integer entry if its index is a multiple of 4 and not a multiple of 3. The function will not 
change the entries in the list whose indexes are not a multiple of 3 or 4. The function shall then return the sum of all entries. 

Examples:
For lst = [1,2,3] the output should be 6
For lst = []  the output should be 0
For lst = [-1,-5,2,-1,-5]  the output should be -126
```

### PUT

```python



def sum_squares(lst):
    """"
    This function will take a list of integers. For all entries in the list, the function shall square the integer entry if its index is a 
    multiple of 3 and will cube the integer entry if its index is a multiple of 4 and not a multiple of 3. The function will not 
    change the entries in the list whose indexes are not a multiple of 3 or 4. The function shall then return the sum of all entries. 
    
    Examples:
    For lst = [1,2,3] the output should be 6
    For lst = []  the output should be 0
    For lst = [-1,-5,2,-1,-5]  the output should be -126
    """
    # empty list
    if len(lst) == 0:
        return 0
    # list with one element
    if len(lst) == 1:
        return lst[0]
    # list with two elements
    if len(lst) == 2:
        return lst[0] + lst[1]
    # list with more than two elements
    else:
        lst_len = len(lst)
        sum_squares = 0
        for i in range(lst_len):
            if (i % 3 == 0):
                sum_squares += lst[i]**2
            elif (i % 4 == 0) and (i % 3 != 0):
                sum_squares += lst[i]**3
            else:
                sum_squares += lst[i]
        return sum_squares
```

### Fact

Mutation (CRP constant): the mutant `len(lst) == 0` -> `len(lst) == 1` at line 16 survives: no existing test distinguishes them.

## H18 — task 25

### Đặc tả (docstring)

```text
Return list of prime factors of given integer in the order from smallest to largest.
Each of the factors should be listed number of times corresponding to how many times it appeares in factorization.
Input number should be equal to the product of all factors
>>> factorize(8)
[2, 2, 2]
>>> factorize(25)
[5, 5]
>>> factorize(70)
[2, 5, 7]
```

### PUT

```python
from typing import List


def factorize(n: int) -> List[int]:
    """ Return list of prime factors of given integer in the order from smallest to largest.
    Each of the factors should be listed number of times corresponding to how many times it appeares in factorization.
    Input number should be equal to the product of all factors
    >>> factorize(8)
    [2, 2, 2]
    >>> factorize(25)
    [5, 5]
    >>> factorize(70)
    [2, 5, 7]
    """

    result = []
    i = 2
    while n > 1:
        if n % i == 0:
            result.append(i)
            n //= i
        else:
            i += 1
    return result
```

### Fact

Boundary value: at line 18, `n` was never equal to 0 (next to the constant 1 in `n > 1`).

## H19 — task 83

### Đặc tả (docstring)

```text
Given a positive integer n, return the count of the numbers of n-digit
positive integers that start or end with 1.
```

### PUT

```python

def starts_one_ends(n):
    """
    Given a positive integer n, return the count of the numbers of n-digit
    positive integers that start or end with 1.
    """
    count = 0
    for i in range(10**(n-1), 10**n):
        if str(i)[0] == '1' or str(i)[-1] == '1':
            count += 1
    return count
```

### Fact

Equivalence class: in the existing tests, parameter `n` of `starts_one_ends` was never negative.

## H20 — task 12

### Đặc tả (docstring)

```text
Out of list of strings, return the longest one. Return the first one in case of multiple
strings of the same length. Return None in case the input list is empty.
>>> longest([])

>>> longest(['a', 'b', 'c'])
'a'
>>> longest(['a', 'bb', 'ccc'])
'ccc'
```

### PUT

```python
from typing import List, Optional


def longest(strings: List[str]) -> Optional[str]:
    """ Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    >>> longest([])

    >>> longest(['a', 'b', 'c'])
    'a'
    >>> longest(['a', 'bb', 'ccc'])
    'ccc'
    """
    if len(strings) == 0:
        return None
    strings = [s.lower() for s in strings]
    strings = [s for s in strings if len(s) > 0]
    strings = [s for s in strings if s]
    return max(strings, key=len)
```

### Fact

Mutation (call-result removal): the mutant `s.lower()` -> `s` at line 16 survives: no existing test distinguishes them.

## H21 — task 20

### Đặc tả (docstring)

```text
From a supplied list of numbers (of length at least two) select and return two that are the closest to each
other and return them in order (smaller number, larger number).
>>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])
(2.0, 2.2)
>>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0])
(2.0, 2.0)
```

### PUT

```python
from typing import List, Tuple


def find_closest_elements(numbers: List[float]) -> Tuple[float, float]:
    """ From a supplied list of numbers (of length at least two) select and return two that are the closest to each
    other and return them in order (smaller number, larger number).
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])
    (2.0, 2.2)
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0])
    (2.0, 2.0)
    """
    if len(numbers) < 2:
        raise ValueError("List must contain at least two numbers")

    closest_numbers = sorted(numbers)
    closest_numbers_difference = abs(closest_numbers[0] - closest_numbers[1])
    closest_numbers_index = 0

    for i in range(1, len(closest_numbers)):
        if abs(closest_numbers[i] - closest_numbers[i - 1]) < closest_numbers_difference:
            closest_numbers_difference = abs(closest_numbers[i] - closest_numbers[i - 1])
            closest_numbers_index = i

    return closest_numbers[closest_numbers_index - 1], closest_numbers[closest_numbers_index]
```

### Fact

Def-use pair (all-uses, c-use): the value assigned to `closest_numbers_index` at line 17 never reaches its use at line 24 in the existing tests.

## H22 — task 127

### Đặc tả (docstring)

```text
You are given two intervals,
where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).
The given intervals are closed which means that the interval (start, end)
includes both start and end.
For each given interval, it is assumed that its start is less or equal its end.
Your task is to determine whether the length of intersection of these two 
intervals is a prime number.
Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)
which its length is 1, which not a prime number.
If the length of the intersection is a prime number, return "YES",
otherwise, return "NO".
If the two intervals don't intersect, return "NO".


[input/output] samples:
intersection((1, 2), (2, 3)) ==> "NO"
intersection((-1, 1), (0, 4)) ==> "NO"
intersection((-3, -1), (-5, 5)) ==> "YES"
```

### PUT

```python

def intersection(interval1, interval2):
    """You are given two intervals,
    where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).
    The given intervals are closed which means that the interval (start, end)
    includes both start and end.
    For each given interval, it is assumed that its start is less or equal its end.
    Your task is to determine whether the length of intersection of these two 
    intervals is a prime number.
    Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)
    which its length is 1, which not a prime number.
    If the length of the intersection is a prime number, return "YES",
    otherwise, return "NO".
    If the two intervals don't intersect, return "NO".


    [input/output] samples:
    intersection((1, 2), (2, 3)) ==> "NO"
    intersection((-1, 1), (0, 4)) ==> "NO"
    intersection((-3, -1), (-5, 5)) ==> "YES"
    """
    # your code here
    # print(interval1, interval2)
    if interval1[0] > interval1[1] or interval2[0] > interval2[1]:
        return "NO"
    elif interval1[0] > interval2[1] or interval2[0] > interval1[1]:
        return "NO"
    else:
        start = max(interval1[0], interval2[0])
        end = min(interval1[1], interval2[1])
        # print(start, end)
        if (end - start) == 0:
            return "NO"
        elif (end - start) == 1:
            return "NO"
        else:
            for i in range(start, end):
                if i > 1:
                    for j in range(2, i):
                        if i % j == 0:
                            return "NO"
            return "YES"
```

### Fact

Condition coverage (C3): the sub-condition `interval1[0] > interval2[1]` of the decision at line 26 is never True in the existing tests.

## H23 — task 73

### Đặc tả (docstring)

```text
Given an array arr of integers, find the minimum number of elements that
need to be changed to make the array palindromic. A palindromic array is an array that
is read the same backwards and forwards. In one change, you can change one element to any other element.

For example:
smallest_change([1,2,3,5,4,7,9,6]) == 4
smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1
smallest_change([1, 2, 3, 2, 1]) == 0
```

### PUT

```python

def smallest_change(arr):
    """
    Given an array arr of integers, find the minimum number of elements that
    need to be changed to make the array palindromic. A palindromic array is an array that
    is read the same backwards and forwards. In one change, you can change one element to any other element.

    For example:
    smallest_change([1,2,3,5,4,7,9,6]) == 4
    smallest_change([1, 2, 3, 4, 3, 2, 2]) == 1
    smallest_change([1, 2, 3, 2, 1]) == 0
    """
    if not arr:
        return 0

    # Find the first occurrence of each element in the array
    first_occurrence = {}
    for i in range(len(arr)):
        if arr[i] not in first_occurrence:
            first_occurrence[arr[i]] = i

    # Find the number of elements that need to be changed
    num_changes = 0
    for i in range(len(arr) // 2):
        if arr[i] != arr[len(arr) - 1 - i]:
            if arr[i] in first_occurrence and first_occurrence[arr[i]] == len(arr) - 1 - i:
                # The element is already at the correct position
                num_changes += 1
                del first_occurrence[arr[i]]
            else:
                # The element is not at the correct position
                if arr[i] in first_occurrence:
                    num_changes += 1
                    del first_occurrence[arr[i]]
                else:
                    num_changes += 2

    return num_changes
```

### Fact

Statement coverage (C1): line 36 (starting with `num_changes += 2`) is never executed by the existing tests.

## H24 — task 135

### Đặc tả (docstring)

```text
Create a function which returns the largest index of an element which
is not greater than or equal to the element immediately preceding it. If
no such element exists then return -1. The given array will not contain
duplicate values.

Examples:
can_arrange([1,2,4,3,5]) = 3
can_arrange([1,2,3]) = -1
```

### PUT

```python

def can_arrange(arr):
    """Create a function which returns the largest index of an element which
    is not greater than or equal to the element immediately preceding it. If
    no such element exists then return -1. The given array will not contain
    duplicate values.

    Examples:
    can_arrange([1,2,4,3,5]) = 3
    can_arrange([1,2,3]) = -1
    """
    if not arr:
        return -1

    if len(arr) == 1:
        return 0

    max_index = -1
    for i in range(1, len(arr)):
        if arr[i] < arr[i - 1]:
            max_index = i

    return max_index
```

### Fact

Mutation (ROR): the mutant `arr[i] < arr[i - 1]` -> `arr[i] <= arr[i - 1]` at line 20 survives: no existing test distinguishes them.

## H25 — task 104

### Đặc tả (docstring)

```text
Given a list of positive integers x. return a sorted list of all 
elements that hasn't any even digit.

Note: Returned list should be sorted in increasing order.

For example:
>>> unique_digits([15, 33, 1422, 1])
[1, 15, 33]
>>> unique_digits([152, 323, 1422, 10])
[]
```

### PUT

```python

def unique_digits(x):
    """Given a list of positive integers x. return a sorted list of all 
    elements that hasn't any even digit.

    Note: Returned list should be sorted in increasing order.
    
    For example:
    >>> unique_digits([15, 33, 1422, 1])
    [1, 15, 33]
    >>> unique_digits([152, 323, 1422, 10])
    []
    """
    # your code here
    result = []
    for i in x:
        if i < 10:
            result.append(i)
        else:
            num = str(i)
            for j in num:
                if int(j) % 2 == 0:
                    break
            else:
                result.append(i)
    result.sort()
    return result
```

### Fact

Boundary value: at line 17, `i` was never equal to 11 (next to the constant 10 in `i < 10`).

## H26 — task 137

### Đặc tả (docstring)

```text
Create a function that takes integers, floats, or strings representing
real numbers, and returns the larger variable in its given variable type.
Return None if the values are equal.
Note: If a real number is represented as a string, the floating point might be . or ,

compare_one(1, 2.5) ➞ 2.5
compare_one(1, "2,3") ➞ "2,3"
compare_one("5,1", "6") ➞ "6"
compare_one("1", 1) ➞ None
```

### PUT

```python

def compare_one(a, b):
    """
    Create a function that takes integers, floats, or strings representing
    real numbers, and returns the larger variable in its given variable type.
    Return None if the values are equal.
    Note: If a real number is represented as a string, the floating point might be . or ,

    compare_one(1, 2.5) ➞ 2.5
    compare_one(1, "2,3") ➞ "2,3"
    compare_one("5,1", "6") ➞ "6"
    compare_one("1", 1) ➞ None
    """
    if str(a).replace(".",",") < str(b).replace(".",","):
        return b
    elif str(a).replace(".",",") == str(b).replace(".",","):
        return None
    else:
        return a
```

### Fact

Equivalence class: in the existing tests, parameter `a` of `compare_one` was never negative.

## H27 — task 158

### Đặc tả (docstring)

```text
Write a function that accepts a list of strings.
The list contains different words. Return the word with maximum number
of unique characters. If multiple strings have maximum number of unique
characters, return the one which comes first in lexicographical order.

find_max(["name", "of", "string"]) == "string"
find_max(["name", "enam", "game"]) == "enam"
find_max(["aaaaaaa", "bb" ,"cc"]) == ""aaaaaaa"
```

### PUT

```python

def find_max(words):
    """Write a function that accepts a list of strings.
    The list contains different words. Return the word with maximum number
    of unique characters. If multiple strings have maximum number of unique
    characters, return the one which comes first in lexicographical order.

    find_max(["name", "of", "string"]) == "string"
    find_max(["name", "enam", "game"]) == "enam"
    find_max(["aaaaaaa", "bb" ,"cc"]) == ""aaaaaaa"
    """
    max_word = None
    max_unique = 0
    for word in words:
        unique = len(set(word))
        if unique > max_unique:
            max_unique = unique
            max_word = word
        elif unique == max_unique:
            if word < max_word:
                max_word = word
    return max_word
```

### Fact

Mutation (RIL): the mutant `for word in words` -> `iterate in reverse order` at line 14 survives: no existing test distinguishes them.

## H28 — task 56

### Đặc tả (docstring)

```text
brackets is a string of "<" and ">".
return True if every opening bracket has a corresponding closing bracket.

>>> correct_bracketing("<")
False
>>> correct_bracketing("<>")
True
>>> correct_bracketing("<<><>>")
True
>>> correct_bracketing("><<>")
False
```

### PUT

```python


def correct_bracketing(brackets: str):
    """ brackets is a string of "<" and ">".
    return True if every opening bracket has a corresponding closing bracket.

    >>> correct_bracketing("<")
    False
    >>> correct_bracketing("<>")
    True
    >>> correct_bracketing("<<><>>")
    True
    >>> correct_bracketing("><<>")
    False
    """
    if not brackets:
        return False
    stack = []
    for bracket in brackets:
        if bracket == '<':
            stack.append('<')
        elif bracket == '>':
            if len(stack) == 0 or stack.pop()!= '<':
                return False
        elif bracket == '>>':
            stack.append('>')
        else:
            return False
    return len(stack) == 0
```

### Fact

Def-use pair (all-uses, p-use): the value assigned to `bracket` at line 19 never reaches its use at line 25 in the existing tests.

## H29 — task 3

### Đặc tả (docstring)

```text
You're given a list of deposit and withdrawal operations on a bank account that starts with
zero balance. Your task is to detect if at any point the balance of account fallls below zero, and
at that point function should return True. Otherwise it should return False.
>>> below_zero([1, 2, 3])
False
>>> below_zero([1, 2, -4, 5])
True
```

### PUT

```python
from typing import List


def below_zero(operations: List[int]) -> bool:
    """ You're given a list of deposit and withdrawal operations on a bank account that starts with
    zero balance. Your task is to detect if at any point the balance of account fallls below zero, and
    at that point function should return True. Otherwise it should return False.
    >>> below_zero([1, 2, 3])
    False
    >>> below_zero([1, 2, -4, 5])
    True
    """
    if not operations:
        return False
    balance_sum = sum(operations)
    if balance_sum == 0:
        return False
    if balance_sum < 0:
        return True

    for operation in operations:
        if operation < 0:
            continue
        balance_sum -= operation

    if balance_sum == 0:
        return False

    return True
```

### Fact

Branch coverage (C2): the True branch of `balance_sum == 0` (line 26) is never taken by the existing tests.

## H30 — task 127

### Đặc tả (docstring)

```text
You are given two intervals,
where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).
The given intervals are closed which means that the interval (start, end)
includes both start and end.
For each given interval, it is assumed that its start is less or equal its end.
Your task is to determine whether the length of intersection of these two 
intervals is a prime number.
Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)
which its length is 1, which not a prime number.
If the length of the intersection is a prime number, return "YES",
otherwise, return "NO".
If the two intervals don't intersect, return "NO".


[input/output] samples:
intersection((1, 2), (2, 3)) ==> "NO"
intersection((-1, 1), (0, 4)) ==> "NO"
intersection((-3, -1), (-5, 5)) ==> "YES"
```

### PUT

```python

def intersection(interval1, interval2):
    """You are given two intervals,
    where each interval is a pair of integers. For example, interval = (start, end) = (1, 2).
    The given intervals are closed which means that the interval (start, end)
    includes both start and end.
    For each given interval, it is assumed that its start is less or equal its end.
    Your task is to determine whether the length of intersection of these two 
    intervals is a prime number.
    Example, the intersection of the intervals (1, 3), (2, 4) is (2, 3)
    which its length is 1, which not a prime number.
    If the length of the intersection is a prime number, return "YES",
    otherwise, return "NO".
    If the two intervals don't intersect, return "NO".


    [input/output] samples:
    intersection((1, 2), (2, 3)) ==> "NO"
    intersection((-1, 1), (0, 4)) ==> "NO"
    intersection((-3, -1), (-5, 5)) ==> "YES"
    """
    # your code here
    # print(interval1, interval2)
    if interval1[0] > interval1[1] or interval2[0] > interval2[1]:
        return "NO"
    elif interval1[0] > interval2[1] or interval2[0] > interval1[1]:
        return "NO"
    else:
        start = max(interval1[0], interval2[0])
        end = min(interval1[1], interval2[1])
        # print(start, end)
        if (end - start) == 0:
            return "NO"
        elif (end - start) == 1:
            return "NO"
        else:
            for i in range(start, end):
                if i > 1:
                    for j in range(2, i):
                        if i % j == 0:
                            return "NO"
            return "YES"
```

### Fact

Statement coverage (C1): line 25 (starting with `return "NO"`) is never executed by the existing tests.

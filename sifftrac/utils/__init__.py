from typing import Callable, TypeVar
from functools import wraps
import numpy as np

from .ballparams import BallParams # noqa: F401

T = TypeVar('ReturnedType')

def memoize_property(f : Callable[[], T]) -> Callable[[], T]:
    """
    Takes a property and ensures it's
    only computed once by storing its
    result in an attribute with the
    same name plus a leading underscore.
    Allows production of a computed variable
    only when it's needed (rather than needing to
    do it at initialization) without having to recompute it
    every time it's accessed.

    # Example:
    ```python
    class MyClass:
        @memoize_property
        def expensive_computation(self):
            # Some expensive computation
            return result

    # Make a MyClass, not clear if I'll need to use the expensive computation
    my_obj = MyClass()

    i_want_to_know_something = check_something(my_obj)

    # Shoot, guess I need to compute it!
    if i_want_to_know_something:
        # Access the expensive computation, which will compute it
        # and store it in the object
        my_obj.expensive_computation
        result1 = my_obj.expensive_computation  # Computed and stored
        result2 = my_obj.expensive_computation  # Retrieved from cache
        assert result1 is result2  # Both results are the same object

        assert result2 is my_obj._expensive_computation  # Accessing the cached value directly
    ```

    This doesn't mean you should freeze it forever. If something else comes up,
    you can always change the cached value:

    ```python
    
    new_value = another_operation(...)

    my_obj._expensive_computation = new_value  # Change the cached value

    assert my_obj.expensive_computation is new_value  # Now the cached value is the new one

    """
    @wraps(f)
    def helper(*args, **kwargs):
        obj = args[0]
        undered_name = f"_{f.__name__}"
        if hasattr(obj, undered_name):
            return getattr(obj, undered_name)
        setattr(obj, undered_name, f(*args, **kwargs))
        if not hasattr(obj, '_memoized_properties'):
            obj._memoized_properties = set()
        obj._memoized_properties.add(f.__name__)
        return getattr(obj, undered_name)
    return helper

def dt_zeros_to_nan(f):
    """ Correct infs when a delta time is zero
    so they can be masked out with nan operations
    """
    def wrapper(*args, **kwargs):
        with np.errstate(divide='ignore'):
            val = np.nan_to_num(f(*args, **kwargs), posinf = np.nan, neginf = np.nan)
        return val
    return wrapper
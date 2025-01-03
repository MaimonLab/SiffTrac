from functools import wraps

from .ballparams import BallParams # noqa: F401

def memoize_property(f):
    """
    Takes a property and ensures it's
    only computed once
    """
    @wraps(f)
    def helper(*args, **kwargs):
        obj = args[0]
        undered_name = f"_{f.__name__}"
        if hasattr(obj, undered_name):
            return getattr(obj, undered_name)
        setattr(obj, undered_name, f(*args, **kwargs))
        return getattr(obj, undered_name)
    return helper
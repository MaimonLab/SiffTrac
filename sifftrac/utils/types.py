from typing import Union, Any
from pathlib import Path
import numpy as np

PathLike = Union[str, Path]

ComplexArray = np.ndarray[Any, complex]
FloatArray = np.ndarray[Any, float]
IntArray = np.ndarray[Any, int]
BoolArray = np.ndarray[Any, np.bool_]
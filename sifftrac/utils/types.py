from typing import Union, Any
from pathlib import Path
import numpy as np

PathLike = Union[str, Path]

ComplexArray = np.ndarray[Any, np.complex128]
FloatArray = np.ndarray[Any, np.float64]
IntArray = np.ndarray[Any, np.int64]
BoolArray = np.ndarray[Any, np.bool_]
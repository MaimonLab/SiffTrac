""" 
TODO: Write a module for parsing ABF files.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

import pyabf

if TYPE_CHECKING:
    from ..utils.types import PathLike

class ABF():
    """
    Wrapper around the PyABF library for `.abf` files.
    Provides access that I find slightly more... pythonic.
    Or it will when I finish it!!!
    """

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension, ideally do more """
        path = Path(path)
        valid = path.suffix == '.abf'
        return valid

    def __init__(self, path : 'PathLike', *args, **kwargs):
        """
        Parse the file at `path` with PyABF, and store its
        abf_file as an attribute in `abf_file`.

        Passes all other arguments to the PyABF constructor.

        Example
        -------
        ```python
        abf = ABF('path/to/file.abf')
        abf[0] # returns the first sweep, all channels

        abf.abf_file # access to the PyABF object
        ```

        """
        self.path = Path(path)
        self.abf_file = pyabf.ABF(self.path, *args, **kwargs)
        
    def __getitem__(self, key) -> np.ndarray:
        """
        Indexes sweeps like an array:
        `abf[0]` returns the first sweep, all channels.
        `abf[0, 1]` returns the first sweep, channel 1.

        Can also index by string for a channel (across all sweeps):
        `abf['Pockels'] returns the Pockels channel across all sweeps.
        """
        #slice-like
        if isinstance(key, tuple):
            pass
        #string-like
        elif isinstance(key, str):
            pass
            #return self.abf_file.sweepY[key]
        #return self.abf_file.setSweep(key)
    
    def __getattr__(self, key):
        """
        Forwards all other attribute requests to the PyABF object.
        """
        return getattr(self.abf_file, key)
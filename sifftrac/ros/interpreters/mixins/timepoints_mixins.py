from typing import TYPE_CHECKING
import os

import pandas as pd

if TYPE_CHECKING:
    from ....utils.types import PathLike

# Copied from Jazz

def read_n_to_last_line(filename : 'PathLike', n : int = 1):
    """Returns the nth before last line of a file (n=1 gives last line)"""
    num_newlines = 0
    with open(filename, "rb") as f:
        try:
            f.seek(-2, os.SEEK_END)
            while num_newlines < n:
                f.seek(-2, os.SEEK_CUR)
                if f.read(1) == b"\n":
                    num_newlines += 1
        except OSError:
            f.seek(0)
        last_line = f.readline().decode()
    return last_line

class HasStartAndEndpoints():
    """
    Mixin class for objects that have a start and end timestamp
    stored in a dataframe
    """
    @property
    def start_timestamp(self)->int:
        return self.df['timestamp'].values[0]
    
    @property
    def end_timestamp(self)->int:
        return self.df['timestamp'].values[-1]
    
    @property
    def start_and_end_timestamps(self)->tuple[int,int]:
        return (self.start_timestamp, self.end_timestamp)
    
    @classmethod
    def probe_start_and_end_timestamps(cls, path : 'PathLike')->tuple[int, int]:
        """ Returns the first and last timestamp as nanoseconds """
        first_row = pd.read_csv(path, sep=',', nrows=1)
        last_row = read_n_to_last_line(path, 1).split(',')
        last_row = pd.Series(last_row, index=first_row.columns)
        return (first_row['timestamp'].values[0], int(last_row['timestamp']))

    def __str__(self):
        retstr = super().__str__()
        retstr += self.__repr__()
        return retstr

    def __repr__(self):
        retstr = super().__repr__()
        retstr += f"\nStart timestamp: {self.start_timestamp}\nEnd timestamp: {self.end_timestamp}"
        return retstr

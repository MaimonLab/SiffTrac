from typing import TYPE_CHECKING, Tuple
import os

import pandas as pd
import numpy as np

from ....utils import memoize_property

if TYPE_CHECKING:
    from ....utils.types import PathLike, FloatArray, IntArray
    from ..ros_interpreter import ROSLog

# Copied from Jazz, not optimal because of the way it can't recognize
# that strings containing new lines are not genuine new lines

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

class HasTimepoints():
    """
    Mixin class for objects that have a start and end timestamp
    stored in a dataframe. Adds a 'datetime' column to the dataframe
    as well that is in UTC and localized to US/Eastern time
    """
    TIMESTAMP_COL : str = 'timestamp'
    df : pd.DataFrame

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    @property
    def timestamp(self) -> 'IntArray':
        """ Returns the timestamp column as an integer array """
        return self.df[self.__class__.TIMESTAMP_COL].values.astype(int)

    @property
    def start_timestamp(self)->int:
        return self.df[self.__class__.TIMESTAMP_COL].values[0]
    
    @property
    def end_timestamp(self)->int:
        return self.df[self.__class__.TIMESTAMP_COL].values[-1]
    
    @property
    def start_and_end_timestamps(self)->Tuple[int,int]:
        return (self.start_timestamp, self.end_timestamp)
    
    @property
    def timestamps(self)->pd.Series:
        return self.df[self.__class__.TIMESTAMP_COL]
    
    @property
    def datetimes(self)->pd.Series:
        if not hasattr(self, 'log'):
            raise AttributeError("No log containing datetimes")
        if hasattr(self.log, 'df'):
            return self.log.df['datetime']

    @classmethod
    def open(cls, path : 'PathLike')->'ROSLog':
        open_call = getattr(super(), 'open', False)
        if not (open_call and callable(open_call)):
            return
        log = open_call(path)
        if hasattr(log, 'df'):
            log.df['datetime'] = (
                pd.to_datetime(log.df[cls.TIMESTAMP_COL].values, unit='ns')
                .tz_localize('UTC')
                .tz_convert('US/Eastern')
            )
        return log

    @classmethod
    def probe_start_and_end_timestamps(cls, path : 'PathLike')->Tuple[int, int]:
        """ Returns the first and last timestamp as nanoseconds """
        first_row = pd.read_csv(path, sep=',', nrows=1)
        last_row = read_n_to_last_line(path, 2).split(',')
        last_row = pd.Series(last_row, index=first_row.columns)
        return (
            first_row[cls.TIMESTAMP_COL].values[0],
            int(last_row[cls.TIMESTAMP_COL])
        )

    def __str__(self):
        retstr = super().__str__()
        retstr += self.__repr__()
        return retstr

    def __repr__(self):
        retstr = super().__repr__()
        retstr += f"\nStart timestamp: {self.start_timestamp}\nEnd timestamp: {self.end_timestamp}"
        return retstr
    
class HasDatetimes():
    """
    Mixin class for objects that have a start and end timestamp
    stored in a dataframe. Adds a 'timestamp' column to the dataframe
    as well that is in UTC and localized to US/Eastern time
    """
    DATETIME_COL : str = 'datetime'
    df : pd.DataFrame

    @property
    @memoize_property
    def dt(self) -> 'FloatArray':
        """ Difference in timestamps between each sample in seconds """
        return self.df[self.DATETIME_COL].diff().dt.total_seconds().values.astype(float)
    
    @property
    @memoize_property
    def median_dt(self) -> float:
        """ Median delta time in seconds """
        return np.median(self.dt[1:])
    


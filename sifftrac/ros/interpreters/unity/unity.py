"""
Interpreters for various gratings experiments
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigFileParamsMixin

if TYPE_CHECKING:
    from ....utils.types import PathLike

class UnityCommandLog(ROSLog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension, ideally do more """
        path = Path(path)
        valid = path.suffix == '.csv' and 'unity_vr_driver_vrcmd' in path.name
        return valid
    
    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')
        self.df['datetime'] = (
            pd.to_datetime(self.df['timestamp'].values, unit='ns')
        )

class UnityInterpreter(
    ConfigFileParamsMixin,
    ROSInterpreter
    ):
    """
    ROS interpreter type that handles the 
    logged Unity information
    """

    LOG_TAG = '.csv'
    LOG_TYPE = UnityCommandLog
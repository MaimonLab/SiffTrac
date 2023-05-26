from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.timepoints_mixins import HasTimepoints

if TYPE_CHECKING:
    from ...utils.types import PathLike

WARNER_COLUMNS = [
    'timestamp',
    'frame_id',
    'Temperature (C)_0_channel_idx',
    'Temperature (C)_0_voltage',
]

class WarnerTemperatureLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        valid &= 'read' in path.name
        if not valid:
            return False
        cols = pd.read_csv(path, sep=',', nrows=1).columns
        valid &= all([col in cols for col in WARNER_COLUMNS])
        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')

class WarnerTemperatureInterpreter(
    GitValidatedMixin,
    ConfigFileParamsMixin,
    HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = WarnerTemperatureLog
    LOG_TAG = '.csv'

    git_config = GitConfig(
        branch = 'sct_dev',
        commit_time = '2023-01-06 14:18:25-5:00',
        package = 'mcc_driver',
        repo_name = 'mcc_driver',
        executable = 'warner_temp_control'
    )

    config_params = ConfigParams(
        packages = ['mcc_driver'],
        executables={'mcc_driver' : ['warner_temp_control']},
    )

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        super().__init__(file_path)

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df

    @property
    def temperature(self)->pd.Series:
        return self.df['Temperature (C)_0_voltage']

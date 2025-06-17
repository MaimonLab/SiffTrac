from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.timepoints_mixins import HasTimepoints, HasDatetimes

if TYPE_CHECKING:
    from ...utils.types import PathLike

WARNER_COLUMNS_OLD = [
    'timestamp',
    'frame_id',
    'Temperature (C)_0_channel_idx',
    'Temperature (C)_0_voltage',
]

WARNER_COLUMNS_NEW = [
    'timestamp',
    'temperature_measurement',
]

class WarnerTemperatureLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        valid &= any(
            appellation in path.name
            for appellation in ['read', 'measurement']
        )
                  
        if not valid:
            return False
        cols = pd.read_csv(path, sep=',', nrows=1).columns
        valid &= (
            all([col in cols for col in WARNER_COLUMNS_OLD])
            or all([col in cols for col in WARNER_COLUMNS_NEW])
        )
        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')

        if set_temp_path := next(path.parent.glob('*set_temperature*'),None):
            self.set_temp_df = pd.read_csv(set_temp_path, sep=',')


class WarnerTemperatureInterpreter(
    GitValidatedMixin,
    ConfigFileParamsMixin,
    HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = WarnerTemperatureLog
    LOG_TAG = '.csv'

    git_config = [
        GitConfig(
            branch = 'sct_dev',
            commit_time = '2023-01-06 14:18:25-5:00',
            package = 'mcc_driver',
            repo_name = 'mcc_driver',
            executable = 'warner_temp_control'
        ),
        GitConfig(
            repo_name = 'mcc_driver',
            package = 'mcc_driver',
            branch = 'sct_dev',
            executable = 'mcc1208fs_adio',
            commit_time = '2024-04-14 19:00:43-04:00',
            commit_hash = 'af2adae8e219951151a7dbcdfc9a80885ffbb228',
        )
    ]

    config_params = ConfigParams(
        packages = ['mcc_driver'],
        executables={'mcc_driver' : [
            'warner_temp_control',
            'mcc1208fs_adio',
        ]},
    )

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        super().__init__(file_path)
        # if it's using the old temperature logging convention
        # (the Thomas style MCC device), rename the columns
        if all(col in self.log.df.columns for col in WARNER_COLUMNS_OLD):
            self.log.df.rename(
                columns={
                    'Temperature (C)_0_voltage' : 'temperature_measurement'
                },
                inplace=True
            )

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df
        raise AttributeError('No temperature log found')

    @property
    def set_temperatures_df(self)->pd.DataFrame:
        if hasattr(self.log, 'set_temp_df'):
            return self.log.set_temp_df
        raise AttributeError('No set temperature log found')

    @property
    def temperature(self)->pd.Series:
        return self.df['temperature_measurement']
    
    @property
    def set_values(self)->pd.Series:
        if hasattr(self, 'set_temperatures_df'):
            return self.set_temperatures_df['Temperature (C)_0_voltage']

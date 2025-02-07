"""
Parses VR Position logs, with variations for each type of condition.
"""
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileUpOneLevelParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedUpOneLevelMixin

if TYPE_CHECKING:
    from ....utils.types import PathLike

EVENT_COLUMNS = [
    'timestamp',
    'Event type',
    'Event message'
]

SCANIMAGE_EVENTS = [
    'AcquisitionPeriod',
    'SetPmtsScanImage',
    'StopAcqScanImage',
]

BAR_EVENTS = [
    'BarSet',
    'JumpOffsetDegrees',
]

class EventsLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        if not valid:
            return False
        cols = pd.read_csv(path, sep=',', nrows=1).columns
        valid &= all([col in cols for col in EVENT_COLUMNS])
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
            .tz_localize('UTC').tz_convert('US/Eastern')
        )

class EventsInterpreter(
    GitValidatedUpOneLevelMixin,
    ConfigFileUpOneLevelParamsMixin,
    #HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = EventsLog
    LOG_TAG = '.csv'

    git_config = [
        GitConfig(
            branch = 'sct_eternarig_dev',
            commit_time = '2024-11-17 18:06:25-05:00',
            package = 'eternarig_experiment_logic',
            repo_name = 'eternarig_experiment_logic',
            executable = 'sct_sutter_bar'
        )
    ]

    config_params = ConfigParams(
        packages = ['eternarig_experiment_logic'],
        executables={
            'eternarig_experiment_logic' : [
                'sct_sutter_bar',
            ],
        },
    )

    def __str__(self) -> str:
        return self.df.__str__()

    def __repr__(self) -> str:
        return self.df.__repr__()

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df

    @property
    def bar_events(self)->pd.DataFrame:
        """
        Get rows of the df where the 'Event type' column is in BAR_EVENTS
        """
        return self.df.loc[self.df['Event type'].isin(BAR_EVENTS)]

    @property
    def temperature_events(self)->pd.DataFrame:
        return self.df.loc[self.df['Event type'] == 'WarnerTemperatureSet']

    @property
    def scanimage_events(self)->pd.DataFrame:
        return self.df.loc[self.df['Event type'].isin(SCANIMAGE_EVENTS)]
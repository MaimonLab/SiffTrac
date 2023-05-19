"""
Parses VR Position logs, with variations for each type of condition.
"""
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileUpOneLevelParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedUpOneLevelMixin
from ..mixins.timepoints_mixins import HasTimepoints

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
            commit_time = '2023-01-21 13:06:53-5:00',
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

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        # can be done appropriately
        super().__init__(file_path)

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df

    @property
    def bar_events(self)->pd.DataFrame:
        self.df.loc[self.df['Event type'] == 'BarSet']

    @property
    def temperature_events(self)->pd.DataFrame:
        self.df.loc[self.df['Event type'] == 'WarnerTemperatureSet']

    @property
    def scanimage_events(self)->pd.DataFrame:
        self.df.loc[self.df['Event type'].isin(SCANIMAGE_EVENTS)]
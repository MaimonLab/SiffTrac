from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedMixin
from ..mixins.timepoints_mixins import HasTimepoints

if TYPE_CHECKING:
    from ....utils.types import PathLike

# PICOPUMP_COLUMNS = [
#     'timestamp',
#     'picopump',
# ]

class PicoPumpLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        valid &= any(
            appellation in path.name
            for appellation in ['picopump',]
        )
                  
        if not valid:
            return False
        #cols = pd.read_csv(path, sep=',', nrows=1).columns
        #valid &= all([col in cols for col in PICOPUMP_COLUMNS])
        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')


class PicoPumpInterpreter(
    GitValidatedMixin,
    ConfigFileParamsMixin,
    HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = PicoPumpLog
    LOG_TAG = '.csv'

    git_config = [
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
        self._name = next(
            col for col in self.df.columns
            if 'picopump' in col
        )

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df
        raise AttributeError('No log found')
    
    @property
    def flow(self)->pd.Series:
        return self.df[self._name]
    
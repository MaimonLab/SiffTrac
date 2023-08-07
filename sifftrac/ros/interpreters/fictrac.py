""" Simply wraps the fulltrac output -- DOES NOT do unit conversions """

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import numpy as np

from ...utils import BallParams
from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.timepoints_mixins import HasTimepoints

if TYPE_CHECKING:
    from ...utils.types import PathLike, ComplexArray, FloatArray, IntArray
    from pandas._typing import ArrayLike

FICTRAC_COLUMNS = [
    'timestamp',
    'frame_id',
    'frame_counter',
    'delta_rotation_cam_0',
    'delta_rotation_cam_1',
    'delta_rotation_cam_2',
    'delta_rotation_error',
    'delta_rotation_lab_0',
    'delta_rotation_lab_1',
    'delta_rotation_lab_2',
    'absolute_rotation_cam_0',
    'absolute_rotation_cam_1',
    'absolute_rotation_cam_2',
    'absolute_rotation_lab_0',
    'absolute_rotation_lab_1',
    'absolute_rotation_lab_2',
    'integrated_position_lab_0',
    'integrated_position_lab_1',
    'integrated_heading_lab',
    'animal_movement_direction_lab',
    'animal_movement_speed',
    'integrated_motion_0',
    'integrated_motion_1',
    'sequence_counter'
]

class FicTracLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        if not valid:
            return False
        cols = pd.read_csv(path, sep=',', nrows=1).columns
        valid &= all([col in cols for col in FICTRAC_COLUMNS])
        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')
        self.df['complex_pos'] = self.df['integrated_position_lab_0'] + 1j*self.df['integrated_position_lab_1']

class FicTracInterpreter(
    GitValidatedMixin,
    ConfigFileParamsMixin,
    HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = FicTracLog
    LOG_TAG = '.csv'

    git_config = GitConfig(
        branch = 'main',
        commit_time = '2022-08-19 16:51:19-04:00',
        package = 'fictrac_ros2',
        repo_name = 'fictrac_ros2',
        executable = 'trackmovements'
    )

    config_params = ConfigParams(
        packages = ['fictrac_ros2'],
        executables={'fictrac_ros2' : ['trackmovements']},
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
        raise AttributeError("No log instantiated")

    @property
    def position(self)->ComplexArray:
        """ Complex position """
        return self.df['complex_pos'].values

    @property
    def x_position(self)->FloatArray:
        """ In rad """
        return (
            self.df['integrated_position_lab_0'].values
        )
        
    @property
    def y_position(self)->FloatArray:
        """ In rad """
        return (
            self.df['integrated_position_lab_1'].values
        )
        
    @property
    def heading(self)->FloatArray:
        return self.df['integrated_heading_lab'].values
        
    @property
    def timestamp(self)->IntArray:
        return self.df['timestamp'].values
    
    @property
    def movement_speed(self)->FloatArray:
        """ In rad / sec """
        return (
            self.df['animal_movement_speed'].values.astype(float) / 
            self.df['datetime'].diff().dt.total_seconds().values.astype(float)
        )
        
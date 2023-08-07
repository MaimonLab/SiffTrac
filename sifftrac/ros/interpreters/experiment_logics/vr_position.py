"""
Parses VR Position logs, with variations for each type of condition.

VR Position uses 'natural' units, e.g. "Bar is up", "Up is 0 degrees",
"Units are mm" etc.
"""
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

import pandas as pd
import numpy as np

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileUpOneLevelParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedUpOneLevelMixin
from ..mixins.timepoints_mixins import HasTimepoints

if TYPE_CHECKING:
    from ....utils.types import PathLike, ComplexArray, FloatArray, IntArray, BoolArray

VR_COLUMNS = [
    'timestamp',
    'frame_id',
    'rotation_x',
    'rotation_y',
    'rotation_z',
    'position_x',
    'position_y',
    'position_z',
]

class VRPositionLog(ROSLog):

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension and column titles """
        path = Path(path)
        valid = path.suffix == '.csv'
        if not valid:
            return False
        cols = pd.read_csv(path, sep=',', nrows=1).columns
        valid &= all([col in cols for col in VR_COLUMNS])
        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            raise ValueError(f"""
                File {path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        
        self.df = pd.read_csv(path, sep=',')
        self.df['complex_pos'] = 1j*(self.df['position_x'] + 1j*self.df['position_y'])

class VRPositionInterpreter(
    GitValidatedUpOneLevelMixin,
    ConfigFileUpOneLevelParamsMixin,
    HasTimepoints,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = VRPositionLog
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
        self.bar_in_front_angle : float = 0.0
        self.ball_radius : float = 3.0
        self.projector_config : Optional[list['ConfigParams']] = None
        super().__init__(file_path)

    def set_projector_config(self, projector_config : list['ConfigParams']):
        """
        To specify the type of projector used -- discerned by
        the ProjectorDriver config, not by the VRPosition per se
        """
        self.projector_config = projector_config

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df

    @property
    def position(self)->ComplexArray:
        """ Complex valued, in mm"""
        return (
            self.df['complex_pos'].values.astype(np.complex128)
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        )

    @property
    def x_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        ).real
        
    @property
    def y_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        ).imag
        
    @property
    def heading(self)->FloatArray:
        """ 0 is bar in front, for bar type experiments """
        return np.angle(
            np.exp(1j*self.df['rotation_z'].values.astype(float))
            * np.exp(-1j*self.bar_in_front_angle)
        )
    
    @property
    def unwrapped_heading(self)->FloatArray:
        """ 2*pi*n is bar in front, for bar type experiments """
        return np.unwrap(self.heading)
        
    @property
    def timestamp(self)->np.ndarray:
        return self.df['timestamp'].values
    
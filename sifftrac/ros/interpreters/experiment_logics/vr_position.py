"""
Parses VR Position logs, with variations for each type of condition.

VR Position uses 'natural' units, e.g. "Bar is up", "Up is 0 degrees",
"Units are mm" etc.
"""
from pathlib import Path
from typing import Optional, List

import pandas as pd
import numpy as np

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileUpOneLevelParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedUpOneLevelMixin
from ..mixins.timepoints_mixins import HasTimepoints

from ....utils.types import PathLike, ComplexArray, FloatArray
from ....utils import memoize_property

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
        self.df['complex_pos'] = 1j*(self.df['position_x'] - 1j*self.df['position_y'])

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

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        # can be done appropriately
        self.bar_in_front_angle : float = 0.0
        self.ball_radius : float = 3.0
        self.projector_config : Optional[List['ConfigParams']] = None
        super().__init__(file_path)

    def set_projector_config(self, projector_config : List['ConfigParams']):
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
    @memoize_property
    def position(self)->ComplexArray:
        """ Complex valued, in mm"""
        return (
            self.df['complex_pos'].values.astype(np.complex128)
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        )

    @property
    @memoize_property
    def x_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        ).real
        
    @property
    @memoize_property
    def y_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_angle)
            * self.ball_radius
        ).imag
        
    @property
    @memoize_property
    def vr_translation_speed(self)->FloatArray:
        """ In mm / sec """
        return (
            np.abs(np.diff(self.position, prepend=np.nan)) 
            / self.df['datetime'].diff().dt.total_seconds().values.astype(float)
        )
    
    @property
    @memoize_property
    def vr_heading(self)->FloatArray:
        """ 0 is bar in front, for bar type experiments """
        return np.angle(
            np.exp(1j*self.df['rotation_z'].values.astype(float))
            * np.exp(-1j*self.bar_in_front_angle)
        )

    @property
    @memoize_property
    def unwrapped_heading(self)->FloatArray:
        """ 2*pi*n is bar in front, for bar type experiments """
        return np.unwrap(self.vr_heading)
        
    @property
    def timestamp(self)->np.ndarray:
        return self.df['timestamp'].values
    
    def correct_position_for_bar_jump(self, jump_time : int, jump_angle : float)->None:
        """
        Corrects the position property for a bar jump at a given time
        (in epoch timestamps) and angle (in radians). Presumes that the
        *bar position itself* is already corrected. Modifies **in place**,
        meaning that the position properties will be updated.

        ## Parameters

        - ```jump_time : int```
            The time of the bar jump in epoch time (nanoseconds)

        - ```jump_angle : float```
            The angle of the bar jump in radians        
        """

        # Find the index of the jump time
        jump_idx = np.searchsorted(self.timestamp, jump_time)

        new_position = self.position.copy()

        # Correct the position
        new_position[jump_idx:] = (
            new_position[jump_idx:] - new_position[jump_idx]
        ) * np.exp(-1j*jump_angle) + new_position[jump_idx]
        
        # Have to undo the transformations applied to the position
        # to get back to 'complex_pos'
        self.log.df['complex_pos'] = (
            new_position
            *np.exp(-1j*self.bar_in_front_angle)
            /self.ball_radius
        )

        # Delete the memoized ones
        if hasattr(self, '_position'):
            del self._position
        if hasattr(self, '_x_position'):
            del self._x_position
        if hasattr(self, '_y_position'):
            del self._y_position
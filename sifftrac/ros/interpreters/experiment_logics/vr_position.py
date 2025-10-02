"""
Parses VR Position logs, with variations for each type of condition.

VR Position uses 'natural' units, e.g. "Bar is up", "Up is 0 degrees",
"Units are mm" etc.
"""
from pathlib import Path
from typing import Optional, List, Callable, Any
from copy import copy

import pandas as pd
import numpy as np

from ..ros_interpreter import ROSInterpreter, ROSLog
from ..mixins.config_file_params import ConfigParams, ConfigFileUpOneLevelParamsMixin
from ..mixins.git_validation import GitConfig, GitValidatedUpOneLevelMixin
from ..mixins.timepoints_mixins import HasTimepoints, HasDatetimes

from ....utils.types import PathLike, ComplexArray, FloatArray
from ....utils import memoize_property, dt_zeros_to_nan

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
        self.df['complex_pos'] = -self.df['position_y'] + 1j*self.df['position_x']

class VRPositionInterpreter(
    GitValidatedUpOneLevelMixin,
    ConfigFileUpOneLevelParamsMixin,
    HasTimepoints,
    HasDatetimes,
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
        self.bar_in_front_heading : float = 0.0
        self.ball_radius : float = 3.0
        self.projector_config : Optional[List['ConfigParams']] = None
        super().__init__(file_path)

    def set_projector_config(self, projector_config : List['ConfigParams']):
        """
        To specify the type of projector used -- discerned by
        the ProjectorDriver config, not by the VRPosition per se
        """
        self.projector_config = projector_config

    def rotate_axes(self,
                    rotation_vector : np.ndarray[Any, float],
                    lock_heading : bool = True):
        """
        Rotates the axes of the VR position log by the given rotation vector
        (in radians), adjusting the position and heading accordingly.
        If `lock_heading` is True, it will not adjust the heading.

        Warning: only makes sense if the VR environment itself is not determined
        by x and y position -- otherwise will incorrectly translate the interpreted
        VR environment!

        # Arguments
        * `rotation_vector : np.ndarray[Any, float]`
            A 3-element array representing the rotation vector in radians
            (dx, dy, dh) where dx and dy are the x and y translations
            and dh is the heading rotation in radians. Usually should come
            from a `FullTrac` interpreter's `minimize_sideslip` method.
        * `lock_heading : bool`
            If True, the heading will not be adjusted, only the position.

        """

        raise NotImplementedError(
            "This method is not implemented yet. "
            "I'm actually not sure what it would mean to rotate the VR position axes "
            "if it's a true 2D environment."
        )
        from ..fictrac import trajectory_from_deltas, rotate_about_axis_angle
        x_y_traj = self.df['complex_pos'].values.astype(np.complex128)
        dr = np.diff(x_y_traj, prepend = 0.0)
        dx, dy = dr.real, dr.imag
        dh = np.diff(np.unwrap(self.vr_heading), prepend = 0.0)

        disp_mat = np.stack((dx, dy, dh), axis = -1)

        rotated_deltas = rotate_about_axis_angle(
            disp_mat,
            rotation_vector,
        )

        disp_mat[:, 2] = dh

        new_traj = trajectory_from_deltas(
            rotated_deltas,
        )

        _x_position = new_traj.real
        _y_position = new_traj.imag
        _h = new_traj[:, 2]

        self.df['complex_pos'] = _x_position + 1j*_y_position

        for attr in ['_position', '_x_position', '_y_position', '_vr_translation_speed']:
            if hasattr(self, attr):
                delattr(self, attr)

        if not lock_heading:
            self.df['rotation_z'] = _h
            for attr in ['_vr_heading', '_unwrapped_heading']:
                if hasattr(self, attr):
                    delattr(self, attr)

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
            * np.exp(1j*self.bar_in_front_heading)
            * self.ball_radius
        )

    @property
    @memoize_property
    def x_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_heading)
            * self.ball_radius
        ).real
        
    @property
    @memoize_property
    def y_position(self)->FloatArray:
        """ In mm """
        return (
            self.df['complex_pos'].values
            * np.exp(1j*self.bar_in_front_heading)
            * self.ball_radius
        ).imag
        
    @property
    @dt_zeros_to_nan
    @memoize_property
    def vr_translation_speed(self)->FloatArray:
        """ In mm / sec """
        return (
            np.abs(np.diff(self.position, prepend=np.nan)) 
            / self.dt
        )
    
    @dt_zeros_to_nan
    def vr_translational_speed_filtered(
        self,
        filter_fn : Callable[[np.ndarray[Any, float]], np.ndarray[Any, complex]],
        replace_nans_with : float = 0.0
    ) -> FloatArray:
        
        """
        In mm / sec

        # Arguments 
        * `filter_fn : Callable`
            The filter to apply to the frame-by-frame translational _velocity_
            (not speed!) Should be a `Callable` with the signature
            `filter_fn(arr : np.ndarray[Any, complex]) -> np.ndarray[Any, float]`
        
        """
        position = copy(self.position)
        position[np.isnan(position)] = replace_nans_with
        filt_position = filter_fn(position)
        return np.abs(np.diff(filt_position, prepend=np.nan)) / self.dt
    
    @property
    @memoize_property
    def bar_position(self) -> FloatArray:
        """ In radians, where 0 is bar in front and -pi/2 is bar to the left """
        return np.angle(
            self.df['rotation_z'].values.astype(float)
        )

    @property
    @memoize_property
    def vr_heading(self)->FloatArray:
        """
        $Pi/2$ is bar in front, for bar type experiments
        Note that this is the OPPOSITE of the bar position if
        there is a bar!
        """
        return np.angle(
            np.exp(-1j*self.df['rotation_z'].values.astype(float))
            * np.exp(-1j*self.bar_in_front_heading)
        )

    @property
    @memoize_property
    def unwrapped_heading(self)->FloatArray:
        """ 2*pi*n is bar in front, for bar type experiments """
        return np.unwrap(self.vr_heading)
        
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
            *np.exp(-1j*self.bar_in_front_heading)
            /self.ball_radius
        )

        # Delete the memoized ones
        for attr in ['_position', '_x_position', '_y_position', '_vr_translation_speed']:
            if hasattr(self, attr):
                delattr(self, attr)
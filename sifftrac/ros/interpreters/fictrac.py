""" Simply wraps the fulltrac output -- DOES NOT do unit conversions """

from pathlib import Path
from typing import Callable, Union, Any
import warnings
from copy import copy

import pandas as pd
import numpy as np

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.timepoints_mixins import HasTimepoints, HasDatetimes

from ...utils.types import PathLike, ComplexArray, FloatArray, IntArray
from ...utils import memoize_property, dt_zeros_to_nan
    
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
    HasDatetimes,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TYPE = FicTracLog
    LOG_TAG = '.csv'

    git_config = [
        GitConfig(
            branch = 'main',
            commit_time = '2022-08-19 16:51:19-04:00',
            package = 'fictrac_ros2',
            repo_name = 'fictrac_ros2',
            executable = 'trackmovements'
        ),
        GitConfig(
            branch = 'dev',
            commit_time = '2024-03-17 14:29:10-04:00',
            package = 'fictrac_ros2',
            repo_name = 'fictrac_ros2',
            executable = 'trackmovements'
        ),
        GitConfig(
            branch = 'dev',
            package = 'flir_camera_driver',
            commit_time = '2024-10-16 11:38:07-04:00',
            repo_name = 'flir_camera_driver',
            executable = 'publish_camera'
        )
    ]   

    config_params = ConfigParams(
        packages = ['fictrac_ros2', 'flir_camera_driver'],
        executables={'fictrac_ros2' : ['trackmovements'],
                     'flir_camera_driver' : ['publish_camera']
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
        raise AttributeError("No log instantiated")

    @property
    @memoize_property
    def position(self)->ComplexArray:
        """ Complex position (in radians) """
        return self.df['complex_pos'].values

    @property
    @memoize_property
    def x_position(self)->FloatArray:
        """ In rad """
        return (
            self.df['integrated_position_lab_0'].values
        )
        
    @property
    @memoize_property
    def y_position(self)->FloatArray:
        """ In rad """
        return (
            self.df['integrated_position_lab_1'].values
        )
        
    @property
    @memoize_property
    def heading(self)->FloatArray:
        """
        Note that in most fictrac rigs, this is actually INVERTED
        because the first users did not correct for an extra mirror
        in the camera.... To know if your rig is mirrored, check the
        `mirrored` property of this class.
        """
        return self.df['integrated_heading_lab'].values
    
    @property
    def mirrored(self)->bool:
        """
        Only applicable on rigs where there IS a mirror between the camera
        and the ball! TODO find a way to demarcate if this is true.... I don't know
        if there is a way to do this definitively though...
        """
        if not hasattr(self, 'experiment_config') or self.experiment_config is None:
            warnings.warn("No experiment config found -- assuming mirrored")
            return True
        image_topic_name = (
            next(config for config in self.experiment_config if 'fictrac_ros2' in config.packages)
            .parameters['image_topic']
        )

        ball_cam = next(
            config for config in self.experiment_config if (
                'flir_camera_driver' in config.packages
                and image_topic_name == config.parameters['image_topic']
            )
        )

        if 'camera_settings' not in ball_cam.parameters:
            warnings.warn("No `camera_settings` parameter found -- assuming mirrored")
            return True
        if 'ReverseX' not in ball_cam.parameters['camera_settings']:
            warnings.warn("No `ReverseX` parameter found -- assuming mirrored")
            return True
        return not ball_cam.parameters['camera_settings']['ReverseX']

    @property
    @memoize_property
    def cheading(self)->ComplexArray:
        """
        Complex heading

        Note that in most fictrac rigs, this is actually INVERTED
        because the first users did not correct for an extra mirror
        in the camera.... To know if your rig is mirrored, check the
        `mirrored` property of this class.
        
        """
        return np.exp(1j*self.heading)
        
    @property
    @dt_zeros_to_nan
    @memoize_property
    def angular_velocity(self)->FloatArray:
        """ In rad / sec -- positive means counterclockwise """
        return (
                -np.angle(self.cheading[1:]/self.cheading[:-1]) /
                self.dt[1:]
            )

    @dt_zeros_to_nan
    def angular_velocity_filtered(self,
        filter_fn : Callable[[np.ndarray[Any, complex]], np.ndarray[Any, float]],
        replace_nans_with : float = 0.0,
    ) -> FloatArray:
        """
        In rad / sec -- positive means counterclockwise

        # Arguments 
        * `filter_fn : Callable`
            The filter to apply to the frame-by-frame translational _velocity_
            (not speed!) Should be a `Callable` with the signature
            `filter_fn(arr : np.ndarray[Any, complex]) -> np.ndarray[Any, float]`
        
        """

        cheading = copy(self.cheading)
        cheading[np.isnan(cheading)] = replace_nans_with
        filt_cheading = filter_fn(cheading)
        return -np.angle(
                filt_cheading[1:]/filt_cheading[:-1]
            ) / self.dt[1:]
    
    @property
    @dt_zeros_to_nan
    @memoize_property
    def movement_speed(self)->FloatArray:
        """ In rad / sec (I'm not actually sure what this column is supposed to be so
        I read it from fictrac instead of computing it. Warning -- will not transform
        with rotation / sideslip minimization)"""
        return (
            self.df['animal_movement_speed'].values.astype(float)[1:] / 
            self.dt[1:]
        )
    
    @property
    @dt_zeros_to_nan
    @memoize_property
    def translational_speed(self)->FloatArray:
        """ In rad / sec """
        return np.abs(self.heading_projection) / self.dt[1:]
    
    @dt_zeros_to_nan
    def translational_speed_filtered(
            self,
            filter_fn : Callable[[np.ndarray[Any, float]], np.ndarray[Any, complex]],
            replace_nans_with : float = 0.0,
        ) -> FloatArray:
        """ Filters translational speed BEFORE applying the absolute value, 
        so that frame-to-frame jitter is not added in. Result is in rad/sec.

        # Arguments

        * `filter_fn : Callable`
            The filter to apply to the frame-by-frame translational _velocity_
            (not speed!) Should be a `Callable` with the signature
            `filter_fn(arr : np.ndarray[Any, complex]) -> np.ndarray[Any, float]`
        
        # Returns

        `FloatArray` : The filtered translational speed (in radians / sec)
        """

        heading_proj = copy(self.heading_projection)
        heading_proj[np.isnan(heading_proj)] = replace_nans_with
        return np.abs(filter_fn(heading_proj)/self.dt[1:])

    @property
    @dt_zeros_to_nan
    @memoize_property
    def heading_projection(self)->ComplexArray:
        """
        Projects translation onto heading 
        Real part is aligned part, imaginary part is orthogonal part.
        For every pair of timepoints, uses the heading
        at the start of the motion. Heading theta = 0 is
        aligned with the x-axis -- to the fly's right!
        """
        return np.diff(self.position) / self.cheading[:-1]

    @property
    @dt_zeros_to_nan 
    @memoize_property
    def forward_velocity(self) -> FloatArray:
        """
        In rad / sec -- project translational speed onto heading --
        """
        return np.imag(self.heading_projection)/self.dt[1:]
                
    @property
    @dt_zeros_to_nan
    @memoize_property
    def sideslip(self):
        """
        In rad / sec -- translational speed orthogonal to heading,
        with positive values corresponding to ego-centric "rightward".
        """
        return np.real(self.heading_projection)/self.dt[1:]
    
    def minimize_sideslip(self, lock_heading : bool = True, starting_idx : int = 0, **kwargs) -> np.ndarray:
        """
        Returns the rotation matrix applied to the current
        (x, y, z) coordinates that minimizes the sideslip, as well
        as adjusting the internal parameters of the interpreter
        itself (without adjusting the underlying log file).

        # Arguments
        * `lock_heading : bool`
            If True, the fictrac heading will not be modified,
            though it will be free to rotate in the fitting procedure

        * `starting_idx : int`
            The index of samples to start at. Sometimes the first several
            minutes of the recording are just the freely spinning ball --
            that would be bad to optimize around!

        * `**kwargs` : Additional arguments to pass to the optimizer. Also
            allows hidden keywords for debugging...

        # Returns
        `np.ndarray` : The rotation vector in radians that minimizes the sideslip.
        The rotation vector should be applied to the x, y, and z axes about which
        rotation would correspond to (sideslip, forward, heading).
        """
        import scipy.optimize as opt

        r = np.zeros(3, dtype=float)
        delta_dataframe = self.df[['delta_rotation_lab_0', 
                                   'delta_rotation_lab_1',
                                   'delta_rotation_lab_2']].values[starting_idx:]

        only_rot = kwargs.pop('only_rot') if 'only_rot' in kwargs else False # for debugging
        if only_rot:
            warnings.warn(
                "Only rotating the data, only useful for debugging purposes",
                RuntimeWarning,
            )
            lock_heading = False

        def _objective(x):
            """
            Mean sideslip + RMS sideslip
            """
            y = rotate_about_axis_angle(delta_dataframe, x)
            return (
                np.sqrt(np.mean(np.square(y[:, 0])))
                + np.abs(np.mean(y[:, 0]))
            )

        ret = opt.minimize(
            _objective, r,
            method='Nelder-Mead',
            bounds=[(-np.pi/2, np.pi/2),] * 3,
            **kwargs
        )

        if ret.success:
            r = ret.x
            if only_rot:
                r[0], r[1] = 0.0, 0.0
            
            # Applies to the _whole_ dataset, not just the `starting_idx` part
            delta_dataframe = self.df[['delta_rotation_lab_0',
                                       'delta_rotation_lab_1',
                                       'delta_rotation_lab_2']].values
            
            rotated_deltas = rotate_about_axis_angle(delta_dataframe, r)
            self._axis_rotation = r
            if lock_heading:
                rotated_deltas[:, 2] = np.diff(np.unwrap(self.heading), prepend = 0.0)

            new_traj = trajectory_from_deltas(
                rotated_deltas
            )

            # Memoized properties will need to be cleared because
            # they may not be valid anymore.
            if hasattr(self, '_memoized_properties'):
                for prop in self._memoized_properties:
                    if hasattr(self, f'_{prop}'):
                        delattr(self, f'_{prop}')

            self._x_position = new_traj[:, 0]
            self._y_position = new_traj[:, 1]
            h = new_traj[:, 2]

            self._position = self._x_position + 1j*self._y_position
            if not lock_heading:
                self._heading = h
                self._cheading = np.exp(1j*h)

            
        else:
            warnings.warn(
                f'\n*** Optimization failed with message:'
                f'\n\t{ret.message}\n',
                RuntimeWarning,
            )

        return r
    
def rvec_to_mat(vec : np.ndarray) -> np.ndarray:
    """
    Compute 3x3 rotation matrix from angle-axis representation.

    Parameters
    ----------
    vec :
        angle-axis rotation vector.

    Returns
    -------
    np.ndarray
        Transformation matrix of the same rotation.
    """
    norm = np.linalg.norm(vec)
    if norm == 0.:
        return np.eye(3)
    x, y, z = vec[0] / norm, vec[1] / norm, vec[2] / norm
    c, s, d = np.cos(norm), np.sin(norm), (1 - np.cos(norm))
    return np.array([
        [c + d*x*x, d*x*y - s*z, d*x*z + s*y],
        [d*x*y + s*z, c + d*y*y, d*y*z - s*x],
        [d*x*z - s*y, d*y*z + s*x, c + d*z*z]
    ])


def rotate_about_z(
    vec: Union[list, np.ndarray],
    angle: Union[float, list, np.ndarray]
):
    """
    Rotate a list of 3-D vectors around the positive z-axis.

    Parameters
    ----------
    vec : list, np.ndarray
        a 3-D vector or list of vectors to rotate.
    angle : float, list, np.ndarray
        amount of rotation or list of rotation amounts in radians.

    Returns
    -------
    np.ndarray
        Rotated 3-D vector or array of rotated vectors.
    """

    if isinstance(angle, np.ndarray):
        return np.matmul(
            np.stack([
                np.stack([
                    np.cos(angle), -np.sin(angle), np.zeros_like(angle)
                ], axis=-1),
                np.stack([
                    np.sin(angle), np.cos(angle), np.zeros_like(angle)
                ], axis=-1),
                np.stack([
                    np.zeros_like(angle), np.zeros_like(angle), np.ones_like(angle)
                ], axis=-1),
            ], axis=1), vec.reshape(-1, 3, 1)
        )[..., 0]

    return np.matmul(
        np.array([
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1]
        ]), vec
    )

def rotate_about_axis_angle(
    vec: np.ndarray,
    r: Union[list, np.ndarray],
) -> np.ndarray:
    """
    Rotate a list of 3-D vectors around a given axis.

    Parameters
    ----------
    vec : np.ndarray
        list of 3-D vectors to rotate.
    r : list, np.ndarray
        angle-axis representation of the rotation vector in radians.

    Returns
    -------
    np.ndarray
        array of rotated 3-D vectors.
    """

    R = rvec_to_mat(r)
    return (R @ vec.T).T

def trajectory_from_deltas(dr_dat: np.ndarray) -> np.ndarray:
    """
    Generate 2-D fly trajectory based on input array of ball rotations.
    
    Note the input should be rotations between each frame in axis-angle
    representation, NOT the Euler angle representation of the ball orientation.
    
    This function assumes:
    1. Geodesic approximation: ball performs only one rotation around a single
    axis per frame.
    2. No slip: magnitude of ball rotation in xy is same as arclength of the
    trajectory per frame.
    3. Rotations at each frame indicates rotation to arrive at ball orientation
    at that frame from the previous frame.

    Parameters
    ----------
    dr_dat : np.ndarray
        array of ball rotations in x-y-z order (side-forw-head)

    Returns
    -------
    np.ndarray
        array containing fly position and heading at each frame: [[x, y, h], ...]
    """

    assert dr_dat.ndim == 2 and dr_dat.shape[1] == 3

    dx = dr_dat[:, 1]       # forward
    dy = -dr_dat[:, 0]      # sideslip
    dh = -dr_dat[:, 2]      # heading change

    h = np.angle(np.exp(1j*np.cumsum(dh)))

    # integrating 2-D velocity vector to get position
    v = np.stack([
        dx,
        dy,
        np.zeros_like(dx)
    ], axis=-1)

    # displacement magnitude decreases due to circular arc of trajectory
    v *= np.sin(dh[:, None]/2 + 1e-20) / (dh[:, None]/2 + 1e-20)

    # displacement direction is between previous and current heading
    r = np.cumsum(
        rotate_about_z(
            v, np.angle(np.exp(1j*(h - dh/2)))
        ),
        axis=0
    )

    return np.stack(
        [r[:, 0], r[:, 1], h],
        axis=-1
    )
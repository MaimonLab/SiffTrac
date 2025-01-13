""" Simply wraps the fulltrac output -- DOES NOT do unit conversions """

from pathlib import Path
from typing import Callable, Any
import warnings

import pandas as pd
import numpy as np

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.timepoints_mixins import HasTimepoints

from ...utils.types import PathLike, ComplexArray, FloatArray, IntArray
from ...utils import memoize_property
    
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

def dt_zeros_to_nan(f):
    """ Correct infs when a delta time is zero
    so they can be masked out with nan operations
    """
    def wrapper(*args, **kwargs):
        return np.nan_to_num(f(*args, **kwargs), posinf = np.nan, neginf = np.nan)
    return wrapper
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
    def position(self)->ComplexArray:
        """ Complex position (in radians) """
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
    def dt(self)->'FloatArray':
        """ Difference in timestamps between each sample in seconds """
        return self.df['datetime'].diff().dt.total_seconds().values.astype(float)
    
    @property
    @memoize_property
    def median_dt(self) -> float:
        """ Median delta time in seconds """
        return np.median(self.dt[1:])
    
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
    def timestamp(self)->IntArray:
        return self.df['timestamp'].values
    
    @property
    @dt_zeros_to_nan
    @memoize_property
    def angular_velocity(self)->FloatArray:
        """ In rad / sec -- positive means counterclockwise """
        return (
            -np.angle(self.cheading[1:]/self.cheading[:-1]) /
            self.dt[1:]
        )
    
    @property
    @dt_zeros_to_nan
    @memoize_property
    def movement_speed(self)->FloatArray:
        """ In rad / sec """
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
    
    def translational_speed_filtered(
            self,
            filter_fn : Callable[[np.ndarray[Any, float]], np.ndarray[Any, complex]]
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

        return np.abs(filter_fn(self.heading_projection/self.dt[1:]))

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
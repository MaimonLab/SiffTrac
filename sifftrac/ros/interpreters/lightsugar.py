"""
Interprets the log from the so-called `LightSugarDriver` package
"""

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import pandas as pd

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin

if TYPE_CHECKING:
    from ...utils.types import PathLike

class LightSugarLog(ROSLog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension, ideally do more """
        path = Path(path)
        valid = path.suffix == '.csv' and 'light_sugar_driver' in path.name
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
        )

class LightSugarInterpreter(
    ConfigFileParamsMixin,
    ROSInterpreter
    ):
    """ ROS interpreter for the LightSugarDriver node"""

    LOG_TAG = '.csv'
    LOG_TYPE = LightSugarLog

    # TODO: implement git validation
    # git_config = [
    #     GitConfig(

    #     )
    # ]

    config_params = ConfigParams(
        packages = ['light_sugar_driver'],
        executables={
            'light_sugar_driver' : ['light_sugar_driver_node',],
        }
    )

    @property
    def df(self)->pd.DataFrame:
        if hasattr(self.log, 'df'):
            return self.log.df

    @property
    def feeding_events(self)->Iterable[pd.Series]:
        """
        Returns rows of the df where the 'sugar_feed_active' column is true
        """
        return (x for _, x in self.df[
            self.df['sugar_feed_active'].values
            #self.df['sugar_feed_active'] == True
        ].iterrows())
    
    @property
    def laser_events(self)->Iterable[pd.Series]:
        """
        Returns rows of the df where any of the laser columns are true
        """
        return (x for _, x in self.df[
            self.df['laser_const_set_active'].values
            or self.df['laser_exponential_set_active'].values
            #(self.df['laser_const_set_active'] == True)
            #| (self.df['laser_exponential_set_active'] == True)
        ].iterrows())



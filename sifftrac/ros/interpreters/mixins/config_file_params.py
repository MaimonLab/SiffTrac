"""
Contains a mixin for finding and checking a config .yaml file
for appropriate experimental parameters
"""

from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING, Union
import logging
from dataclasses import dataclass, field

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from ....utils.types import PathLike

@dataclass
class ConfigParams():
    """
    A class for storing configuration metadata for an executable.
    """
    packages : Union[str,List[str]] = field(default_factory=list)
    executables : Union[str,Dict[str,List[str]]] = field(default_factory=dict) # key: package, value: list of executables
    parameters : Dict[str, List[str]] = field(default_factory=dict) # names of the parameters that are used for each executable
    param_values : Dict[str, Any] = field(default_factory=dict) # key: parameter name, value: parameter value

class ConfigFileParamsMixin():
    """
    A mixin for ROS interpreters that validates the git commit
    corresponding to the data being logged and ensures it's
    compatible with the interpreter. To use, define a class
    attribute config_params of type ConfigParams with a list
    of packages and a dict of executables for each package.
    """

    config_params = ConfigParams()
    experiment_config : List['ConfigParams']

    def __init__(self, file_path : 'PathLike', *args, **kwargs):
        file_path = Path(file_path)
        try:
            putative_config_file = next(
                (
                    path for path in file_path.parent.glob('*config.yaml')
                    if not (path.name.startswith('._'))
                ) , None
            )
            if putative_config_file is None:
                # try the file_path just to be sure
                putative_config_file = next(
                    (
                        path for path in file_path.glob('*config.yaml')
                        if not (path.name.startswith('._'))
                    )
                )
            if hasattr(self.__class__, 'config_params'):
                self.validate_config(putative_config_file)
            else:
                logging.warning(
                    f"""No config_params attribute found for {self.__class__.__name__}.
                    Unable to validate configuration file and store parameters.
                    To fix, implement a class attribute config_params of type ConfigParams.
                    """
                )
                self.experiment_config = None
        except Exception as e:
            logging.warning(
                f"""Failed to read config file found for {self.__class__.__name__}.
                Unable to validate configuration file and store parameters.
                Exception: \n{e}
                """
            )
            self.experiment_config = None
        super().__init__(file_path, *args, **kwargs)

    def validate_config(self, config_file_path : 'PathLike'):
        """
        Validates the configuration file for the interpreter.
        """
        config_file_path = Path(config_file_path)

        # load the git state file
        config_yaml = YAML()
        config_data = config_yaml.load(config_file_path)
        config_data : dict[str, dict] = config_data['compiled_config']

        known_config_params = self.__class__.config_params

        # Find the executable(s) for this interpreter class,
        # store a list of tuples, one with the data from the
        # .yaml file that matches at least one GitConfig for
        # this class, and one which is the corresponding GitConfig

        this_data = [
            config_data
            for node_name, config_data in config_data.items()
            if 
                'package' in config_data and
                config_data['package'] in known_config_params.packages and
                config_data['executable'] in known_config_params.executables[config_data['package']]
        ]

        if len(this_data) == 0:
            logging.warning(f"""
                Could not successfully parse config file for {config_file_path}.\n
            """)
            return

        configs = []
        for config in this_data:
            configs.append(
                ConfigParams(
                    packages = config['package'],
                    executables = config['executable'],
                    parameters = config['parameters'],
                    param_values = config['parameters']
                )
            ) 
        self.experiment_config = configs

class ConfigFileUpOneLevelParamsMixin(ConfigFileParamsMixin):
    """
    For config files that are one level up from the data file.
    """

    def validate_config(self, config_file_path : 'PathLike'):
        """
        Validates the configuration file for the interpreter.
        """
        config_file_path = Path(config_file_path).parent
        super().validate_config(config_file_path)
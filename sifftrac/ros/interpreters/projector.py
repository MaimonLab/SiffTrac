from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from .ros_interpreter import ROSInterpreter, ROSLog
from .mixins.git_validation import GitConfig, GitValidatedMixin
from .mixins.config_file_params import ConfigParams, ConfigFileParamsMixin

if TYPE_CHECKING:
    from ...utils.types import PathLike

class ProjectorLog(ROSLog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OLD_PROJECTOR_SPEC = False

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension, ideally do more """
        path = Path(path)
        valid = path.suffix == '.yaml' and 'projector_bar_specifications' in path.name
        #y = YAML()
        #y.load(path)

        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        if not self.isvalid(path):
            self.OLD_PROJECTOR_SPEC = True
            return
    
        y = YAML()
        info = y.load(path)
        self.OLD_PROJECTOR_SPEC = not ('start_bar_in_front' in info.keys())

class ProjectorInterpreter(
    ConfigFileParamsMixin,
    GitValidatedMixin,
    ROSInterpreter
    ):
    """ ROS interpreter for the ROSFicTrac node"""

    LOG_TAG = '.yaml'
    LOG_TYPE = ProjectorLog

    git_config = [
        GitConfig(
            branch = 'set_parameters_executable',
            commit_time = '2023-01-06 14:28:51-05:00',
            package = 'projector_driver',
            repo_name = 'projector_driver',
            executable = 'projector_bar',
        ),
        GitConfig(
            branch = 'set_parameters_executable',
            commit_time = '2023-01-06 14:28:51-05:00',
            package = 'dlpc_projector_settings',
            repo_name = 'projector_driver',
            executable = 'dlpc_projector_settings',
        ),
    ]

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        self.exp_params = None #TODO implement this so that coordinate transforms
        # can be done appropriately
        super().__init__(file_path)

    @property
    def OLD_PROJECTOR_SPEC(self)->bool:
        self.log : ProjectorLog
        if hasattr(self.log, 'OLD_PROJECTOR_SPEC'):
            return self.log.OLD_PROJECTOR_SPEC
        else:
            return True
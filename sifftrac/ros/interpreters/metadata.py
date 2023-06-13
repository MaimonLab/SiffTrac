from pathlib import Path
from typing import TYPE_CHECKING
import json


from .ros_interpreter import ROSInterpreter, ROSLog

if TYPE_CHECKING:
    from ...utils.types import PathLike

class MetadataLog(ROSLog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.OLD_PROJECTOR_SPEC = False

    @classmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Checks extension, ideally do more """
        path = Path(path)
        valid = (path.suffix == '.json') and ('metadata' in path.name)
        #y = YAML()
        #y.load(path)

        return valid

    def open(self, path : 'PathLike'):
        path = Path(path)
        with open(path) as json_file:
            self._metadata = json.load(json_file)    

class MetadataInterpreter(
    ROSInterpreter
    ):
    """ ROS interpreter for the metadata file"""

    LOG_TAG = '.json'
    LOG_TYPE = MetadataLog

    def __init__(
            self,
            file_path : 'PathLike',
        ):
        super().__init__(file_path)

    @property
    def metadata(self)->dict: 
        """ Returns the metadata dictionary """
        return self.log._metadata
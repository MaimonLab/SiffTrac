"""
The ROS interpreter object is a class for interpreting the various log
files for each type of ROS node. The idea is:

Each type of node logs data its own way, usually with characteristic
log file names, types, locations, etc. 
"""

from typing import TYPE_CHECKING, Type
from pathlib import Path
from abc import ABC, abstractmethod, abstractclassmethod
import logging

if TYPE_CHECKING:
    from ...utils.types import PathLike

class ROSLog(ABC):

    def __init__(self, path : 'PathLike'):
        path = Path(path)
        self.path : Path = path
        self.open(path)

    @classmethod
    @abstractmethod
    def isvalid(cls, path : 'PathLike')->bool:
        """ Returns whether a path points to a valid log file."""
        return False

    @abstractmethod
    def open(self, path : 'PathLike'):
        pass

class ROSInterpreter(ABC):
    """
    The ROSInterpreter class is a class for interpreting the various log
    files for each type of ROS node.
    """
    LOG_TYPE : Type[ROSLog]
    LOG_TAG : str # file suffix

    def __init__(self, file_path : 'PathLike'):
        """
        The constructor for the ROSInterpreter class.

        Parameters
        ----------
        file : str
            The path to the log file to be interpreted.
        """
        #self.file_path = file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not (
                (self.__class__.LOG_TAG is None) or
                (file_path.suffix == self.__class__.LOG_TAG)
            ):
            raise ValueError(f"""
                File {file_path} does not have the correct extension
                for {self.__class__.__name__} log files.
            """)
        if not (file_path.exists()):
            raise ValueError(
                f"""File {file_path} does not exist."""
            )
        
        self.file_path : Path = file_path
        self.log = self.open(self.file_path)

    @classmethod
    def open(cls, file_path : 'PathLike')->ROSLog:
        """
        The open method returns a ROSLog object,
        which confirms that the file is of the correct type
        and provides access to the relevant attributes
        """
        file_path = Path(file_path)
        return cls.LOG_TYPE(file_path)
    
    @classmethod
    def isvalid(cls, file_path : 'PathLike', report_failure : bool = True)->bool:
        """
        The isvalid method returns whether a file is of the correct type.
        """
        file_path = Path(file_path)
        try:
            return cls.LOG_TYPE.isvalid(file_path)
        except Exception as e:
            if report_failure:
                logging.warning(f"""
                Failed to validate file {file_path} as a {cls.LOG_TYPE.__name__} log
                due to error: {e.with_traceback(e.__traceback__)}
                """
                )
            return False

        
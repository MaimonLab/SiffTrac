"""
A class which parses a configuration file, discerns
which types of interpreters are needed, instantiates them,
and lets them find their appropriate logs
"""
from pathlib import Path
from typing import TYPE_CHECKING, Type, Optional
import inspect

import numpy as np

from . import interpreters
from .interpreters.ros_interpreter import ROSInterpreter
from .interpreters import (
    VRPositionInterpreter, FicTracInterpreter, WarnerTemperatureInterpreter,
    ProjectorInterpreter, EventsInterpreter,
)
from .interpreters.mixins.timepoints_mixins import HasTimepoints


if TYPE_CHECKING:
    from ..utils.types import PathLike


INTERPRETERS : list[Type[ROSInterpreter]]= [
    cls
    for name, cls in
    inspect.getmembers(
        interpreters,
        lambda x: issubclass(x, ROSInterpreter) if inspect.isclass(x) else False
    )
]

class Experiment():
    """
    A class which parses an experiment folder and discerns
    1) which types of interpreters are needed for the data therein
    and 2) links variables up that should influence one another (e.g.
    projector configuration files with the VR Position).
    """

    def __init__(self, path : 'PathLike'):
        path = Path(path)
        # probe whether any of the interpreters are valid
        # for any files in this path
        files_in_path = list(path.glob("*") if path.is_dir() else path.parent.glob("**/*"))
        self.interpreters = []
        for interpreter_class in INTERPRETERS:
            for file in files_in_path:
                if (not file.is_dir()) and interpreter_class.isvalid(file):
                    self.interpreters.append(interpreter_class(file))
    
        if (self.vr_position != None) and (self.projector != None):
            self.vr_position.bar_in_front_angle = self.projector.bar_front_angle

    @property
    def vr_position(self)->Optional['VRPositionInterpreter']:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, VRPositionInterpreter)),
            None
        )

    @property
    def fulltrac(self)->Optional['FicTracInterpreter']:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, FicTracInterpreter)),
            None
        )
    
    @property
    def warner_temperature(self)->Optional['WarnerTemperatureInterpreter']:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, WarnerTemperatureInterpreter)),
            None
        )
    
    @property
    def events(self)->Optional['EventsInterpreter']:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, EventsInterpreter)),
            None
        )
    
    @property
    def projector(self)->Optional['ProjectorInterpreter']:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, ProjectorInterpreter)),
            None
        )

    @property
    def start_timestamp(self)->int:
        """ Nanoseconds """
        return 0
    
    @property
    def end_timestamp(self)->int:
        """ Nanoseconds """
        return 0
    
    @classmethod
    def probe_start_and_end_timestamps(cls, path : 'PathLike')->tuple[int, int]:
        """
        Checks a path for a set of data files corresponding to an experiment
        and estimates its start and end timestamps in nanoseconds without
        opening and initializing all the files.
        """
        path = Path(path)

        files_in_path = list(path.glob("*") if path.is_dir() else path.parent.glob("**/*"))
        earliest_start, latest_end = 0, np.inf
        for interpreter_class in INTERPRETERS:
            for file in files_in_path:
                if (
                    (not file.is_dir())
                    and interpreter_class.isvalid(file)
                    and issubclass(interpreter_class, HasTimepoints)
                ):
                    start, end = interpreter_class.probe_start_and_end_timestamps(file)
                    earliest_start = max(earliest_start, start)
                    latest_end = min(latest_end, end)

        return(earliest_start, int(latest_end))

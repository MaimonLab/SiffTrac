"""
A class which parses a configuration file, discerns
which types of interpreters are needed, instantiates them,
and lets them find their appropriate logs
"""
from pathlib import Path
from typing import TYPE_CHECKING, Type
import inspect

import numpy as np

from . import interpreters
from .interpreters.ros_interpreter import ROSInterpreter
from .interpreters import (
    VRPositionInterpreter, FicTracInterpreter, WarnerTemperatureInterpreter,
    ProjectorInterpreter, EventsInterpreter,
)
from .interpreters.mixins.timepoints_mixins import HasStartAndEndpoints


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
    
    @property
    def vr_position(self)->'VRPositionInterpreter':
        return next(
            interpreter for interpreter in self.interpreters
            if isinstance(interpreter, VRPositionInterpreter)
        )

    @property
    def fulltrac(self)->'FicTracInterpreter':
        return next(
            interpreter for interpreter in self.interpreters
            if isinstance(interpreter, FicTracInterpreter)
        )
    
    @property
    def warner_temperature(self)->'WarnerTemperatureInterpreter':
        return next(
            interpreter for interpreter in self.interpreters
            if isinstance(interpreter, WarnerTemperatureInterpreter)
        )
    
    @property
    def events(self)->'EventsInterpreter':
        return next(
            interpreter for interpreter in self.interpreters
            if isinstance(interpreter, EventsInterpreter)
        )
    
    @property
    def projector(self)->'ProjectorInterpreter':
        return next(
            interpreter for interpreter in self.interpreters
            if isinstance(interpreter, ProjectorInterpreter)
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
                    and issubclass(interpreter_class, HasStartAndEndpoints)
                ):
                    start, end = interpreter_class.probe_start_and_end_timestamps(file)
                    earliest_start = max(earliest_start, start)
                    latest_end = min(latest_end, end)

        return(earliest_start, latest_end)

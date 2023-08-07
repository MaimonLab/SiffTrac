"""
A class which parses a configuration file, discerns
which types of interpreters are needed, instantiates them,
and lets them find their appropriate logs
"""
from pathlib import Path
from typing import TYPE_CHECKING, Type, Optional
import inspect

import numpy as np
import ruamel.yaml as yaml

from . import interpreters
from .interpreters.ros_interpreter import ROSInterpreter
from .interpreters import (
    VRPositionInterpreter, FicTracInterpreter, WarnerTemperatureInterpreter,
    ProjectorInterpreter, EventsInterpreter, MetadataInterpreter,
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
        files_in_path = list(path.rglob("*") if path.is_dir() else path.parent.rglob("*"))
        self.interpreters = []
        for file in files_in_path:
            pass
        for interpreter_class in INTERPRETERS:
            for file in files_in_path:
                if (
                    (not file.is_dir())
                    and interpreter_class.isvalid(file)
                    and (not '._' in file.name) # this annoying fucking macos thing
                ):
                    self.interpreters.append(interpreter_class(file))
    
        if (self.vr_position != None) and (self.projector != None):
            self.vr_position.bar_in_front_angle = self.projector.bar_front_angle
            self.vr_position.set_projector_config(self.projector.experiment_config)

    #@property
    #def bringup_config_(self)->dict:


    @property
    def genotype(self)->str:
        return next(
            (
                interpreter for interpreter in self.interpreters
                if isinstance(interpreter, MetadataInterpreter)
            )
        ).metadata['genotype']
    
    @property
    def notes(self)->str:
        return next(
            (
                interpreter for interpreter in self.interpreters
                if isinstance(interpreter, MetadataInterpreter)
            )
        ).metadata['notes']

    @property
    def vr_position(self)->Optional[VRPositionInterpreter]:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, VRPositionInterpreter)),
            None
        )

    @property
    def fulltrac(self)->Optional[FicTracInterpreter]:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, FicTracInterpreter)),
            None
        )
    
    @property
    def warner_temperature(self)->Optional[WarnerTemperatureInterpreter]:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, WarnerTemperatureInterpreter)),
            None
        )
    
    @property
    def events(self)->Optional[EventsInterpreter]:
        return next(
            (interpreter for interpreter in self.interpreters
            if isinstance(interpreter, EventsInterpreter)),
            None
        )
    
    @property
    def projector(self)->Optional[ProjectorInterpreter]:
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
    
    @staticmethod
    def probe_start_and_end_timestamps(path : 'PathLike', suppress_warnings : bool = True)->tuple[int, int]:
        """
        Checks a path for a set of data files corresponding to an experiment
        and estimates its start and end timestamps in nanoseconds without
        opening and initializing all the files.

        path : PathLike
            The path to the experiment folder or a file within it.

        suppress_warnings : bool
            Whether to suppress warnings about files that are not interpretable.
            You basically always want this to be true -- for example, MacOS
            creates a bunch of hidden files that are not interpretable and spam
            your terminal with warnings if you don't suppress them.
        """
        path = Path(path)

        files_in_path = list(path.glob("*") if path.is_dir() else path.parent.glob("*"))
        earliest_start, latest_end = np.nan, np.nan
        for interpreter_class in INTERPRETERS:
            for file in files_in_path:
                try:
                    if (
                        (not file.is_dir())
                        and issubclass(interpreter_class, HasTimepoints)
                        and interpreter_class.isvalid(file)
                        and ('._' not in file.name)
                    ):
                        start, end = interpreter_class.probe_start_and_end_timestamps(file)
                        earliest_start = min(start, earliest_start)
                        latest_end = max(end, latest_end)
                except Exception as e:
                    if not suppress_warnings:
                        print(f"Error probing {file} for timestamps: {e}")
                    continue

        return (earliest_start, latest_end)

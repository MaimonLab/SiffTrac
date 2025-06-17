"""
A class which parses a configuration file, discerns
which types of interpreters are needed, instantiates them,
and lets them find their appropriate logs. Automatically works
as long as the interpreters are imported in the `interpreters` module.
"""
from pathlib import Path
from typing import TYPE_CHECKING, Type, Optional, List, Tuple, TypeVar
import inspect

import numpy as np
from ruamel.yaml import YAML

from . import interpreters
from .interpreters.ros_interpreter import ROSInterpreter
from .interpreters import (
    VRPositionInterpreter, FicTracInterpreter, WarnerTemperatureInterpreter,
    ProjectorInterpreter, EventsInterpreter, MetadataInterpreter,
    LightSugarInterpreter, PicoPumpInterpreter
)
from .interpreters.mixins.timepoints_mixins import HasTimepoints


if TYPE_CHECKING:
    from ..utils.types import PathLike

RosT = TypeVar("RosT", bound=ROSInterpreter)

INTERPRETERS : List[Type[ROSInterpreter]]= [
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

    TODO: Instead of making properties for each type of `Interpreter`,
    make them document themselves by alias. Worse for linters, better
    for use I think?
    """

    def __init__(self, path : 'PathLike'):
        path = Path(path)
        self.main_path = path
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
                    and ('._' not in file.name) # this annoying fucking macos thing
                ):
                    self.interpreters.append(interpreter_class(file))
    
        if (self.vr_position is not None) and (self.projector is not None):
            self.vr_position.bar_in_front_angle = self.projector.bar_front_angle
            self.vr_position.set_projector_config(self.projector.experiment_config)

    def get_interpreter_type(self, cls : type[RosT])->Optional[RosT]:
        """ Returns interpreter of type cls, if any exists """
        return next(
            (
                interpreter for interpreter in self.interpreters
                if isinstance(interpreter, cls)
            ),
            None,
        )
    
    def correct_all_bar_jumps(self):
        """
        Iterates through all events containing `JumpOffsetDegrees` in their
        `Event type` and adjusts the position-type attributes in the 
        `VRPositionInterpreter` to accurately track the position after the bar
        jump.

        ## Example

        ```python
            exp = Experiment('path/to/experiment')
            exp.correct_all_bar_jumps()
        ```
        """
        if self.events is None:
            return
        for _, x in self.events.df.iterrows():
            if x['Event type'] == 'JumpOffsetDegrees':
                offset = float(x['Event message'].split('Offset bar by ')[-1])
                self.vr_position.correct_position_for_bar_jump(
                    x['timestamp'], offset
                )

    def minimize_sideslip(self, fictrac_only : bool = True, lock_heading : bool = True):
        """
        Minimizes the sideslip from the `FullTrac` data and then applies
        the resulting rotation to the `VRPositionInterpreter` if it exists.

        ## Arguments
        * `fictrac_only : bool`
            If True, only minimizes the sideslip in the `FullTrac` interpreter
            and does not apply the rotation to the `VRPositionInterpreter` or
            any other interpreters to which it might apply. If the VR is a true
            2D environment, this should be set to `True`, or else the positions
            of objects in the environment will be altered in analyses (at least
            as implemented for now).

        * `lock_heading : bool`
            If True, the heading will not be adjusted, only the position.
        
        ## Example
        ```python
            exp = Experiment('path/to/experiment')
            exp.minimize_sideslip()
        ```
        """
        if self.fulltrac is None:
            raise ValueError("No FullTrac interpreter found in this experiment.")
        
        first_event_timestamp = self.events.df['timestamp'].min() if self.events else 0

        fulltrac_min_r = self.fulltrac.minimize_sideslip(
            lock_heading=lock_heading,
            starting_idx = np.where(self.fulltrac.timestamps >= first_event_timestamp)[0][0] if self.events else 0
        )
        
        if fictrac_only:
            return
        
        if self.vr_position is not None:
            self.vr_position.rotate_axes(fulltrac_min_r)

    @property
    def config(self)->Optional[YAML]:
        if self.main_path.glob('*_config.yaml'):
            return YAML().load(next(self.main_path.glob('*_config.yaml')))


    @property
    def genotype(self)->str:
        return self.get_interpreter_type(MetadataInterpreter).metadata['genotype']
    
    @property
    def notes(self)->str:
        return self.get_interpreter_type(MetadataInterpreter).metadata['notes']

    @property
    def vr_position(self)->Optional[VRPositionInterpreter]:
        return self.get_interpreter_type(VRPositionInterpreter)
    
    @property
    def fulltrac(self)->Optional[FicTracInterpreter]:
        """ Returns the first FicTracInterpreter class it finds,
        if any """
        return self.get_interpreter_type(FicTracInterpreter)
    
    @property
    def warner_temperature(self)->Optional[WarnerTemperatureInterpreter]:
        """ Returns the first WarnerTemperatureInterpreter class it finds,
        if any """
        return self.get_interpreter_type(WarnerTemperatureInterpreter)
    
    @property
    def events(self)->Optional[EventsInterpreter]:
        """ Returns the first EventsInterpreter class it finds,
        if any """
        return self.get_interpreter_type(EventsInterpreter)
    
    @property
    def projector(self)->Optional[ProjectorInterpreter]:
        """ Returns the first ProjectorInterpreter class it finds,
        if any """
        return self.get_interpreter_type(ProjectorInterpreter)
    
    @property
    def light_sugar(self)->Optional[LightSugarInterpreter]:
        """ Returns the first LightSugarInterpreter class it finds,
        if any """
        return self.get_interpreter_type(LightSugarInterpreter)
    
    @property
    def picopumps(self)->List[PicoPumpInterpreter]:
        """ Returns all the PicoPumpInterpreter classes it finds """
        return [
            interpreter
            for interpreter in self.interpreters
            if isinstance(interpreter, PicoPumpInterpreter)
        ]
    # @property
    # def start_timestamp(self)->int:
    #     """ Nanoseconds """
    #     return 0
    
    # @property
    # def end_timestamp(self)->int:
    #     """ Nanoseconds """
    #     return 0
    
    @staticmethod
    def probe_start_and_end_timestamps(path : 'PathLike', suppress_warnings : bool = True)->Tuple[int, int]:
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

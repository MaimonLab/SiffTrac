from typing import Optional, Union
from pathlib import Path
import warnings

import numpy as np

from .experiment import Experiment
from . import interpreters
from ..utils.types import PathLike

def minimize_sideslip(exp : Experiment):
    """
    Minimizes the sideslip using a `FullTrac` interpreter
    then corrects all trajectories in the experiment accordingly.
    """
    fulltrac_min_r = exp.fulltrac.minimize_sideslip()
    raise NotImplementedError(
        "This function is not implemented yet. "
        "Please use the `FullTrac` interpreter directly to minimize sideslip."
    )

def find_experiment_containing_timestamp(
        path : 'PathLike',
        timestamp : int,
        pattern : Optional[str] = None
    )->Experiment:
    """
    Finds the experiment containing the given timestamp.

    If `pattern` is specified, it will be used to filter the
    possible experiment directories. Otherwise, all directories
    containing at least one file will be considered.
    """
    path = Path(path)
    path = path if path.is_dir() else path.parent
    possible_superdirs = []

    pattern = '*' if pattern is None else pattern
    # Retrieves all directories that contain at least one file
    # directly that bookends the requested timestamp

    # Retrieves all directories that contain at least one file
    # directly that bookends the requested timestamp

    for experiment_path in path.rglob(pattern):
        start, end = Experiment.probe_start_and_end_timestamps(experiment_path)
        if start <= timestamp <= end:
            possible_superdirs.append(experiment_path)

    # find highest level directory of those
    if len(possible_superdirs) > 0:
        possible_superdirs.sort()
        return Experiment(possible_superdirs[0])
    else:
        raise ValueError(f"No experiment found containing timestamp {timestamp}.")
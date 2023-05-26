from typing import TYPE_CHECKING
from pathlib import Path

from .experiment import Experiment
from . import interpreters

if TYPE_CHECKING:
    from ..utils.types import PathLike

def find_experiment_containing_timestamp(
        path : 'PathLike',
        timestamp : int
    )->Experiment:
    """
    Finds the experiment containing the given timestamp.
    """
    path = Path(path)
    path = path if path.is_dir() else path.parent
    possible_superdirs = []
    # Retrieves all directories that contain at least one file
    # directly that bookends the requested timestamp
    for experiment_path in path.rglob('*'):
        start, end = Experiment.probe_start_and_end_timestamps(experiment_path)
        if start <= timestamp <= end:
            possible_superdirs.append(experiment_path)

    # find highest level directory of those
    if len(possible_superdirs) > 0:
        possible_superdirs.sort()
        return Experiment(possible_superdirs[0])
    else:
        raise ValueError(f"No experiment found containing timestamp {timestamp}.")
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
    for experiment_path in path.rglob('*'):
        start, end = Experiment.probe_start_and_end_timestamps(experiment_path)
        if start <= timestamp <= end:
            return Experiment(experiment_path)
    raise ValueError(f"No experiment found containing timestamp {timestamp}.")
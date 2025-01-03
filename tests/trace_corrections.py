"""
These tests are to demonstrate that the methods for
correcting a bar jump (or changing gain) to maintain
a consistent coordinate frame in virtual reality are
correct. Takes a simulated trajectory and manually rotates
the frame of reference at various time points. Then compares
that output to the correction tools' outputs.
"""
from typing import Any, Tuple
import numpy as np

def generate_simulated_trajectory(
        mean_v : np.ndarray[Any,np.dtype[complex]],
        mean_dtheta : np.ndarray[Any,np.dtype[float]],
        n_steps : int = 100000
    ) -> Tuple[np.ndarray[Any,np.dtype[complex]], np.ndarray[Any,np.dtype[float]]]:
    """
    Generate a non-rotated simulated trajectory.

    ## Parameters

    - ```mean_v : np.ndarray[Any,np.dtype[complex]]```
        The mean velocity of the simulated trajectory. The real part
        is the mean sideslip, and the imaginary part is the mean forward
        speed.

    - ```mean_dtheta : np.ndarray[Any,np.dtype[float]]```
        The mean angular velocity of the simulated trajectory in
        radians per unit time

    ## Returns

    ```
    (trajectory, heading) : Tuple[
        np.ndarray[Any,np.dtype[complex]],
        np.ndarray[Any,np.dtype[float]]
    ]
    ```
    """

    # Generate the velocities
    df = np.random.exponential(mean_v.imag, n_steps)
    ds = np.random.exponential(mean_v.real, n_steps)

    # Generate the dthetas
    dtheta = np.random.exponential(mean_dtheta, n_steps)

    theta = np.cumsum(dtheta)

    # Generate the trajectory
    trajectory = np.cumsum((ds + 1j*df)*np.exp(1j*theta))

    return trajectory, theta


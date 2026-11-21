"""Stationary block bootstrap (Politis & Romano 1994), task E-7.

Blocks start at a uniform random row and have geometric lengths with mean ``mean_block``;
indices wrap around the end of the sample. Rows of a 2-D input are resampled together, so
paired series (e.g. two strategies' returns) keep their cross-correlation. Seeds go through
``numpy.random.SeedSequence`` so a fixed seed gives identical draws.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

Statistic = Callable[[npt.NDArray[np.float64]], float | np.floating]


def stationary_indices(n: int, mean_block: float, rng: np.random.Generator) -> npt.NDArray[np.intp]:
    """One bootstrap sample of ``n`` row indices."""
    if mean_block < 1.0:
        raise ValueError("mean_block must be >= 1")
    new_block = rng.random(n) < 1.0 / mean_block
    new_block[0] = True
    starts = rng.integers(0, n, size=n)
    block_id = np.cumsum(new_block) - 1
    first_row = np.flatnonzero(new_block)
    offset = np.arange(n) - first_row[block_id]
    idx: npt.NDArray[np.intp] = (starts[first_row][block_id] + offset) % n
    return idx


def stationary_bootstrap(
    x: npt.ArrayLike,
    stat: Statistic,
    *,
    n_boot: int = 1000,
    mean_block: float = 20.0,
    seed: int | np.random.SeedSequence = 0,
) -> npt.NDArray[np.float64]:
    """``n_boot`` values of ``stat`` on stationary-bootstrap resamples of the rows of ``x``."""
    data = np.asarray(x, dtype=np.float64)
    ss = seed if isinstance(seed, np.random.SeedSequence) else np.random.SeedSequence(seed)
    rng = np.random.default_rng(ss)
    n = data.shape[0]
    return np.array(
        [float(stat(data[stationary_indices(n, mean_block, rng)])) for _ in range(n_boot)]
    )


def confidence_interval(
    x: npt.ArrayLike,
    stat: Statistic,
    *,
    level: float = 0.9,
    n_boot: int = 1000,
    mean_block: float = 20.0,
    seed: int | np.random.SeedSequence = 0,
) -> tuple[float, float]:
    """Percentile interval of ``stat`` at ``level`` (0.9 = 5th to 95th percentile)."""
    draws = stationary_bootstrap(x, stat, n_boot=n_boot, mean_block=mean_block, seed=seed)
    tail = (1.0 - level) / 2.0
    lo, hi = np.quantile(draws, [tail, 1.0 - tail])
    return float(lo), float(hi)

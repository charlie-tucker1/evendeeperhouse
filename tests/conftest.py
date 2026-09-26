"""Shared fixtures."""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(scope="session")
def sr() -> int:
    return 44100


def to_mono(y: np.ndarray) -> np.ndarray:
    return y.mean(axis=1) if y.ndim == 2 else y

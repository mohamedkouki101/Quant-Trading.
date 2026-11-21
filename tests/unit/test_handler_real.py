"""E-2 on real data: the vault hides the locked test period (no strategy is run here)."""

import pandas as pd
import pytest

from momlab.data.handler import DataHandler

pytestmark = pytest.mark.data


def test_real_handler_is_vaulted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOMLAB_UNLOCK_TEST", raising=False)
    dh = DataHandler.from_processed("vw", fields=("n_firms", "avg_size"))
    assert len(dh.assets) == 49
    assert dh.dates[0] == pd.Timestamp("1926-07-01")
    assert dh.dates[-1] < pd.Timestamp("2006-01-01")
    assert dh.dates[-1] == pd.Timestamp("2005-12-30")  # last trading day of 2005

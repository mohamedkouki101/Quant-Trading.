"""E-0: RunConfig validation, YAML merge and config hash."""

import hashlib
import json
from pathlib import Path

import pydantic
import pytest

from momlab import config as cfg

ROOT = Path(__file__).resolve().parents[2]


def test_base_yaml_has_preregistered_defaults() -> None:
    c = cfg.load_config(ROOT / "configs" / "base.yaml")
    assert c.lookback_months == 12
    assert c.skip_months == 1
    assert c.holding_months == 1
    assert c.n_per_leg == 10
    assert c.vol_target == 0.10
    assert c.vol_window == 126
    assert c.leverage_cap == 2.0
    assert c.fill_lag == 1
    assert c.cost.model == "flat"
    assert c.cost.bps == 10.0
    assert c.weighting == "vw"
    assert str(c.start) == "1926-07-01" and str(c.end) == "2005-12-31"


def test_fill_lag_zero_raises() -> None:
    with pytest.raises(pydantic.ValidationError, match="fill_lag"):
        cfg.RunConfig(fill_lag=0)


def test_other_validation() -> None:
    with pytest.raises(pydantic.ValidationError):
        cfg.RunConfig(unknown_field=1)  # type: ignore[call-arg]
    with pytest.raises(pydantic.ValidationError):
        cfg.RunConfig(cost={"model": "flat", "bps": -1.0})
    with pytest.raises(pydantic.ValidationError, match="end"):
        cfg.RunConfig(start="2000-01-01", end="1999-01-01")
    with pytest.raises(pydantic.ValidationError):
        cfg.RunConfig(signal_sign=0)


def test_hash_is_sha256_of_canonical_json() -> None:
    c = cfg.RunConfig()
    canonical = json.dumps(c.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    assert c.config_hash() == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert cfg.RunConfig().config_hash() == c.config_hash()  # same config, same hash


def test_yaml_key_order_does_not_change_hash(tmp_path: Path) -> None:
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text("strategy: b3\nn_per_leg: 7\ncost:\n  model: flat\n  bps: 5\n", encoding="utf-8")
    b.write_text("cost:\n  bps: 5\n  model: flat\nn_per_leg: 7\nstrategy: b3\n", encoding="utf-8")
    assert cfg.load_config(a).config_hash() == cfg.load_config(b).config_hash()
    assert cfg.load_config(a).config_hash() != cfg.RunConfig().config_hash()


def test_strategy_yaml_merges_over_base(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    strat = tmp_path / "s.yaml"
    base.write_text("n_per_leg: 10\ncost:\n  model: flat\n  bps: 10\n", encoding="utf-8")
    strat.write_text("strategy: b4\ncost:\n  bps: 25\n", encoding="utf-8")
    c = cfg.load_config(base, strat)
    assert c.strategy == "b4"
    assert c.n_per_leg == 10
    assert c.cost.model == "flat" and c.cost.bps == 25.0  # nested dicts merge key by key


def test_strategy_files_load() -> None:
    for path in sorted((ROOT / "configs" / "strategies").glob("*.yaml")):
        c = cfg.load_config(ROOT / "configs" / "base.yaml", path)
        assert c.strategy in {"b1", "b3", "b4", "b5"}


def test_yaml_must_be_a_mapping(tmp_path: Path) -> None:
    p = tmp_path / "x.yaml"
    p.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        cfg.load_config(p)

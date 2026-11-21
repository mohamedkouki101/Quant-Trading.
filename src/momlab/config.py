"""Run configuration (task E-0): pydantic models, YAML loading and the config hash.

A run is described by ``configs/base.yaml`` (the pre-registered defaults, PREREGISTRATION.md
§4) merged with one strategy YAML. ``config_hash`` is the sha256 of the canonical JSON of the
validated model (sorted keys, no whitespace), so key order in YAML never changes it.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CostConfig(BaseModel):
    """Cost model settings. All costs in basis points (1 bp = 0.0001)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: Literal["flat", "spread_impact_borrow"] = "flat"
    #: Flat one-way cost per unit of traded weight (``FlatBps``).
    bps: float = Field(default=10.0, ge=0.0)
    #: ``SpreadImpactBorrow``: half-spread (same for all assets here), commission, annual
    #: borrow fee on short notional, impact coefficient k and AUM in dollars.
    half_spread_bps: float = Field(default=0.0, ge=0.0)
    commission_bps: float = Field(default=0.0, ge=0.0)
    borrow_bps_annual: float = Field(default=0.0, ge=0.0)
    impact_k: float = Field(default=0.0, ge=0.0)
    aum: float = Field(default=0.0, ge=0.0)


class RunConfig(BaseModel):
    """Everything that defines one backtest run. Weights are fractions of NAV; vol in
    annualised decimals (0.10 = 10%)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: Literal["b1", "b3", "b4", "b5"] = "b3"
    universe: Literal["kf49"] = "kf49"
    weighting: Literal["vw", "ew"] = "vw"
    start: dt.date = dt.date(1926, 7, 1)
    end: dt.date = dt.date(2005, 12, 31)
    rebalance: Literal["month_end"] = "month_end"
    lookback_months: int = Field(default=12, ge=1)
    skip_months: int = Field(default=1, ge=0)
    holding_months: int = Field(default=1, ge=1)
    n_per_leg: int = Field(default=10, ge=1)
    #: B5 only: +1 buys recent winners (continuation), -1 buys recent losers (reversal).
    signal_sign: Literal[-1, 1] = 1
    vol_target: float = Field(default=0.10, gt=0.0)
    vol_window: int = Field(default=126, ge=2)
    leverage_cap: float = Field(default=2.0, gt=0.0)
    gross_cap: float | None = Field(default=None, gt=0.0)
    net_cap: float | None = Field(default=None, gt=0.0)
    position_cap: float | None = Field(default=None, gt=0.0)
    cost: CostConfig = CostConfig()
    fill_lag: int = 1
    seed: int = 7

    @field_validator("fill_lag")
    @classmethod
    def _fill_lag_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError(
                "fill_lag must be >= 1 (a fill at the signal's own close is look-ahead)"
            )
        return v

    @model_validator(mode="after")
    def _dates_ordered(self) -> RunConfig:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self

    def canonical_json(self) -> str:
        """Canonical JSON: sorted keys, no whitespace."""
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def config_hash(self) -> str:
        """sha256 hex digest of :meth:`canonical_json`."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def load_config(*paths: Path) -> RunConfig:
    """Merge YAML files left to right (later files win, nested mappings merge key by key) and
    validate the result."""
    merged: dict[str, Any] = {}
    for p in paths:
        merged = _deep_merge(merged, _read_yaml(Path(p)))
    return RunConfig.model_validate(merged)

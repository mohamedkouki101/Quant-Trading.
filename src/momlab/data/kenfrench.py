"""Ken French data library: downloader (task D-1) and parser (task D-2).

Data is Copyright Eugene F. Fama and Kenneth R. French. It is downloaded by code into
``data/raw/`` (gitignored) and never committed. ``data/manifest.json`` (committed) records the
URL, download time (UTC), sha256 and size of every raw file, so results can cite the vintage.

CLI: ``python -m momlab.data.kenfrench download [--force]``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import pandas as pd
import requests

from momlab import paths, periods
from momlab.data import clean

BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

KF_FILES: tuple[str, ...] = (
    "49_Industry_Portfolios_CSV.zip",
    "49_Industry_Portfolios_daily_CSV.zip",
    "F-F_Research_Data_Factors_CSV.zip",
    "F-F_Research_Data_Factors_daily_CSV.zip",
    "F-F_Momentum_Factor_CSV.zip",
    "F-F_Momentum_Factor_daily_CSV.zip",
    "F-F_ST_Reversal_Factor_CSV.zip",
    "F-F_ST_Reversal_Factor_daily_CSV.zip",
)

#: (connect, read) timeouts in seconds.
TIMEOUT: tuple[float, float] = (10.0, 120.0)
#: Attempts per file: the first try plus one retry.
ATTEMPTS = 2


class DownloadError(RuntimeError):
    """A file could not be downloaded after all attempts."""


class _Response(Protocol):
    @property
    def content(self) -> bytes: ...
    @property
    def status_code(self) -> int: ...

    def raise_for_status(self) -> None: ...


Getter = Callable[..., _Response]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_manifest(path: Path) -> dict[str, Any]:
    """Return the manifest as a dict (empty sections if the file does not exist)."""
    if path.exists():
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    return {}


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    """Write the manifest deterministically (sorted keys, 2-space indent, LF, trailing newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _fetch(url: str, get: Getter) -> bytes:
    """Download ``url`` with one retry; reject anything that is not a zip archive."""
    errors: list[str] = []
    for _ in range(ATTEMPTS):
        try:
            resp = get(url, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        if not zipfile.is_zipfile(io.BytesIO(resp.content)):
            errors.append("response is not a zip archive")
            continue
        return resp.content
    if errors and all(e == "response is not a zip archive" for e in errors):
        raise DownloadError(f"{url}: not a zip archive (the server returned something else)")
    raise DownloadError(
        f"could not download {url} after {ATTEMPTS} attempts; the Ken French site may be down "
        f"or unreachable. Errors: {'; '.join(errors)}"
    )


def download_all(
    raw_dir: Path = paths.RAW_DIR,
    manifest_path: Path = paths.MANIFEST,
    *,
    force: bool = False,
    files: Sequence[str] = KF_FILES,
    get: Getter = requests.get,
) -> dict[str, Any]:
    """Download the Ken French zips into ``raw_dir`` and record them in the manifest.

    A file is skipped when it exists on disk and its sha256 equals the manifest entry, so a
    second run changes nothing. ``force=True`` downloads again; the old entry is kept under
    ``previous_vintages`` when the content changed. Returns the ``raw`` manifest section.
    """
    manifest = read_manifest(manifest_path)
    raw: dict[str, Any] = manifest.setdefault("raw", {})
    raw_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    for name in files:
        dest = raw_dir / name
        entry = raw.get(name)
        if (
            not force
            and entry is not None
            and dest.exists()
            and _sha256(dest.read_bytes()) == entry["sha256"]
        ):
            continue
        url = BASE_URL + name
        content = _fetch(url, get)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(content)
        tmp.replace(dest)
        new: dict[str, Any] = {
            "url": url,
            "download_ts": _utc_now(),
            "sha256": _sha256(content),
            "bytes": len(content),
        }
        history: list[dict[str, Any]] = list(entry.get("previous_vintages", [])) if entry else []
        if entry is not None and entry["sha256"] != new["sha256"]:
            history.append({k: entry[k] for k in ("download_ts", "sha256", "bytes")})
        if history:
            new["previous_vintages"] = history
        raw[name] = new
        changed = True
        write_manifest(manifest_path, manifest)  # after every file, so a later failure keeps it
        print(f"downloaded {name}: {len(content):,} bytes, sha256 {new['sha256'][:12]}")
    if changed or not manifest_path.exists():
        write_manifest(manifest_path, manifest)
    return raw


# ---------------------------------------------------------------------------------------------
# Parsing (task D-2)
# ---------------------------------------------------------------------------------------------

Freq = Literal["D", "M", "A"]
_DATA_RE = re.compile(r"^\s*(\d{4}|\d{6}|\d{8})\s*,")
_FREQ_BY_LEN: dict[int, Freq] = {8: "D", 6: "M", 4: "A"}


class ParseError(ValueError):
    """A Ken French CSV does not have the expected structure."""


@dataclass(frozen=True)
class Block:
    """One table inside a Ken French CSV: its title line, frequency, columns and raw rows."""

    title: str
    freq: Freq
    columns: list[str]
    rows: list[tuple[str, list[str]]]


def split_blocks(text: str) -> list[Block]:
    """Split a Ken French CSV into its blocks.

    A block starts at a header line beginning with a comma (``,Agric,Food ,...``); its title is
    the last non-empty line above that header; its rows are the date-keyed lines below it.
    Column names are stripped of the padding spaces Ken French uses.
    """
    lines = text.splitlines()
    blocks: list[Block] = []
    title = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(","):
            columns = [c.strip() for c in line.split(",")[1:]]
            rows: list[tuple[str, list[str]]] = []
            i += 1
            while i < len(lines) and _DATA_RE.match(lines[i]):
                parts = [p.strip() for p in lines[i].split(",")]
                if len(parts) - 1 != len(columns):
                    raise ParseError(
                        f"block {title!r}: row {parts[0]} has {len(parts) - 1} values, "
                        f"expected {len(columns)} columns"
                    )
                rows.append((parts[0], parts[1:]))
                i += 1
            freq = _FREQ_BY_LEN[len(rows[0][0])] if rows else "A"
            blocks.append(Block(title, freq, columns, rows))
            continue
        if line.strip():
            title = line.strip()
        i += 1
    return blocks


def _parse_dates(codes: list[str], freq: Freq) -> pd.DatetimeIndex:
    """``YYYYMMDD`` to that day; ``YYYYMM`` to the last calendar day of the month."""
    if freq == "D":
        idx = pd.to_datetime(codes, format="%Y%m%d")
    elif freq == "M":
        idx = pd.to_datetime(codes, format="%Y%m") + pd.offsets.MonthEnd(0)
    else:
        raise ParseError("annual blocks are not parsed (not used by the project)")
    return pd.DatetimeIndex(pd.DatetimeIndex(idx).astype("datetime64[ns]"), name="date")


def _to_frame(block: Block, *, percent: bool) -> pd.DataFrame:
    """Wide frame (dates x columns) with missing codes as NaN and percents as decimals."""
    index = _parse_dates([r[0] for r in block.rows], block.freq)
    values = [[float(v) for v in r[1]] for r in block.rows]
    wide = pd.DataFrame(values, index=index, columns=block.columns, dtype="float64")
    out, _ = clean.rule1_missing_codes(wide, percent=percent)
    return out


def read_block(text: str, title: str, *, percent: bool) -> pd.DataFrame:
    """Return the block whose title equals ``title`` as a cleaned wide frame."""
    for block in split_blocks(text):
        if block.title == title:
            return _to_frame(block, percent=percent)
    raise ParseError(f"no block titled {title!r}")


def read_first_block(text: str, *, freq: Literal["D", "M"], percent: bool) -> pd.DataFrame:
    """Return the first block with frequency ``freq`` (factor files have untitled blocks)."""
    for block in split_blocks(text):
        if block.freq == freq:
            return _to_frame(block, percent=percent)
    raise ParseError(f"no block with frequency {freq!r}")


def crsp_vintage(text: str) -> str:
    """The CRSP vintage named in the file header (e.g. ``"202609"``), or ``"unknown"``."""
    m = re.search(r"created (?:by )?using the (\d{6}) CRSP database", text)
    return m.group(1) if m else "unknown"


VW_MONTHLY = "Average Value Weighted Returns -- Monthly"
EW_MONTHLY = "Average Equal Weighted Returns -- Monthly"
VW_DAILY = "Average Value Weighted Returns -- Daily"
EW_DAILY = "Average Equal Weighted Returns -- Daily"
N_FIRMS = "Number of Firms in Portfolios"
AVG_SIZE = "Average Firm Size"

PANEL_COLUMNS = [
    "date",
    "asset",
    "weighting",
    "ret",
    "available_at",
    "n_firms",
    "avg_size",
    "source_vintage",
]


def _check_same_columns(*frames: pd.DataFrame) -> list[str]:
    cols = list(frames[0].columns)
    for f in frames[1:]:
        if list(f.columns) != cols:
            raise ParseError(f"industry columns differ between blocks: {cols} vs {list(f.columns)}")
    return cols


def _long_panel(
    vw: pd.DataFrame,
    ew: pd.DataFrame,
    chars: pd.DataFrame,
    *,
    daily: bool,
    assets: list[str],
    source_vintage: str,
) -> pd.DataFrame:
    """Stack VW and EW wide returns into the long schema of PLAN §5.2 and attach the lagged
    characteristics (``chars``: one row per month-end key and asset)."""
    parts = []
    for name, wide in (("vw", vw), ("ew", ew)):
        long = (
            wide.rename_axis("date")
            .reset_index()
            .melt(id_vars="date", var_name="asset", value_name="ret")
        )
        long["weighting"] = name
        parts.append(long)
    out = pd.concat(parts, ignore_index=True)
    out["key"] = out["date"] + pd.offsets.MonthEnd(0) if daily else out["date"]
    out = out.merge(chars, on=["key", "asset"], how="left", validate="many_to_one")
    out["available_at"] = out["date"]
    out["asset"] = pd.Categorical(out["asset"], categories=assets)
    out["weighting"] = pd.Categorical(out["weighting"], categories=["vw", "ew"])
    out["source_vintage"] = pd.Categorical([source_vintage] * len(out))
    out["n_firms"] = out["n_firms"].round().astype("Int64")
    out = out.sort_values(["date", "weighting", "asset"], kind="stable").reset_index(drop=True)
    return out[PANEL_COLUMNS]


def build_industry_panels(
    monthly_text: str, daily_text: str, *, source_vintage: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the long monthly and daily industry panels (PLAN §5.2).

    ``ret`` is a simple decimal return. ``n_firms`` and ``avg_size`` (average firm size, $
    millions) on a row dated in month m are the values Ken French reports for month m-1, so a
    decision at the end of month m never uses a characteristic reported for month m (leakage
    item L3). ``available_at`` equals ``date`` because every value on the row is known then.
    """
    vw_m = read_block(monthly_text, VW_MONTHLY, percent=True)
    ew_m = read_block(monthly_text, EW_MONTHLY, percent=True)
    nf = read_block(monthly_text, N_FIRMS, percent=False)
    size = read_block(monthly_text, AVG_SIZE, percent=False)
    vw_d = read_block(daily_text, VW_DAILY, percent=True)
    ew_d = read_block(daily_text, EW_DAILY, percent=True)
    assets = _check_same_columns(vw_m, ew_m, nf, size, vw_d, ew_d)
    clean.rule2_dates(pd.DatetimeIndex(nf.index), "M")  # shift(1) below needs consecutive months
    lagged = pd.concat(
        {
            "n_firms": nf.shift(1)
            .rename_axis("key")
            .reset_index()
            .melt(id_vars="key", var_name="asset", value_name="v")["v"],
            "avg_size": size.shift(1)
            .rename_axis("key")
            .reset_index()
            .melt(id_vars="key", var_name="asset", value_name="v")["v"],
        },
        axis=1,
    )
    keys = nf.rename_axis("key").reset_index().melt(id_vars="key", var_name="asset")
    chars = pd.concat([keys[["key", "asset"]], lagged], axis=1)
    monthly = _long_panel(
        vw_m, ew_m, chars, daily=False, assets=assets, source_vintage=source_vintage
    )
    daily = _long_panel(vw_d, ew_d, chars, daily=True, assets=assets, source_vintage=source_vintage)
    return monthly, daily


FACTOR_NAMES = {
    "Mkt-RF": "mkt_rf",
    "SMB": "smb",
    "HML": "hml",
    "RF": "rf",
    "Mom": "mom",
    "ST_Rev": "st_rev",
}


def build_factor_panel(ff3: str, mom: str, st_rev: str, *, freq: Literal["D", "M"]) -> pd.DataFrame:
    """Wide factor panel ``date, mkt_rf, smb, hml, rf, mom, st_rev`` (decimals) on the dates of
    the Fama-French 3-factor file. Mom and ST_Rev rows outside those dates are dropped."""
    base = read_first_block(ff3, freq=freq, percent=True)
    extra: list[pd.DataFrame | pd.Series] = [
        read_first_block(t, freq=freq, percent=True) for t in (mom, st_rev)
    ]
    out = base.join(extra, how="left")
    out = out.rename(columns=FACTOR_NAMES)
    expected = list(FACTOR_NAMES.values())
    if list(out.columns) != expected:
        raise ParseError(f"factor columns {list(out.columns)} != {expected}")
    return out.rename_axis("date").reset_index()


# ---------------------------------------------------------------------------------------------
# Processing: raw zips -> processed parquet + manifest + data-quality report
# ---------------------------------------------------------------------------------------------


def _read_zip_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        members = zf.namelist()
        if len(members) != 1:
            raise ParseError(f"{path.name}: expected one file in the zip, found {members}")
        return zf.read(members[0]).decode("latin-1")


def _date_range(dates: pd.Series | pd.DatetimeIndex) -> dict[str, Any]:
    d = pd.DatetimeIndex(dates)
    return {
        "first_date": d.min().date().isoformat(),
        "last_date": d.max().date().isoformat(),
    }


def _write_parquet(df: pd.DataFrame, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.part")
    df.to_parquet(tmp, index=False, engine="pyarrow")
    tmp.replace(path)
    content = path.read_bytes()
    return {
        "sha256": _sha256(content),
        "bytes": len(content),
        "rows": len(df),
        **_date_range(df["date"]),
    }


def process_all(
    raw_dir: Path = paths.RAW_DIR,
    processed_dir: Path = paths.PROCESSED_DIR,
    manifest_path: Path = paths.MANIFEST,
    report_path: Path = paths.REPORTS_DIR / "data_quality.json",
    flags_path: Path = paths.REPORTS_DIR / "data_flags_daily.csv",
    *,
    row_level_before: pd.Timestamp = periods.TEST_START,
) -> dict[str, Any]:
    """Parse the raw zips, apply the cleaning rules, write the four processed parquet files,
    update the manifest (rows and dates for raw files, hashes for processed files) and write a
    data-quality report. Returns the report.

    Checks run on every date, but flagged rows are only written for dates before
    ``row_level_before`` (the locked test period gets counts only, DECISIONS 009).
    """
    text = {name: _read_zip_text(raw_dir / name) for name in KF_FILES}
    ind_m_txt = text["49_Industry_Portfolios_CSV.zip"]
    ind_d_txt = text["49_Industry_Portfolios_daily_CSV.zip"]
    manifest = read_manifest(manifest_path)
    raw_entries = manifest.get("raw", {})
    daily_sha = raw_entries.get("49_Industry_Portfolios_daily_CSV.zip", {}).get("sha256", "?")
    vintage = f"crsp={crsp_vintage(ind_d_txt)};sha256={daily_sha[:16]}"
    monthly, daily = build_industry_panels(ind_m_txt, ind_d_txt, source_vintage=vintage)
    fac_m = build_factor_panel(
        text["F-F_Research_Data_Factors_CSV.zip"],
        text["F-F_Momentum_Factor_CSV.zip"],
        text["F-F_ST_Reversal_Factor_CSV.zip"],
        freq="M",
    )
    fac_d = build_factor_panel(
        text["F-F_Research_Data_Factors_daily_CSV.zip"],
        text["F-F_Momentum_Factor_daily_CSV.zip"],
        text["F-F_ST_Reversal_Factor_daily_CSV.zip"],
        freq="D",
    )

    report: dict[str, Any] = {"source_vintage": vintage, "rules": {}}
    rules = report["rules"]
    daily_dates = pd.DatetimeIndex(daily["date"].unique())
    rules["rule2_industry_daily"] = clean.rule2_dates(daily_dates, "D").details
    rules["rule2_industry_monthly"] = clean.rule2_dates(
        pd.DatetimeIndex(monthly["date"].unique()), "M"
    ).details
    rules["rule2_factors_daily"] = clean.rule2_dates(pd.DatetimeIndex(fac_d["date"]), "D").details
    rules["rule2_factors_monthly"] = clean.rule2_dates(pd.DatetimeIndex(fac_m["date"]), "M").details
    report["factor_daily_dates_equal_industry_daily_dates"] = bool(
        pd.DatetimeIndex(fac_d["date"]).equals(daily_dates)
    )
    flag_frames = []
    for w in ("vw", "ew"):
        # pivot (not pivot_table): duplicates must raise, never be aggregated away.
        wide_d = daily[daily["weighting"] == w].pivot(  # noqa: PD010
            index="date", columns="asset", values="ret"
        )
        wide_m = monthly[monthly["weighting"] == w].pivot(  # noqa: PD010
            index="date", columns="asset", values="ret"
        )
        rules[f"rule3_daily_{w}"] = clean.rule3_missing_returns(wide_d).details
        rules[f"rule3_monthly_{w}"] = clean.rule3_missing_returns(wide_m).details
        flags, rep = clean.rule5_flag_outliers(wide_d)
        flags.insert(2, "weighting", w)
        visible = flags["date"] < row_level_before
        flag_frames.append(flags[visible])
        rules[f"rule5_daily_{w}"] = {**rep.details, "n_flagged_test_period": int((~visible).sum())}
    flags_all = pd.concat(flag_frames, ignore_index=True)
    flags_path.parent.mkdir(parents=True, exist_ok=True)
    flags_all.to_csv(flags_path, index=False, lineterminator="\n")
    report["factor_missing"] = {
        f: {c: int(v) for c, v in df.drop(columns="date").isna().sum().items()}
        for f, df in (("monthly", fac_m), ("daily", fac_d))
    }

    processed: dict[str, Any] = {}
    for name, df in (
        ("industry_daily.parquet", daily),
        ("industry_monthly.parquet", monthly),
        ("factors_daily.parquet", fac_d),
        ("factors_monthly.parquet", fac_m),
    ):
        processed[name] = _write_parquet(df, processed_dir / name)
    report["processed"] = processed

    for name in KF_FILES:
        if name not in raw_entries:
            continue
        freq: Literal["D", "M"] = "D" if "daily" in name else "M"
        first = next(b for b in split_blocks(text[name]) if b.freq == freq)
        idx = _parse_dates([r[0] for r in first.rows], freq)
        raw_entries[name].update({"rows": len(first.rows), **_date_range(idx)})
    manifest["raw"] = raw_entries
    manifest["processed"] = processed
    write_manifest(manifest_path, manifest)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point: ``download [--force]`` or ``process``."""
    parser = argparse.ArgumentParser(prog="python -m momlab.data.kenfrench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    dl = sub.add_parser("download", help="download raw zips to data/raw/")
    dl.add_argument("--force", action="store_true", help="download again and record a new vintage")
    sub.add_parser("process", help="parse raw zips into data/processed/*.parquet")
    args = parser.parse_args(argv)
    if args.cmd == "download":
        download_all(paths.RAW_DIR, paths.MANIFEST, force=args.force)
    else:
        rep = process_all()
        for name, entry in rep["processed"].items():
            span = f"{entry['first_date']} to {entry['last_date']}"
            print(f"wrote {name}: {entry['rows']:,} rows, {span}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

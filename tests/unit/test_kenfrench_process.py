"""D-2: end-to-end processing on fixture zips in a temp folder (no network, no real data)."""

import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from momlab import paths
from momlab.data import kenfrench as kf

FIX = Path(__file__).resolve().parents[1] / "fixtures"
HEAD = "This file was created using the 202609 CRSP database.\r\n\r\n"
FF3_M = (
    HEAD
    + ",Mkt-RF,SMB,HML,RF\r\n"
    + "".join(
        f"{d},   1.00,   0.10,  -0.10,   0.30\r\n" for d in ("202301", "202302", "202303", "202304")
    )
)
FF3_D = (
    HEAD
    + ",Mkt-RF,SMB,HML,RF\r\n"
    + "".join(
        f"{d},   0.10,   0.01,  -0.01,   0.01\r\n"
        for d in ("20230130", "20230131", "20230201", "20230228", "20230301")
    )
)
MOM_M = (
    HEAD
    + ",Mom\r\n202302,   2.00\r\n202303,  -99.99\r\n\r\nAnnual Factors:\r\n,Mom\r\n2023, 1.0\r\n"
)
MOM_D = HEAD + ",Mom\r\n20230131,   0.20\r\n20230201,   0.30\r\n"
ST_M = HEAD + ",ST_Rev\r\n202212,   9.00\r\n202301,   0.40\r\n202302,   0.50\r\n"
ST_D = HEAD + ",ST_Rev\r\n20230127,   9.00\r\n20230130,   0.05\r\n20230131,   0.06\r\n"


def _zip(path: Path, member: str, text: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, text.encode("latin-1"))


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    texts = {
        "49_Industry_Portfolios_CSV.zip": (FIX / "kf_sample.csv").read_bytes().decode("latin-1"),
        "49_Industry_Portfolios_daily_CSV.zip": (FIX / "kf_sample_daily.csv")
        .read_bytes()
        .decode("latin-1"),
        "F-F_Research_Data_Factors_CSV.zip": FF3_M,
        "F-F_Research_Data_Factors_daily_CSV.zip": FF3_D,
        "F-F_Momentum_Factor_CSV.zip": MOM_M,
        "F-F_Momentum_Factor_daily_CSV.zip": MOM_D,
        "F-F_ST_Reversal_Factor_CSV.zip": ST_M,
        "F-F_ST_Reversal_Factor_daily_CSV.zip": ST_D,
    }
    for name, text in texts.items():
        _zip(raw / name, name.replace(".zip", ".csv"), text)
    return raw


def _manifest_for(raw: Path, path: Path) -> None:
    entries = {}
    for z in sorted(raw.glob("*.zip")):
        b = z.read_bytes()
        entries[z.name] = {
            "url": kf.BASE_URL + z.name,
            "download_ts": "2026-11-08T00:00:00Z",
            "sha256": hashlib.sha256(b).hexdigest(),
            "bytes": len(b),
        }
    kf.write_manifest(path, {"raw": entries})


def test_process_all_writes_panels_manifest_and_report(raw_dir: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _manifest_for(raw_dir, manifest)
    report = kf.process_all(
        raw_dir, tmp_path / "processed", manifest, tmp_path / "q.json", tmp_path / "flags.csv"
    )
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["processed"]["industry_monthly.parquet"]["rows"] == 24
    assert m["processed"]["industry_daily.parquet"]["last_date"] == "2023-03-01"
    assert m["raw"]["49_Industry_Portfolios_CSV.zip"]["rows"] == 4  # first monthly block
    assert m["raw"]["49_Industry_Portfolios_CSV.zip"]["first_date"] == "2023-01-31"
    assert m["raw"]["F-F_Momentum_Factor_daily_CSV.zip"]["last_date"] == "2023-02-01"
    assert report["source_vintage"].startswith("crsp=202609;sha256=")
    assert report["factor_daily_dates_equal_industry_daily_dates"] is True

    fm = pd.read_parquet(tmp_path / "processed" / "factors_monthly.parquet")
    assert list(fm.columns) == ["date", "mkt_rf", "smb", "hml", "rf", "mom", "st_rev"]
    # ST_Rev's 2022-12 row is outside the FF3 dates and is dropped; Mom's 2023-03 code is NaN.
    assert len(fm) == 4
    assert fm["rf"].tolist() == pytest.approx([0.003] * 4, abs=1e-15)
    assert fm["mom"].isna().tolist() == [True, False, True, True]
    assert fm["st_rev"].tolist()[:2] == pytest.approx([0.004, 0.005], abs=1e-15)
    assert report["factor_missing"]["monthly"]["mom"] == 3

    # Rule 5 flagged Food's +150% day (vw) and nothing else. The fixture dates (2023) are in the
    # locked test period, so only the count is reported and no row is written (DECISIONS 009).
    flags = pd.read_csv(tmp_path / "flags.csv")
    assert flags.empty
    assert list(flags.columns) == ["date", "asset", "weighting", "ret"]
    assert report["rules"]["rule5_daily_vw"]["n_flagged"] == 1
    assert report["rules"]["rule5_daily_vw"]["n_flagged_test_period"] == 1
    assert report["rules"]["rule5_daily_ew"]["n_flagged"] == 0
    q = json.loads((tmp_path / "q.json").read_text(encoding="utf-8"))
    assert q["rules"]["rule3_daily_vw"]["missing_by_asset"] == {"Fun": 2}

    # Deterministic: processing again gives a byte-identical manifest.
    before = manifest.read_bytes()
    kf.process_all(
        raw_dir, tmp_path / "processed", manifest, tmp_path / "q.json", tmp_path / "f.csv"
    )
    assert manifest.read_bytes() == before


def test_zip_with_two_members_raises(tmp_path: Path) -> None:
    p = tmp_path / "x.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("a.csv", "a")
        zf.writestr("b.csv", "b")
    with pytest.raises(kf.ParseError, match="expected one file"):
        kf._read_zip_text(p)


def test_parse_errors() -> None:
    text = (FIX / "kf_sample.csv").read_bytes().decode("latin-1")
    with pytest.raises(kf.ParseError, match="annual"):
        kf.read_block(text, "Average Value Weighted Returns -- Annual", percent=True)
    with pytest.raises(kf.ParseError, match="frequency"):
        kf.read_first_block(text, freq="D", percent=True)
    other = text.replace(",Agric,Food,Fun\r\n202301,      3", ",Agric,Food,Games\r\n202301,      3")
    with pytest.raises(kf.ParseError, match="columns differ"):
        daily = (FIX / "kf_sample_daily.csv").read_bytes().decode("latin-1")
        kf.build_industry_panels(other, daily, source_vintage="v")


def test_factor_columns_checked() -> None:
    bad = FF3_M.replace("Mkt-RF", "Market")
    with pytest.raises(kf.ParseError, match="factor columns"):
        kf.build_factor_panel(bad, MOM_M, ST_M, freq="M")


def test_cli_process(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake = {"processed": {"a.parquet": {"rows": 1234, "first_date": "x", "last_date": "y"}}}
    monkeypatch.setattr(kf, "process_all", lambda: fake)
    assert kf.main(["process"]) == 0
    assert "wrote a.parquet: 1,234 rows, x to y" in capsys.readouterr().out
    assert paths.MANIFEST.name == "manifest.json"


def test_flag_rows_written_before_cutoff(raw_dir: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _manifest_for(raw_dir, manifest)
    kf.process_all(
        raw_dir,
        tmp_path / "processed",
        manifest,
        tmp_path / "q.json",
        tmp_path / "flags.csv",
        row_level_before=pd.Timestamp("2100-01-01"),
    )
    flags = pd.read_csv(tmp_path / "flags.csv")
    assert flags.to_dict("records") == [
        {"date": "2023-02-01", "asset": "Food", "weighting": "vw", "ret": 1.5}
    ]

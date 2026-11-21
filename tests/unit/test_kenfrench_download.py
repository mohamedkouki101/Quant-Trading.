"""D-1: Ken French downloader. The HTTP layer is mocked; no test here touches the network."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
import requests

from momlab.data import kenfrench as kf


def _zip_bytes(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, text)
    return buf.getvalue()


class FakeResponse:
    def __init__(self, content: bytes, status: int = 200) -> None:
        self.content = content
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=None)


class FakeGet:
    """Records calls; returns a fixed zip per URL, or raises/returns the queued outcomes."""

    def __init__(self, outcomes: list[object] | None = None) -> None:
        self.calls: list[str] = []
        self.timeouts: list[object] = []
        self.outcomes = list(outcomes or [])

    def __call__(self, url: str, timeout: object) -> FakeResponse:
        self.calls.append(url)
        self.timeouts.append(timeout)
        if self.outcomes:
            nxt = self.outcomes.pop(0)
            if isinstance(nxt, BaseException):
                raise nxt
            assert isinstance(nxt, FakeResponse)
            return nxt
        name = url.rsplit("/", 1)[1]
        return FakeResponse(_zip_bytes(name.replace(".zip", ".csv"), f"content of {name}\n"))


def test_file_list_matches_research_inventory() -> None:
    assert kf.KF_FILES == (
        "49_Industry_Portfolios_CSV.zip",
        "49_Industry_Portfolios_daily_CSV.zip",
        "F-F_Research_Data_Factors_CSV.zip",
        "F-F_Research_Data_Factors_daily_CSV.zip",
        "F-F_Momentum_Factor_CSV.zip",
        "F-F_Momentum_Factor_daily_CSV.zip",
        "F-F_ST_Reversal_Factor_CSV.zip",
        "F-F_ST_Reversal_Factor_daily_CSV.zip",
    )
    assert kf.BASE_URL == "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"


def test_download_writes_files_and_manifest(tmp_path: Path) -> None:
    get = FakeGet()
    manifest = tmp_path / "manifest.json"
    kf.download_all(tmp_path / "raw", manifest, get=get)

    assert len(get.calls) == 8
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for name in kf.KF_FILES:
        entry = data["raw"][name]
        content = (tmp_path / "raw" / name).read_bytes()
        assert entry["url"] == kf.BASE_URL + name
        assert entry["sha256"] == hashlib.sha256(content).hexdigest()
        assert entry["bytes"] == len(content)
        assert entry["download_ts"].endswith("Z")  # UTC ISO-8601


def test_second_run_is_idempotent(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    kf.download_all(tmp_path / "raw", manifest, get=FakeGet())
    before = manifest.read_bytes()
    get2 = FakeGet()
    kf.download_all(tmp_path / "raw", manifest, get=get2)
    assert get2.calls == []
    assert manifest.read_bytes() == before


def test_changed_file_on_disk_is_redownloaded(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    kf.download_all(tmp_path / "raw", manifest, get=FakeGet())
    (tmp_path / "raw" / kf.KF_FILES[0]).write_bytes(b"corrupted")
    get2 = FakeGet()
    kf.download_all(tmp_path / "raw", manifest, get=get2)
    assert get2.calls == [kf.BASE_URL + kf.KF_FILES[0]]


def test_force_redownloads_and_keeps_old_vintage(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    kf.download_all(tmp_path / "raw", manifest, get=FakeGet(), files=kf.KF_FILES[:1])
    name = kf.KF_FILES[0]
    first = json.loads(manifest.read_text(encoding="utf-8"))["raw"][name]

    new_zip = _zip_bytes("x.csv", "revised data\n")
    get2 = FakeGet([FakeResponse(new_zip)])
    kf.download_all(tmp_path / "raw", manifest, get=get2, files=kf.KF_FILES[:1], force=True)
    second = json.loads(manifest.read_text(encoding="utf-8"))["raw"][name]

    assert get2.calls == [kf.BASE_URL + name]
    assert second["sha256"] == hashlib.sha256(new_zip).hexdigest()
    assert second["previous_vintages"] == [
        {k: first[k] for k in ("download_ts", "sha256", "bytes")}
    ]


def test_one_retry_then_success(tmp_path: Path) -> None:
    ok = FakeResponse(_zip_bytes("a.csv", "a\n"))
    get = FakeGet([requests.ConnectionError("boom"), ok])
    kf.download_all(tmp_path / "raw", tmp_path / "m.json", get=get, files=kf.KF_FILES[:1])
    assert len(get.calls) == 2
    assert get.timeouts[0] == kf.TIMEOUT


def test_two_failures_raise_clear_error(tmp_path: Path) -> None:
    get = FakeGet([requests.Timeout("slow"), FakeResponse(b"", status=503)])
    with pytest.raises(kf.DownloadError, match="site may be down"):
        kf.download_all(tmp_path / "raw", tmp_path / "m.json", get=get, files=kf.KF_FILES[:1])
    assert not (tmp_path / "raw" / kf.KF_FILES[0]).exists()
    assert not (tmp_path / "m.json").exists()


def test_html_error_page_is_rejected(tmp_path: Path) -> None:
    page = FakeResponse(b"<html>maintenance</html>")
    get = FakeGet([page, page])
    with pytest.raises(kf.DownloadError, match="not a zip"):
        kf.download_all(tmp_path / "raw", tmp_path / "m.json", get=get, files=kf.KF_FILES[:1])


def test_manifest_keeps_other_sections(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"processed": {"x.parquet": {"sha256": "abc"}}}), "utf-8")
    kf.download_all(tmp_path / "raw", manifest, get=FakeGet(), files=kf.KF_FILES[:1])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["processed"] == {"x.parquet": {"sha256": "abc"}}
    assert manifest.read_bytes().endswith(b"}\n")
    assert b"\r\n" not in manifest.read_bytes()


def test_cli_parses_force(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_download_all(raw_dir: Path, manifest_path: Path, *, force: bool = False) -> None:
        seen["force"] = force
        seen["raw_dir"] = raw_dir

    monkeypatch.setattr(kf, "download_all", fake_download_all)
    assert kf.main(["download", "--force"]) == 0
    assert seen["force"] is True
    assert kf.main(["download"]) == 0
    assert seen["force"] is False

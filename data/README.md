# data/

Raw and processed data are **never committed**. They are downloaded and built by code:

```
uv run python tasks.py data
```

| Folder | Content | In git? |
|---|---|---|
| `raw/` | Downloaded zip files exactly as served | no (gitignored) |
| `interim/` | Temporary parsing output | no (gitignored) |
| `processed/` | Long-format parquet panels (PLAN §5.2) | no (gitignored) |
| `manifest.json` | URL, download time, sha256, rows and date range per file | **yes** |

Ken French data is Copyright Eugene F. Fama and Kenneth R. French. See `docs/DATA.md`.

# DataTrust

**A trust report for every Hugging Face dataset.**

People train AI models on datasets from Hugging Face without knowing:

- Is the license real and safe to use?
- Was this dataset built from another dataset with a stricter license?
- Is it a near-copy of another dataset?
- Is it abandoned?

DataTrust checks all of this automatically and gives each dataset a **trust score from 0 to 100**, plus a report page, a public JSON API, and a badge you can add to your README.

> ⚠️ **Scores are informational only and are not legal advice.** Always read a dataset's actual license before using it.

## Status

🚧 Early development — **v0.1.0: data pipeline working.** The top 5,000 most-downloaded datasets
are collected from the Hugging Face API and cleaned by a Spark job into one Parquet table.

### First findings (top 5,000 datasets, collected October 2026)

- **39%** have no README at all.
- **50%** state no license anywhere (tags or README text); only **~31%** have a clearly permissive license.
- Only **18%** of READMEs say where the data came from, and only **15%** describe limitations or bias.
- **34%** are flagged as *likely not a dataset* (file hosting, model-weight dumps) — and they receive
  **23.5%** of all downloads in the top 5,000.

### Try the pipeline locally

Needs Python 3.12 and Docker Desktop.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                # then add your free Hugging Face read token
python -m datatrust.collector.run_collect --limit 50
docker compose run --rm pipeline python -m datatrust.pipelines.clean_metadata
pytest                              # Spark tests run inside Docker: docker compose run --rm pipeline pytest
```

Full design notes, decisions, and progress: [docs/PROJECT_HANDBOOK.md](docs/PROJECT_HANDBOOK.md).

## Roadmap

- [x] v0.1.0 — Collect and clean dataset metadata from the Hugging Face API
- [ ] v0.2.0 — Lineage graph, license-conflict, duplicate, and health checks
- [ ] v0.3.0 — Trust score
- [ ] v0.4.0 — Public JSON API (FastAPI)
- [ ] v0.5.0 — Search website and embeddable badge
- [ ] v0.6.0 — Tests and CI/CD
- [ ] v1.0.0 — Public launch

## Tech stack

Python · PySpark · Parquet · DuckDB · FastAPI · React (Vite) · Docker · GitHub Actions · Hugging Face Spaces · Cloudflare Pages

## License

Code is released under the [MIT License](LICENSE).

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

🚧 Early development. See the roadmap below.

## Roadmap

- [ ] v0.1.0 — Collect and clean dataset metadata from the Hugging Face API
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

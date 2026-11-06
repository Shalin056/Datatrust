# DataTrust — Progress Report

A running log of what we started, how we built it, what is finished, and what comes next.
**Updated at the end of every work session.** Newest session is at the top of the
[Session log](#session-log).

_Last updated: 2026-11-05_

---

## At a glance

| | |
|---|---|
| **Current step** | Step 4 — Clean and store the data (sub-steps 4.1–4.3 done) |
| **Current branch** | `feature/cleaning` — 10 commits, not pushed yet (pushed + merged at Step 4.7) |
| **Tests** | 59 passing (`pytest`), lint clean (`ruff check .`) |
| **Data collected** | Top 5,000 HF datasets by downloads + 5,000 README cards (54.5 MB, collected 2026-10-18) |
| **Last version tag** | none yet — `v0.1.0` comes at the end of Step 4 |
| **Next action** | Step 4.4 — find licenses written inside README text |

### Waiting on you
- [ ] Commit this report: `git add docs/PROGRESS.md` then `git commit -m "docs: add progress report"`
- [ ] Optional side work: confirm the Windows PySpark practice setup works (see [Side work](#side-work-not-part-of-the-project-code))

---

## Accounts and names

| Thing | Name / link | Status |
|---|---|---|
| GitHub repo | <https://github.com/Shalin056/Datatrust> (public) | ✅ in use |
| Git commit email | GitHub noreply address (personal email kept private) | ✅ set |
| Hugging Face account | `Shalin0203` | ✅ |
| HF token | **Read** token, stored only in `.env` (never committed) | ✅ in use |
| HF dataset repo (processed data) | `Shalin0203/datatrust-data` | ⏳ not created yet (needs a **Write** token) |
| HF Space (API) | `Shalin0203/datatrust-api` | ⏳ Step 10 |
| Website | Cloudflare Pages | ⏳ Step 10 |

---

## How to run things (cheat sheet)

There are **two Python environments** on purpose:

| Environment | Used for | Libraries from |
|---|---|---|
| Windows `.venv` | Collector, plain-Python logic, `pytest`, `ruff` | `requirements-dev.txt` |
| Docker `pipeline` container | Anything that uses Spark (PySpark is **only** here) | `requirements-pipeline.txt` |

```
# Windows .venv (activate first in each new PowerShell window)
.venv\Scripts\Activate.ps1                     # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pytest                                          # run all tests
ruff check .                                    # lint
python -m datatrust.collector.run_collect       # collect data (--limit N, --skip-cards, --fresh)

# Docker (open Docker Desktop first, wait for "Engine running")
docker compose build pipeline                                       # build/refresh the Spark image
docker compose run --rm pipeline python -m datatrust.pipelines.inspect_raw   # look at raw data
```

Settings priority for how many datasets to collect: `--limit` on the command line > `MAX_DATASETS` in `.env` > `configs/settings.yaml`.

---

## Roadmap

| # | Step | Status | Branch | Tag |
|---|---|---|---|---|
| 1 | Project plan + folder structure | ✅ Done | — | — |
| 2 | Git, GitHub, first commits | ✅ Done | `main` | — |
| 3 | Collect the data | ✅ Done (merged, PR #1) | `feature/collector` | — |
| 4 | Clean and store the data | 🔄 In progress (3 of 7 sub-steps) | `feature/cleaning` | `v0.1.0` |
| 5 | Lineage, license-conflict, duplicate, health checks | ⏳ Not started | — | `v0.2.0` |
| 6 | Trust score | ⏳ Not started | — | `v0.3.0` |
| 7 | API (FastAPI) | ⏳ Not started | — | `v0.4.0` |
| 8 | Website + badge | ⏳ Not started | — | `v0.5.0` |
| 9 | Tests + CI/CD | ⏳ Not started | — | `v0.6.0` |
| 10 | Deploy online | ⏳ Not started | — | `v0.9.0` |
| 11 | Documentation + launch | ⏳ Not started | — | `v1.0.0` |

### Step 4 sub-steps

| Sub-step | What | Status | Commits |
|---|---|---|---|
| 4.1 | Spark in Docker + first read-only look at the data | ✅ Done | 4 |
| 4.2 | License IDs → plain categories | ✅ Done | 3 |
| 4.3 | Split README cards into sections | ✅ Done | 3 |
| 4.4 | Find licenses written inside README text | ⏭️ **Next** | — |
| 4.5 | Spark cleaning job: raw JSONL → clean Parquet | ⏳ | — |
| 4.6 | `likely_not_a_dataset` flag + Spark tests in Docker | ⏳ | — |
| 4.7 | Push, PR, merge, tag `v0.1.0` | ⏳ | — |

### Planned but not yet scheduled into a sub-step
- **Publish processed data to the HF dataset repo** (`datatrust/export/publish_to_hub.py`). The original plan put this in Step 4; it is not in the 4.1–4.7 list. Proposal: do it together with the scheduled refresh job (Steps 9–10), since that is when the website/API first need it online. Needs a Write token.
- **Hand-labeled lineage test set** (`data/labels/lineage_gold.csv` + `LABELING_GUIDE.md`, ~100 rows) — Step 5, to measure lineage precision/recall.
- **License conflict rules** (`configs/license_rules.yaml`) — Step 5.
- **Score weights** (`configs/score_weights.yaml`) — Step 6.
- **"Informational only, not legal advice" notice** in the app and API — Steps 7–8.
- **README with architecture diagram, setup steps, known limitations** — Step 11 (this report feeds it).
- **Grow collection to ~10,000 datasets** to make up for the junk repos — after Step 4.
- **Build later (after v1.0):** full-Hub crawl, duplicate detection by file hashes, comparing actual dataset contents, ML-based lineage detection, user feedback on wrong links.

---

## File inventory

All 45 files in the repo (plus this report), and the step that created each.

| File | Step | Purpose |
|---|---|---|
| `.gitignore` | 2 | Never commit secrets (`.env`), data, caches |
| `.gitattributes` | 2 | LF line endings so scripts work in Linux/Docker |
| `.env.example` | 2 | Settings template (`HF_TOKEN=`, `MAX_DATASETS=`), no real values |
| `README.md` | 2 | Front page (short for now; finished in Step 11) |
| `LICENSE` | 2 | MIT license for our code |
| `data/{raw,clean,output,samples,labels}/.gitkeep` | 2 | Keep empty data folders in Git |
| `pyproject.toml` | 3 | Project info + pytest and ruff settings |
| `requirements.txt` | 3 | Run-time libraries: requests, python-dotenv, PyYAML |
| `requirements-dev.txt` | 3 | + pytest, ruff |
| `configs/settings.yaml` | 3 | Collection size, page size, paths, timeouts, retries |
| `datatrust/__init__.py` | 3 | Marks the package |
| `datatrust/config.py` | 3 | Loads settings + `.env` |
| `datatrust/logging_setup.py` | 3 | Timestamped log lines |
| `datatrust/io_utils.py` | 3 | Read/write/append JSONL (not in the original plan; both fetchers needed it) |
| `datatrust/collector/__init__.py` | 3 | Marks the sub-package |
| `datatrust/collector/hf_client.py` | 3 | HF HTTP client: token, retries, rate-limit waits |
| `datatrust/collector/fetch_datasets.py` | 3 | Dataset list + metadata |
| `datatrust/collector/fetch_cards.py` | 3 | README cards, resumable |
| `datatrust/collector/run_collect.py` | 3 | The collect command |
| `tests/__init__.py` | 3 | Lets tests import shared helpers (not in the original plan) |
| `tests/conftest.py` | 3 | Fake HTTP session/response + no-sleep fixture |
| `tests/fixtures/api_datasets_page.json` | 3 | Real 2-item sample from the HF API |
| `tests/test_config.py` | 3 | 4 tests |
| `tests/test_io_utils.py` | 3 | 5 tests |
| `tests/test_hf_client.py` | 3 | 14 tests |
| `tests/test_fetch_datasets.py` | 3 | 6 tests |
| `tests/test_fetch_cards.py` | 3 | 5 tests |
| `requirements-pipeline.txt` | 4.1 | + pyspark 4.1.3 (Docker only) |
| `docker/spark.Dockerfile` | 4.1 | Python 3.12 + Java 17 + PySpark image |
| `docker-compose.yml` | 4.1 | `pipeline` service, mounts project at `/app`, reads `.env` |
| `.dockerignore` | 4.1 | Keep `.env` and `data/` out of the image |
| `datatrust/pipelines/__init__.py` | 4.1 | Marks the sub-package |
| `datatrust/pipelines/spark_session.py` | 4.1 | `create_spark()` with local-mode settings |
| `datatrust/pipelines/raw_schemas.py` | 4.1 | Hand-written schemas for raw JSONL (new vs plan) |
| `datatrust/pipelines/inspect_raw.py` | 4.1 | Read-only data summary (new vs plan) |
| `configs/licenses.yaml` | 4.2 | License ID → name + category (replaces the planned `license_aliases.yaml`; aliases arrive in 4.4) |
| `datatrust/pipelines/normalize_license.py` | 4.2 | License tags → IDs + one category |
| `tests/test_normalize_license.py` | 4.2 | 12 tests |
| `configs/card_sections.yaml` | 4.3 | Heading keywords per section (new vs plan) |
| `datatrust/pipelines/parse_cards.py` | 4.3 | Card → sections with real content |
| `tests/test_parse_cards.py` | 4.3 | 13 tests |
| `docs/PROGRESS.md` | — | This report |

**Not in Git (on purpose):** `.env` (token), `.venv/` (local libraries), `data/raw/datasets.jsonl` and `data/raw/cards.jsonl` (rebuilt by the collector).

---

## Completed work

### Step 1 — Project plan and folder structure ✅ (2026-10-18)

**What:** Agreed the architecture, trust-score parts, hosting plan, and the full folder layout.

**How / key decisions:**
- Pipeline of separate steps, each reading and writing files (raw JSONL → clean Parquet → outputs), so one step can be re-run without redoing the others.
- **Spark + Parquet, no Hadoop/HDFS.** Data fits on one machine; Spark local mode uses all CPU cores. Spark's real value here is near-duplicate detection (MinHash LSH) in Step 5. Reason to write in the README: HDFS was evaluated and not needed at this size.
- Spark runs **in Docker**, because Spark on plain Windows needs extra Hadoop helper files.
- Hosting: GitHub (code + scheduled jobs), HF dataset repo (processed data), HF Spaces (API), Cloudflare Pages (website + static badge JSON so badges work while the free API sleeps).
- First trust-score design: license clarity 25, license safety 25, documentation 20, maintenance 15, originality 15 (weights to live in a config file).
- Honest risks noted: rate limits, messy licenses, lineage guessing from free text, not legal advice, free-hosting sleep and storage resets.

**Tools checked:** Git 2.49, Python 3.12.9 (used instead of the suggested 3.11), Node upgraded 18 → 24.22 (18 is end-of-life and too old for Vite), Docker 28.3 + WSL2 (default version 2, Ubuntu installed). First `docker run hello-world` failed because the Docker engine was not running; fixed by opening Docker Desktop.

### Step 2 — Git, GitHub, first commits ✅ (2026-10-18)

**What:** Turned the folder into a Git repo and pushed it to GitHub.

**How:**
- Files: `.gitignore`, `.gitattributes`, `.env.example`, `README.md`, `LICENSE`, `data/*/.gitkeep`. Ignore rules were tested on a scratch copy before committing.
- Switched Git to the GitHub **noreply email**.
- Created an HF **read token**, stored only in `.env`; `git status` confirmed it is ignored.
- 3 commits: `chore: add gitignore and gitattributes`, `docs: add README and MIT license`, `chore: add env template and data folders`.
- Learned: `init`, `status`, `add`, `commit`, `log`, `remote`, `push -u`.

### Step 3 — Collect the data ✅ (2026-10-18, merged as PR #1)

**What:** Downloaded metadata for the 5,000 most-downloaded HF datasets plus each one's README card.

**How:**
- `hf_client.py` — adds the token and a User-Agent; retries 429/500/502/503/504 and network errors with exponential backoff (2s, 4s, 8s … max 60s, 5 attempts); on 429 waits exactly the reset time HF sends (`RateLimit: "api";r=0;t=213`); returns 404/401 without retrying; follows the `Link: rel="next"` header for paging.
- `fetch_datasets.py` — `/api/datasets?sort=downloads&direction=-1&limit=1000&full=true`; flattens each item, keeping license from both tags and card header for later comparison.
- `fetch_cards.py` — downloads `https://huggingface.co/datasets/<id>/resolve/main/README.md`; appends each result immediately (crash-safe); skips finished cards on re-run but retries `error` ones; cuts cards longer than 200,000 characters.
- Tests use a **fake internet connection** (`tests/conftest.py`), so no real API calls; sleeps are faked so retry tests run instantly.
- Set up the Windows `.venv` and installed `requirements-dev.txt`.
- Workflow learned: feature branch → 10 small commits → push → Pull Request → merge commit → delete branch → `git pull` on `main`.

**Observed free rate limits (without token):** 500 API calls and 3,000 file downloads per 5 minutes. With the token we were never limited.

**Results:** 5,000 datasets and 5,000 cards, **0 errors**, ~14 minutes (16:39–16:53), resume tested and working.

### Step 4.1 — Spark in Docker + first look ✅ (2026-10-24)

**What:** Got Spark running and inspected the raw data without changing it.

**How:**
- `docker/spark.Dockerfile` — `python:3.12-slim-bookworm` + `openjdk-17-jre-headless` + PySpark 4.1.3. Requirements are copied before code so Docker caches the slow install. Code is not baked in; it is mounted at run time.
- `docker-compose.yml` — the `pipeline` service; `.env` passed at run time (optional), never stored in the image.
- `spark_session.py` — `local[*]`, 2 GB driver memory, 8 shuffle partitions (instead of 200), UTC time zone, web UI and progress bars off, WARN-level logs.
- `inspect_raw.py` — counts, schema, card status counts, top licenses (uses `groupBy`, `explode_outer`).
- First image build took ~125 s (pip install 70 s, Java 17 s); later builds reuse the cache.
- Harmless startup messages to ignore: `NativeCodeLoader: Unable to load native-hadoop library`, `Using incubator modules`.
- 4 commits.

**Bug found and fixed:** Spark's automatic schema guessing crashed with `COLUMN_ALREADY_EXISTS: formats` because `tokyotech-llm/swallow-math-v2` writes `formats` and `X-Humanoid/ArtVIP` writes `Formats` (also `modalities`/`Modalities`). Fix: hand-written schemas in `raw_schemas.py`; `card_data` kept as one JSON text column; `license_from_card` read as text because some cards give a list (e.g. `openai/gsm8k` → `["mit"]`).

### Step 4.2 — License categories ✅ (2026-11-02)

**What:** Translate each license ID into one plain-language category.

**How:**
- Found that HF license **tags are already clean** (43 distinct IDs from HF's fixed list; card header and tags never disagree; no license appears only in the card header). So the job is *meaning*, not spelling.
- `configs/licenses.yaml` — every ID → name + category. Categories (least → most restrictive): `public_domain`, `permissive`, `restricted_use`, `share_alike`, `non_commercial`, `no_derivatives`, `custom`, `unclear`; the code adds `missing` for no license.
- `normalize_license.py` — plain Python (testable on Windows, called by Spark later). Output: `license_ids`, `license_category`, `license_detail` (custom name for `other`), `has_multiple_licenses`. Several licenses → the **strictest** (we can't tell "either" from "both"). Unknown new IDs → `unclear`, never a crash. Category typos in the YAML fail loudly at load time.
- 12 tests, 3 commits.
- Judgment calls: plain `cc` = unclear; `cc-by-nc-nd` = no_derivatives; RAIL licenses and `c-uda` = restricted_use; `apple-amlr` = non_commercial.

**Results on real data:** every ID in our data is in the table (nothing unclear by accident); 19 datasets list more than one license; of 268 `other` licenses, 124 give a name or link.

### Step 4.3 — README sections ✅ (2026-11-02)

**What:** Detect which key sections each card has **with real content**: description, structure, uses, sources, limitations, license, citation. Output: `has_front_matter`, `word_count`, `sections_found`, `section_texts`, `empty_sections`.

**How:**
- Counted the most common real headings first (`Citation` 875, `Dataset Structure` 625, `Dataset Description` 572 …) and built the keyword list from them.
- `configs/card_sections.yaml` — keywords per section; order matters (first match wins).
- `parse_cards.py` — splits off the YAML header; walks lines; ignores `#` lines inside ``` code blocks (647 real cards have them); regex for headings; normalizes headings (removes emojis/numbers/punctuation); whole-word matching with `\b`; ignores filler like `[More Information Needed]` (in 198 cards), `TBD`, `TODO`, `N/A`, `coming soon`; joins several headings that map to the same section.
- 13 tests, 3 commits.

**Bug caught by tests:** the first rule required 20 characters, which marked a License section saying just `MIT` as empty. Replaced with "remove filler, then need ≥ 3 letters/digits".

---

## Data findings so far

From the top 5,000 datasets (collected 2026-10-18):

- **39% have no README at all** (1,953). Many are not real datasets: **357** are image hosting repos (`icdn10`…`icdn18`), **752** are `owner/owner` repos full of randomly named model-weight files.
- Missing READMEs get more common further down: 23% in the top 500, 27% in 500–1,000, 41–46% below rank 1,000.
- **52% have no license tag** (2,605). 31% permissive, 5.4% non-commercial, 5.4% custom (`other`), 2.8% share-alike, 1.6% unclear, 1.2% public domain, 0.3% no-derivatives, 0.2% restricted-use.
- Of the 2,605 untagged datasets, 652 have a README and 64 of those have a License section (used in Step 4.4).
- Of 3,047 cards that exist: citation 47%, description 38%, structure 35%, license section 33%, uses 21%, **sources 18%**, **limitations 15%**. 1,033 cards (34%) have none of the 7 sections.
- Median card length: 430 words.

---

## Known limitations / open questions

- **Description count is too low:** text under a title like `# Dataset Card for X` is not counted as a description. Step 5 will also use the API's short description; may add a "text under the title" rule.
- **Strictest-license rule** is sometimes too strict for truly dual-licensed datasets.
- **Download ranking** only covers ~the last 30 days and is inflated by file-hosting repos.
- **License categories are simplified readings, not legal advice** (must be stated in the app).
- Setext-style headings (text underlined with `===`) are not detected — rare.
- Filler removal is a plain text replace, so the word "todo" inside a longer word is also removed — harmless for real sections.
- Spark code (`spark_session.py`, `inspect_raw.py`) has no automated tests yet — planned in Step 4.6.
- Raw data is a one-time snapshot (2026-10-18); no scheduled refresh until Step 9.

---

## Side work (not part of the project code)

- **PySpark on Windows for personal practice** (2026-11-04). Found: Java 19 installed (not a supported Spark version), no `JAVA_HOME`, no `HADOOP_HOME`, winget available. Plan given: install Java 21 (`winget install --id EclipseAdoptium.Temurin.21.JDK -e`), `setx JAVA_HOME ...`, separate folder `C:\Users\shali\spark-practice` with its own venv and `pyspark==4.1.3`, a `hello_spark.py` test (sets `PYSPARK_PYTHON` to avoid the Windows worker error). Writing files on Windows needs unofficial `winutils.exe`/`hadoop.dll` from community repos; WSL Ubuntu suggested as the cleaner option. **Status: not yet confirmed as working.**

---

## Next step: 4.4 — Licenses inside README text

**Goal:** For datasets with **no license tag**, read the card's License section and recognise names like "Apache-2.0 License", "CC BY 4.0", "MIT." and map them to our license IDs.

**Why:** 652 untagged datasets have a README; 64 of those have a License section. This is where the truly messy license names live.

**Plan:** add name variations ("aliases") per license, a small matcher that only looks inside the License section found by `parse_cards.py` (so "MIT researchers" elsewhere is never a match), tests, and a `license_source` field (`tag` / `card_text` / `none`).

---

## Working agreements

- Go slowly: each step split into small sub-steps (1–3 files), with a walkthrough of how the code works, then wait for "next".
- One feature branch per step; small commits in the style `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `build:`; Pull Request with a merge commit; version tag at each milestone.
- Every code file starts with a header (what it does / what it uses / what uses it); every function has a comment above it (what / inputs / returns).
- Never commit secrets; never paste the token anywhere.
- This report is updated at the end of every session.

---

## Session log

### 2026-11-05
- Created this progress report (`docs/PROGRESS.md`), then double-checked it against the repo (all 45 files, 24 commits, 59 tests) and the real data; corrected the image-hosting count to 357 and added missing sections (accounts, cheat sheet, file inventory, planned work, waiting-on-you list).

### 2026-11-04
- Clarified that PySpark is installed only in the Docker image, not the Windows `.venv` (by design). Docker Desktop was not running at the time.
- Gave a separate setup for PySpark on Windows for personal practice.

### 2026-11-02
- Step 4.2 done: license category table + normalizer + 12 tests.
- Step 4.3 done: card section parser + 13 tests. Total 59 tests.
- Agreed to go slower: each step split into small sub-steps with code walkthroughs.

### 2026-10-24
- Step 4.1 done: Spark Docker image, session helper, explicit schemas (fixed `formats`/`Formats` crash), raw-data inspector.

### 2026-10-18
- Steps 1–3 done: plan, tool checks, Git/GitHub setup, collector (34 tests), full collection of 5,000 datasets + cards, PR #1 merged.
- Investigated the 39% missing READMEs — real, not a bug.

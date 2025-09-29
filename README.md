# County Health Rankings API Prototype
This homework was done in partner with Codex. This repository contains the submission for CS106 homework 4. It includes a utility script for converting CSV data into a SQLite database and a Flask API prototype that exposes the requested `county_data` endpoint.

## Project structure

- `csv_to_sqlite.py` &mdash; Script that ingests a CSV file and writes/updates a table in `data.db`.
- `api/index.py` &mdash; Flask application that implements the `county_data` endpoint backed by `data.db`.
- `requirements.txt` &mdash; Python dependencies for the API.
- `link.txt` &mdash; URL to the deployed endpoint (update after deployment).
- `.gitignore` &mdash; Ignores temporary and generated files.

Both code files include inline comments documenting that generative AI (OpenAI GPT-5 Codex) was used, per the assignment policy.

## Prerequisites

- Python 3.11 or newer.
- `pip` for installing dependencies.
- The February 2025 versions of `zip_county.csv` and `county_health_rankings.csv` from the assignment prompt.

## 1. Build `data.db`

1. Download the two CSV files into the repository root.
2. Create or overwrite the SQLite database by running:

   ```bash
   python3 csv_to_sqlite.py data.db zip_county.csv
   python3 csv_to_sqlite.py data.db county_health_rankings.csv
   ```

   Each invocation drops and recreates the table that matches the CSV filename stem (e.g., `zip_county.csv` &rarr; `zip_county`).

## 2. Run the API locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Launch the Flask app:

   ```bash
   python3 api/index.py
   ```

   The service listens on port 8000 by default.

3. Query the endpoint:

   ```bash
   curl -H 'content-type: application/json' \
        -d '{"zip":"02138","measure_name":"Adult obesity"}' \
        http://127.0.0.1:8000/county_data
   ```

### Expected behavior

- Requires JSON POST with `zip` (5-digit string) and `measure_name` (one of the 12 allowed measure names).
- Returns matching rows using the `county_health_rankings` schema for the counties mapped to the given ZIP.
- Returns HTTP 400 if inputs are missing or invalid.
- Returns HTTP 404 if the ZIP/measure combination is not found.
- Returns HTTP 418 if the payload includes `{"coffee": "teapot"}`.

## 3. Deploying

### Option A: Netlify (files included)

This repo now contains the bits Netlify needs under `netlify/functions/` plus a `netlify.toml` build config.

1. Run the two `csv_to_sqlite.py` commands locally (see section 1) so that `data.db` exists in the project root.
2. Push the repository to GitHub (private) and connect it when creating a Netlify site.
3. Netlify will execute the build command from `netlify.toml`, which installs dependencies into `netlify/functions/` and copies `data.db` next to the Python function (`netlify/functions/county_data.py`).
4. After the deploy completes, test the endpoint at `https://<yoursite>.netlify.app/county_data` using a POST request with JSON.
5. Update `link.txt` with the production URL once everything works.

> **Note:** If you prefer, you can run the build command locally before committing (to vendor dependencies) but it is not required—Netlify will install them during the deploy.

### Option B: Other platforms

The Flask app remains compatible with WSGI platforms such as Render or Vercel. A typical flow is:

1. Create a new private repository (named `<username>-hw4`) under the `cs1060f25` organization based on this project.
2. Upload `data.db` to the hosting provider using the two CSV files and `csv_to_sqlite.py`, then configure the service to expose the Flask app.
3. After the endpoint is live, replace the placeholder URL in `link.txt` with the deployed `county_data` URL.

## Tests

A minimal smoke test can be run via Flask's test client:

```bash
python3 - <<'PY'
from api.index import APP
client = APP.test_client()
print(client.post('/county_data', json={
    'zip': '02138',
    'measure_name': 'Adult obesity'
}))
PY
```

(Ensure `data.db` already contains the relevant tables before running the test.)

## Notes

- `csv_to_sqlite.py` expects valid CSV headers that map directly to SQL identifiers (alphanumeric and underscores, starting with a letter or underscore).
- The API checks for both FIPS codes and county/state names when joining ZIP data to county statistics to accommodate variations in the provided datasets.

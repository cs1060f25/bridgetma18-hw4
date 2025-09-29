"""Flask entrypoint for the county_data API."""

# Source: Implemented with assistance from OpenAI's GPT-5 (Codex) in the Harvard CS106 Codex CLI.

from __future__ import annotations

import json
import re
import sqlite3
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, HTTPException, NotFound

APP = Flask(__name__)

# Allow overriding via environment variable if desired at deploy time.
DB_PATH = Path(__file__).resolve().parent.parent / "data.db"

ALLOWED_MEASURES = {
    "Violent crime rate",
    "Unemployment",
    "Children in poverty",
    "Diabetic screening",
    "Mammography screening",
    "Preventable hospital stays",
    "Uninsured",
    "Sexually transmitted infections",
    "Physical inactivity",
    "Adult obesity",
    "Premature Death",
    "Daily fine particulate matter",
}

ZIP_PATTERN = re.compile(r"^\d{5}$")


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    if not DB_PATH.exists():
        raise NotFound(description=f"Database not found at {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def validate_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """Validate and normalize incoming JSON payload."""
    zip_code = payload.get("zip")
    measure_name = payload.get("measure_name")

    if zip_code is None or measure_name is None:
        raise BadRequest(description="Both 'zip' and 'measure_name' are required")

    if not isinstance(zip_code, str) or not ZIP_PATTERN.match(zip_code):
        raise BadRequest(description="zip must be a 5-digit string")

    if not isinstance(measure_name, str):
        raise BadRequest(description="measure_name must be a string")

    if measure_name not in ALLOWED_MEASURES:
        raise BadRequest(description="measure_name must be one of the documented measures")

    return {"zip": zip_code, "measure_name": measure_name}


def lookup_county_data(zip_code: str, measure_name: str) -> List[Dict[str, Any]]:
    """Query data.db for rows matching the requested zip and measure."""
    query = """
        SELECT DISTINCT
            chr.state,
            chr.county,
            chr.state_code,
            chr.county_code,
            chr.year_span,
            chr.measure_name,
            chr.measure_id,
            chr.numerator,
            chr.denominator,
            chr.raw_value,
            chr.confidence_interval_lower_bound,
            chr.confidence_interval_upper_bound,
            chr.data_release_year,
            chr.fipscode
        FROM county_health_rankings AS chr
        INNER JOIN zip_county AS zc
            ON zc.zip = :zip
           AND (
               (chr.fipscode IS NOT NULL AND chr.fipscode = zc.county_code)
               OR (chr.county = zc.county AND chr.state = zc.state_abbreviation)
           )
        WHERE chr.measure_name = :measure
        ORDER BY chr.data_release_year ASC, chr.year_span ASC
    """

    with get_connection() as connection:
        rows = connection.execute(query, {"zip": zip_code, "measure": measure_name}).fetchall()

    return [dict(row) for row in rows]


@APP.errorhandler(HTTPException)
def handle_http_exception(error: HTTPException) -> Response:
    """Return JSON error payloads for HTTPException instances."""
    description = error.description or HTTPStatus(error.code).phrase if error.code else "Unknown error"

    # werkzeug attaches Response on some exceptions (e.g., IM_A_TEAPOT) - reuse it.
    if error.response is None:
        response = jsonify({"error": description})
        response.status_code = error.code or HTTPStatus.INTERNAL_SERVER_ERROR
        return response

    error.response.set_data(json.dumps({"error": description}))
    error.response.mimetype = "application/json"
    return error.response


@APP.errorhandler(Exception)
def handle_unexpected_exception(error: Exception) -> Response:
    """Catch-all error handler that surfaces a JSON response."""
    response = jsonify({"error": str(error) or "Internal server error"})
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


@APP.route("/county_data", methods=["POST"])
def county_data() -> Response:
    """Return health ranking records for a given ZIP code and measure."""
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequest(description="Request body must be JSON")

    if payload.get("coffee") == "teapot":
        response = jsonify({"error": "Request rejected: I'm a teapot."})
        response.status_code = HTTPStatus.IM_A_TEAPOT
        return response

    validated = validate_payload(payload)
    records = lookup_county_data(validated["zip"], validated["measure_name"])

    if not records:
        raise NotFound(description="No matching records found")

    return jsonify(records)


@APP.route("/")
def index() -> Response:
    """Render a minimal UI that lets users query the API."""
    return render_template("index.html", measures=sorted(ALLOWED_MEASURES))


# Expose an alternate path that matches Vercel's default function routing (/api/*).
APP.add_url_rule("/api/county_data", view_func=county_data, methods=["POST"])


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8000, debug=True)


# Alias used by Vercel Python runtime
app = APP

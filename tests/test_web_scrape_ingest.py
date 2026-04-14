"""
Tests for web_scrape_ingest.py — covers parsing helpers and schema
compatibility with normalize_source_data(), without making any network calls.
"""

from __future__ import annotations

import os
import unittest.mock

import pytest

from src.web_scrape_ingest import _parse_duration, _parse_release_year, _lastfm_artist_slug
from src.normalize import normalize_source_data


# ---------------------------------------------------------------------------
# _parse_duration
# ---------------------------------------------------------------------------


def test_parse_duration_mm_ss():
    assert _parse_duration("3:42") == (3 * 60 + 42) * 1000


def test_parse_duration_single_digit_minutes():
    assert _parse_duration("0:45") == 45 * 1000


def test_parse_duration_long_track():
    assert _parse_duration("10:05") == (10 * 60 + 5) * 1000


def test_parse_duration_m_s_format():
    assert _parse_duration("3m 42s") == (3 * 60 + 42) * 1000


def test_parse_duration_m_s_no_space():
    assert _parse_duration("3m42s") == (3 * 60 + 42) * 1000


def test_parse_duration_none():
    assert _parse_duration(None) is None


def test_parse_duration_empty():
    assert _parse_duration("") is None


def test_parse_duration_invalid():
    assert _parse_duration("unknown") is None


# ---------------------------------------------------------------------------
# _parse_release_year
# ---------------------------------------------------------------------------


def test_parse_release_year_four_digits():
    assert _parse_release_year("2023") == "2023"


def test_parse_release_year_with_text():
    assert _parse_release_year("Released 2019") == "2019"


def test_parse_release_year_full_date():
    assert _parse_release_year("15 Jun 2021") == "2021"


def test_parse_release_year_none():
    assert _parse_release_year(None) is None


def test_parse_release_year_no_year():
    assert _parse_release_year("no date available") is None


# ---------------------------------------------------------------------------
# _lastfm_artist_slug
# ---------------------------------------------------------------------------


def test_lastfm_artist_slug_derived():
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LASTFM_ARTIST_URL", None)
        slug = _lastfm_artist_slug("Ashwin Azer")
    assert slug == "Ashwin+Azer"


def test_lastfm_artist_slug_special_chars():
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("LASTFM_ARTIST_URL", None)
        slug = _lastfm_artist_slug("AC/DC")
    assert "/" not in slug


def test_lastfm_artist_slug_full_url_override():
    env = {"LASTFM_ARTIST_URL": "https://www.last.fm/music/Ashwin+Azer"}
    with unittest.mock.patch.dict(os.environ, env):
        slug = _lastfm_artist_slug("Ashwin Azer")
    assert slug == "Ashwin+Azer"


def test_lastfm_artist_slug_raw_override():
    env = {"LASTFM_ARTIST_URL": "My+Artist"}
    with unittest.mock.patch.dict(os.environ, env):
        slug = _lastfm_artist_slug("Anything")
    assert slug == "My+Artist"


# ---------------------------------------------------------------------------
# Schema compatibility: normalize_source_data() with web_scrape input
# ---------------------------------------------------------------------------


def _sample_web_scrape_data() -> dict:
    return {
        "source": "web_scrape",
        "artist": {
            "id": "Ashwin+Azer",
            "name": "Ashwin Azer",
            "genres": ["indie pop"],
            "url": "https://www.last.fm/music/Ashwin+Azer",
        },
        "discography": [
            {
                "id": "some-album",
                "title": "Some Album",
                "type": "Album",
                "release_date": "2021",
                "release_date_precision": "year",
                "total_tracks": 2,
                "label": None,
                "upc": None,
                "url": "https://www.last.fm/music/Ashwin+Azer/Some+Album",
                "tracks": [
                    {
                        "id": "some-album_1",
                        "title": "Track One",
                        "track_number": 1,
                        "disc_number": 1,
                        "duration_ms": 213000,
                        "isrc": None,
                        "url": "https://www.last.fm/music/Ashwin+Azer/Some+Album",
                    },
                    {
                        "id": "some-album_2",
                        "title": "Track Two",
                        "track_number": 2,
                        "disc_number": 1,
                        "duration_ms": 185000,
                        "isrc": None,
                        "url": "https://www.last.fm/music/Ashwin+Azer/Some+Album",
                    },
                ],
            }
        ],
    }


def test_normalize_web_scrape_source():
    result = normalize_source_data(_sample_web_scrape_data())
    assert result["source"] == "web_scrape"


def test_normalize_web_scrape_artist_name():
    result = normalize_source_data(_sample_web_scrape_data())
    assert result["artist"]["name"] == "Ashwin Azer"


def test_normalize_web_scrape_artist_url_preserved():
    """normalize_artist() should carry the Last.fm URL through via the url fallback."""
    result = normalize_source_data(_sample_web_scrape_data())
    assert result["artist"]["url"] == "https://www.last.fm/music/Ashwin+Azer"


def test_normalize_web_scrape_release_url_preserved():
    result = normalize_source_data(_sample_web_scrape_data())
    release = result["releases"][0]
    assert release["url"] == "https://www.last.fm/music/Ashwin+Azer/Some+Album"


def test_normalize_web_scrape_release_count():
    result = normalize_source_data(_sample_web_scrape_data())
    assert len(result["releases"]) == 1


def test_normalize_web_scrape_track_url_preserved():
    result = normalize_source_data(_sample_web_scrape_data())
    track = result["releases"][0]["tracks"][0]
    assert track["url"] == "https://www.last.fm/music/Ashwin+Azer/Some+Album"


def test_normalize_web_scrape_release_date_year_only():
    result = normalize_source_data(_sample_web_scrape_data())
    release = result["releases"][0]
    assert release["release_date"]["year"] == "2021"
    assert release["release_date"]["month"] is None


def test_normalize_web_scrape_null_isrc():
    result = normalize_source_data(_sample_web_scrape_data())
    track = result["releases"][0]["tracks"][0]
    assert track["isrc"] is None

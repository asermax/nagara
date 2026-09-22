import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# Isolate DB + audio dir BEFORE app modules import (config/db bind at import time).
_tmp = tempfile.mkdtemp(prefix="nagara-test-")
os.environ["NAGARA_DATA_DIR"] = _tmp
os.environ["NAGARA_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["NAGARA_API_KEY"] = "test-key"
# The suite must not inherit a configured Access pair from the developer's .env: invariant
# 6's not-configured paths are only reachable when both halves are unset, and env vars
# take precedence over pydantic-settings' env_file, so pinning them empty wins.
os.environ["NAGARA_CF_ACCESS_CLIENT_ID"] = ""
os.environ["NAGARA_CF_ACCESS_CLIENT_SECRET"] = ""

from app.config import settings  # noqa: E402
from app.helpers import now_iso  # noqa: E402
from app.models import init_db  # noqa: E402
from app.service.fetch import FetchedPage  # noqa: E402
from app.service.storage import audio, base, image  # noqa: E402

init_db()

# The extraction boundary keys its cassette interactions on the job id, which is the
# item id — random per run. These matchers normalize itm_ ids on both sides of the
# comparison (keeping any -N retry suffix, so a reminted id never collapses onto the id
# it replaced), which makes a fabricated cassette replay against any id a run mints.
# The same normalization on firecrawl and gemini bodies is a no-op: no other request
# carries an itm_ id.
_ITEM_ID = re.compile(rb"itm_[0-9a-f]{8}")


def _item_normalized_path(r1, r2) -> bool:
    return _ITEM_ID.sub(b"itm_fixed", r1.path.encode()) == _ITEM_ID.sub(b"itm_fixed", r2.path.encode())


def _item_normalized_body(r1, r2) -> bool:
    return _ITEM_ID.sub(b"itm_fixed", r1.body or b"") == _ITEM_ID.sub(b"itm_fixed", r2.body or b"")


def pytest_recording_configure(config, vcr):
    vcr.register_matcher("item_normalized_path", _item_normalized_path)
    vcr.register_matcher("item_normalized_body", _item_normalized_body)


@pytest.fixture
def extraction_service(monkeypatch):
    """Point the extraction client at the fabricated-cassette host and give firecrawl a
    replay key, so every extraction-boundary test speaks to the same fake service.

    A test overrides either setting by patching it again in its own body — the later
    write wins for the test's duration, and both unwind on teardown.
    """
    monkeypatch.setattr(settings, "cloudflare_extraction_url", "https://extraction.test")
    monkeypatch.setattr(settings, "firecrawl_api_key", "replay-key")


@pytest.fixture
def seed_recipe():
    """Seed version 1 of a domain's recipe, returning the row id.

    The test database is one sqlite per session, so a second seed of the same domain
    reuses the row it already has rather than violating the (domain, version) pair.
    """

    def _seed(domain: str = "example.test", script: str = "// seeded script v1") -> str:
        with sqlite3.connect(str(Path(os.environ["NAGARA_DATA_DIR"]) / "test.db")) as conn:
            existing = conn.execute(
                "SELECT id FROM recipe_versions WHERE domain = ? AND version = 1", (domain,)
            ).fetchone()
            if existing is not None:
                return existing[0]
            recipe_id = "rcp_" + uuid.uuid4().hex[:8]
            conn.execute(
                "INSERT INTO recipe_versions (id, domain, version, script, created_at) VALUES (?, ?, 1, ?, ?)",
                (recipe_id, domain, script, now_iso()),
            )
            conn.commit()
        return recipe_id

    return _seed


def _fetcher_returning(html: str):
    class _StubFetcher:
        def __init__(self, *_args):
            pass

        def fetch(self, url):
            return FetchedPage(html=html, url=url, source="firecrawl")

    return _StubFetcher


@pytest.fixture
def stub_fetcher():
    """A fetcher class standing in for FirecrawlFetcher, returning fixed HTML."""
    return _fetcher_returning


@pytest.fixture
def stub_enqueue():
    """Patch the enqueue path's two remote calls as one: the firecrawl fetch returns
    fixed HTML and the extraction spawn is accepted.

    Tests that need the mock object itself, or a failing fetch or spawn, patch the two
    seams explicitly instead.
    """

    @contextmanager
    def _stub(html: str = "<html></html>", *, spawn: bool = True):
        with (
            patch("app.service.pipeline.steps.FirecrawlFetcher", _fetcher_returning(html)),
            patch("app.service.pipeline.steps.spawn_extraction", new_callable=AsyncMock, return_value=spawn),
        ):
            yield

    return _stub


@pytest.fixture(scope="session")
def vcr_config():
    # One central place governs every cassette, so there is no per-test opt-in to forget.
    # filter_headers: vcrpy records request headers verbatim into the committed YAML, so
    # credentials must be scrubbed here or they leak — this repo has cleaned a leaked key
    # out of its history once already. The Cloudflare Access pair joins the auth headers
    # for the same reason: a recorded spawn with Access enabled would otherwise commit
    # the service's credentials.
    # match_on adds body: every later POST endpoint (firecrawl /v2/scrape, the describer,
    # the extraction spawn) is one URL called with a different body per item, so
    # method+URL matching collapses every article onto one cassette entry and replays
    # the first recorded response for all of them. The path and body matchers are the
    # itm_-normalizing pair registered above, so extraction cassettes replay regardless
    # of the item ids a run mints.
    return {
        "filter_headers": [
            "authorization",
            "x-api-key",
            "x-goog-api-key",
            "cf-access-client-id",
            "cf-access-client-secret",
        ],
        "match_on": [
            "method",
            "scheme",
            "host",
            "port",
            "item_normalized_path",
            "query",
            "item_normalized_body",
        ],
    }


@pytest.fixture
def bucket_settings(monkeypatch):
    """Configure a bucket backend across every storage submodule that reads settings.

    The store classes read `settings` from their own module while the shared bucket client and
    the presigned-URL builder read it from `base`, so patching one namespace configures half
    the code path and leaves the other on the real settings. Returns the namespace so a test
    can assert against the same values.
    """

    def _configure(**overrides):
        values = SimpleNamespace(
            s3_configured=True,
            s3_endpoint="https://storage.railway.app",
            s3_bucket="nagara-audio",
            s3_access_key_id="k",
            s3_secret_access_key="s",
            s3_region="auto",
            s3_addressing_style="virtual",
            s3_url_ttl=3600,
            **overrides,
        )
        for module in (base, audio, image):
            monkeypatch.setattr(module, "settings", values)
        return values

    return _configure


@pytest.fixture(scope="session", autouse=True)
def _vcr_trafilatura_streaming_shim():
    # vcrpy's replay stub subclasses http.client.HTTPResponse, which lacks the release_conn
    # that trafilatura's streaming urllib3 fetch (preload_content=False then response.stream)
    # calls. The AttributeError is swallowed inside trafilatura and the fetch silently returns
    # None, so a cassette replays as "fetch: no response" instead of its recorded body. Give
    # the stub the no-op urllib3 would have provided. Applies session-wide so a later cassette
    # test cannot forget it — same reason filter_headers is centralized above.
    from vcr.stubs import VCRHTTPResponse

    if not hasattr(VCRHTTPResponse, "release_conn"):
        setattr(VCRHTTPResponse, "release_conn", lambda self: None)
    yield

import os
import tempfile
from types import SimpleNamespace

import pytest

# Isolate DB + audio dir BEFORE app modules import (config/db bind at import time).
_tmp = tempfile.mkdtemp(prefix="nagara-test-")
os.environ["NAGARA_DATA_DIR"] = _tmp
os.environ["NAGARA_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["NAGARA_API_KEY"] = "test-key"

from app.models import init_db  # noqa: E402
from app.service.storage import audio, base, image  # noqa: E402

init_db()


@pytest.fixture(scope="session")
def vcr_config():
    # One central place governs every cassette, so there is no per-test opt-in to forget.
    # filter_headers: vcrpy records request headers verbatim into the committed YAML, so
    # credentials must be scrubbed here or they leak — this repo has cleaned a leaked key
    # out of its history once already.
    # match_on adds body: every later POST endpoint (firecrawl /v2/scrape, the describer) is
    # one URL called with a different body per item, so method+URL matching collapses every
    # article onto one cassette entry and replays the first recorded response for all of them.
    return {
        "filter_headers": ["authorization", "x-api-key"],
        "match_on": ["method", "scheme", "host", "port", "path", "query", "body"],
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

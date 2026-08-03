import os
import tempfile

import pytest

# Isolate DB + audio dir BEFORE app modules import (config/db bind at import time).
_tmp = tempfile.mkdtemp(prefix="nagara-test-")
os.environ["NAGARA_DATA_DIR"] = _tmp
os.environ["NAGARA_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["NAGARA_API_KEY"] = "test-key"

from app.models import init_db  # noqa: E402

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

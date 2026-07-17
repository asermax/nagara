import os
import tempfile

# Isolate DB + audio dir BEFORE app modules import (config/db bind at import time).
_tmp = tempfile.mkdtemp(prefix="nagara-test-")
os.environ["NAGARA_DATA_DIR"] = _tmp
os.environ["NAGARA_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["NAGARA_API_KEY"] = "test-key"

from app.models import init_db  # noqa: E402

init_db()

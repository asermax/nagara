"""Recipe storage and domain matching (docs/technical-design/recipes.md).

The recipe store lives in the item database beside the items: one row per version of
one domain's script, the current version being the highest. A URL matches a recipe by
the host of the fetch's final URL with only a leading ``www`` dropped — subdomains are
distinct domains, and consolidation comes from redirects, which the fetch resolves.
"""

import urllib.parse
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..helpers import now_iso
from ..models.recipe import RecipeVersion


def domain_from_url(url: str) -> str:
    """The recipe key: the final host, leading www dropped."""
    host = urllib.parse.urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def _recipe_version_id() -> str:
    return "rcp_" + uuid.uuid4().hex[:8]


async def latest_recipe(db: AsyncSession, domain: str) -> RecipeVersion | None:
    """The domain's current recipe: the highest version, by the indexed descent."""
    result = await db.execute(
        select(RecipeVersion)
        .where(RecipeVersion.domain == domain)
        .order_by(RecipeVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def insert_recipe_version(db: AsyncSession, domain: str, script: str) -> RecipeVersion:
    """Stage the next version of a domain's recipe as a pure insert: version = max + 1.

    No commit — the row rides the caller's transaction — but the insert is flushed
    immediately, so it reaches the database ahead of the item write that points at
    it: with no mapped relationship between the models, a later autoflush orders
    the items UPDATE before this INSERT and Postgres rejects the pointer. The
    unique (domain, version) constraint keeps two concurrent completions from
    writing the same version: the loser's transaction fails wholesale, the item
    stays on its previous state, and the next poll re-resolves the job and
    re-inserts at the now-advanced max. A revision never updates a row, so
    nothing is lost by starting over."""
    # max() reads the one integer needed here; latest_recipe would hydrate the whole
    # script Text column for a row this insert never uses.
    result = await db.execute(
        select(func.max(RecipeVersion.version)).where(RecipeVersion.domain == domain)
    )
    version = (result.scalar() or 0) + 1
    row = RecipeVersion(
        id=_recipe_version_id(),
        domain=domain,
        version=version,
        script=script,
        created_at=now_iso(),
    )
    db.add(row)
    await db.flush()
    return row

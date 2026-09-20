"""Recipe storage and domain matching (docs/technical-design/recipes.md).

The recipe store lives in the item database beside the items: one row per version of
one domain's script, the current version being the highest. A URL matches a recipe by
the host of the fetch's final URL with only a leading ``www`` dropped — subdomains are
distinct domains, and consolidation comes from redirects, which the fetch resolves.
"""

import urllib.parse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..helpers import now_iso
from ..models.recipe import RecipeVersion, recipe_version_id


def domain_from_url(url: str) -> str:
    """The recipe key: the final host, leading www dropped."""
    host = urllib.parse.urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


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

    No flush — the row rides the caller's commit, so the unique (domain, version)
    constraint is what keeps two concurrent completions from writing the same version:
    the loser's transaction fails wholesale, the item stays on its previous state, and
    the next poll re-resolves the job and re-inserts at the now-advanced max. A revision
    never updates a row, so nothing is lost by starting over."""
    current = await latest_recipe(db, domain)
    version = (current.version + 1) if current is not None else 1
    row = RecipeVersion(
        id=recipe_version_id(),
        domain=domain,
        version=version,
        script=script,
        created_at=now_iso(),
    )
    db.add(row)
    return row

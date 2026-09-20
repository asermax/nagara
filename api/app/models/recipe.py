from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class RecipeVersion(Base):
    """One version of one domain's extraction recipe, in the item database.

    A revision is a pure insert that updates no row, and the current recipe for a domain
    is the highest version, so the per-article read is one indexed descent over the
    (domain, version) unique constraint. ``script`` carries the whole script with its
    declarations embedded, stored exactly as the authoring loop validated it, so a
    failing recipe reaches a revision prompt as one piece. Items point at the version
    whose script extracted them (or, after a spawn, the version they were spawned with)
    so a revision that made things worse traces to the items it touched.
    """

    __tablename__ = "recipe_versions"
    __table_args__ = (UniqueConstraint("domain", "version", name="uq_recipe_versions_domain_version"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    domain: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer)
    script: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)

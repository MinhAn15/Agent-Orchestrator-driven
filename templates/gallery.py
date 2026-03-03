"""Template Gallery (v0.5).

Provides a registry of reusable agent-orchestration templates that can be
loaded, searched, and rendered at runtime.

Each template is described by a :class:`TemplateSpec` and is backed by a
Markdown file in this directory (``templates/``).  The gallery auto-discovers
``.md`` files so adding a new template is as simple as dropping a file.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

_TEMPLATES_DIR = Path(__file__).parent


@dataclass
class TemplateSpec:
    """Metadata + content for a single orchestration template."""

    name: str
    slug: str  # filesystem stem, e.g. "incident-response"
    description: str
    tags: List[str] = field(default_factory=list)
    content: str = ""  # raw Markdown content

    def render(self, variables: Optional[Dict[str, str]] = None) -> str:
        """Return content with ``{{variable}}`` placeholders replaced.

        Args:
            variables: Mapping of placeholder name -> value.

        Returns:
            Rendered template string.
        """
        text = self.content
        for key, val in (variables or {}).items():
            text = text.replace(f"{{{{{key}}}}}", val)
        return text

    def matches(self, query: str) -> bool:
        """Case-insensitive search across name, description, and tags."""
        q = query.lower()
        return (
            q in self.name.lower()
            or q in self.description.lower()
            or any(q in t.lower() for t in self.tags)
        )


# ---------------------------------------------------------------------------
# Built-in template metadata (description + tags)
# ---------------------------------------------------------------------------

_METADATA: Dict[str, Dict] = {
    "incident-response": {
        "description": "End-to-end agent workflow for triaging and resolving production incidents.",
        "tags": ["ops", "incident", "sre"],
    },
    "bug-triage": {
        "description": "Automated bug classification and routing to the responsible team.",
        "tags": ["engineering", "qa", "bugs"],
    },
    "customer-support": {
        "description": "Multi-step support flow: classify intent, retrieve docs, escalate if needed.",
        "tags": ["support", "cx", "helpdesk"],
    },
    "content-ops": {
        "description": "Content pipeline: research, draft, review, and publish with human-in-the-loop.",
        "tags": ["content", "marketing", "editorial"],
    },
    "lead-enrichment": {
        "description": "Enrich CRM leads by querying external APIs and scoring fit.",
        "tags": ["sales", "crm", "enrichment"],
    },
}


class TemplateGallery:
    """In-memory gallery of orchestration templates.

    Usage::

        gallery = TemplateGallery.load()
        tmpl = gallery.get("incident-response")
        rendered = tmpl.render({"team": "Platform", "severity": "P1"})
    """

    def __init__(self, templates: Optional[List[TemplateSpec]] = None) -> None:
        self._store: Dict[str, TemplateSpec] = {}
        for t in templates or []:
            self._store[t.slug] = t

    # ------------------------------------------------------------------
    # Class-level factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "TemplateGallery":
        """Discover and load all ``.md`` files in *directory*.

        Falls back to the ``templates/`` directory next to this file.
        """
        base = directory or _TEMPLATES_DIR
        specs: List[TemplateSpec] = []
        for md_file in sorted(base.glob("*.md")):
            slug = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            meta = _METADATA.get(slug, {})
            # Try to extract first-line description from Markdown if not in registry
            description = meta.get("description") or _extract_description(content)
            specs.append(
                TemplateSpec(
                    name=_slug_to_title(slug),
                    slug=slug,
                    description=description,
                    tags=meta.get("tags", []),
                    content=content,
                )
            )
        return cls(specs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, slug: str) -> TemplateSpec:
        """Return template by slug; raises :class:`KeyError` if not found."""
        try:
            return self._store[slug]
        except KeyError:
            raise KeyError(f"Template '{slug}' not found. Available: {self.slugs()}")

    def search(self, query: str) -> List[TemplateSpec]:
        """Return templates whose name/description/tags match *query*."""
        return [t for t in self._store.values() if t.matches(query)]

    def list_all(self) -> List[TemplateSpec]:
        """Return all templates sorted by name."""
        return sorted(self._store.values(), key=lambda t: t.name)

    def slugs(self) -> List[str]:
        return sorted(self._store.keys())

    def register(self, spec: TemplateSpec) -> None:
        """Register a new template (or overwrite an existing one)."""
        self._store[spec.slug] = spec

    def __len__(self) -> int:
        return len(self._store)

    def __iter__(self) -> Iterable[TemplateSpec]:
        return iter(self._store.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug_to_title(slug: str) -> str:
    """Convert 'incident-response' -> 'Incident Response'."""
    return slug.replace("-", " ").replace("_", " ").title()


def _extract_description(markdown: str) -> str:
    """Pull the first non-heading paragraph from Markdown as a description."""
    for line in markdown.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return re.sub(r"[*_`]+", "", line)[:200]
    return ""


# Convenience singleton
_gallery: Optional[TemplateGallery] = None


def get_gallery() -> TemplateGallery:
    """Return (and lazily initialise) the module-level gallery singleton."""
    global _gallery
    if _gallery is None:
        _gallery = TemplateGallery.load()
    return _gallery

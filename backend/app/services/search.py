"""Global search across the research record.

Deterministic keyword matching only — deliberately no embeddings, no vector
store and no LLM in the MVP. Results always name the entity type and the
project so a reader can tell two similar hits apart.
"""

import re

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    BusinessAction,
    Decision,
    Evidence,
    Insight,
    Interview,
    Participant,
    ResearchProject,
)
from app.schemas.dashboard import SearchGroup, SearchResponse, SearchResult

TYPE_LABELS = {
    "project": "Research projects",
    "participant": "Participants",
    "interview": "Interviews",
    "evidence": "Evidence",
    "insight": "Insights",
    "decision": "Decisions",
    "action": "Actions",
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "were",
    "why", "how", "what", "do", "does", "did", "we", "our", "us", "it", "this", "that", "with",
}


def _snippet(text: str | None, query: str, width: int = 160) -> str:
    if not text:
        return ""
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= width:
        return flat
    lower = flat.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return flat[:width].rstrip() + "…"
    start = max(idx - 50, 0)
    end = min(start + width, len(flat))
    return ("…" if start else "") + flat[start:end].rstrip() + ("…" if end < len(flat) else "")


def _like(column, term: str):
    return func.lower(column).like(f"%{term.lower()}%")


def _match(columns: list, query: str):
    """All meaningful words of the query must appear across the columns.

    Deterministic and explainable: no stemming, no fuzzy scoring, no vectors.
    Filler words are dropped because requiring "why" and "are" to appear would
    make a natural-language query return nothing.
    """
    words = re.split(r"[^a-z0-9]+", query.lower())
    terms = [t for t in words if len(t) >= 2 and t not in STOPWORDS]
    if not terms:
        # A query made only of filler words (or punctuation) still searches literally.
        terms = [t for t in words if t] or [query.lower()]
    return and_(*[or_(*[_like(column, term) for column in columns]) for term in terms])


def search(db: Session, query: str, types: list[str] | None = None, limit: int = 8) -> SearchResponse:
    term = (query or "").strip()
    if len(term) < 2:
        return SearchResponse(query=term, total=0, groups=[], suggestions=[])

    selected = set(types or TYPE_LABELS.keys())
    results: dict[str, list[SearchResult]] = {key: [] for key in TYPE_LABELS}

    if "project" in selected:
        for p in db.execute(
            select(ResearchProject)
            .where(_match([ResearchProject.name, ResearchProject.objective, ResearchProject.description], term))
            .limit(limit)
        ).scalars():
            results["project"].append(
                SearchResult(
                    id=p.id,
                    entity_type="project",
                    title=p.name,
                    subtitle=f"Research project · {p.status.replace('_', ' ')}",
                    snippet=_snippet(p.objective, term),
                    href=f"/projects/{p.id}",
                    badges=[p.status.replace("_", " ")],
                    project_id=p.id,
                )
            )

    if "participant" in selected:
        for p in db.execute(
            select(Participant)
            .where(_match([Participant.display_name, Participant.code, Participant.segment], term))
            .limit(limit)
        ).scalars():
            results["participant"].append(
                SearchResult(
                    id=p.id,
                    entity_type="participant",
                    title=p.display_name,
                    subtitle=f"Synthetic participant · {p.code} · {p.segment.replace('_', ' ')}",
                    snippet=f"{p.purchase_frequency or 'Purchase history not recorded'} · eligibility {p.eligibility}",
                    href=f"/participants/{p.id}",
                    badges=[p.segment.replace("_", " ")],
                )
            )

    if "interview" in selected:
        for i in db.execute(
            select(Interview)
            .where(_match([Interview.title, Interview.code, Interview.notes, Interview.summary], term))
            .limit(limit)
        ).scalars():
            project = db.get(ResearchProject, i.project_id)
            results["interview"].append(
                SearchResult(
                    id=i.id,
                    entity_type="interview",
                    title=f"{i.code} · {i.title}",
                    subtitle=f"Interview · {project.name if project else 'Unknown project'}",
                    snippet=_snippet(i.summary or i.objective, term),
                    href=f"/interviews/{i.id}",
                    badges=[i.status.replace("_", " ")],
                    project_id=i.project_id,
                )
            )

    if "evidence" in selected:
        for e in db.execute(
            select(Evidence)
            .where(_match([Evidence.content, Evidence.interpretation, Evidence.code], term))
            .limit(limit)
        ).scalars():
            project = db.get(ResearchProject, e.project_id)
            results["evidence"].append(
                SearchResult(
                    id=e.id,
                    entity_type="evidence",
                    title=f"{e.code} · {e.evidence_type.replace('_', ' ')}",
                    subtitle=f"Evidence · {project.name if project else 'Unknown project'}",
                    snippet=_snippet(e.content, term),
                    href=f"/evidence/{e.id}",
                    badges=[e.provenance_status],
                    project_id=e.project_id,
                )
            )

    if "insight" in selected:
        for ins in db.execute(
            select(Insight)
            .where(_match([Insight.title, Insight.summary, Insight.research_question, Insight.code], term))
            .limit(limit)
        ).scalars():
            project = db.get(ResearchProject, ins.project_id) if ins.project_id else None
            results["insight"].append(
                SearchResult(
                    id=ins.id,
                    entity_type="insight",
                    title=f"{ins.code} · {ins.title}",
                    subtitle=f"Insight · {project.name if project else 'No project linked'} · {ins.status.replace('_', ' ')}",
                    snippet=_snippet(ins.summary, term),
                    href=f"/insights/{ins.id}",
                    badges=[ins.status.replace("_", " "), f"{ins.confidence} confidence"],
                    project_id=ins.project_id,
                )
            )

    if "decision" in selected:
        for d in db.execute(
            select(Decision)
            .where(_match([Decision.title, Decision.problem_statement, Decision.description, Decision.code], term))
            .limit(limit)
        ).scalars():
            results["decision"].append(
                SearchResult(
                    id=d.id,
                    entity_type="decision",
                    title=f"{d.code} · {d.title}",
                    subtitle=f"Decision · {d.business_function.replace('_', ' ')} · {d.status.replace('_', ' ')}",
                    snippet=_snippet(d.problem_statement, term),
                    href=f"/decisions/{d.id}",
                    badges=[d.status.replace("_", " ")],
                    project_id=d.project_id,
                )
            )

    if "action" in selected:
        for a in db.execute(
            select(BusinessAction)
            .where(_match([BusinessAction.title, BusinessAction.description, BusinessAction.code], term))
            .limit(limit)
        ).scalars():
            results["action"].append(
                SearchResult(
                    id=a.id,
                    entity_type="action",
                    title=f"{a.code} · {a.title}",
                    subtitle=f"Action · {a.status.replace('_', ' ')} · due {a.due_date or 'not set'}",
                    snippet=_snippet(a.description, term),
                    href=f"/actions?focus={a.id}",
                    badges=[a.status.replace("_", " ")],
                )
            )

    groups = [
        SearchGroup(entity_type=key, label=TYPE_LABELS[key], items=items)
        for key, items in results.items()
        if items
    ]
    total = sum(len(g.items) for g in groups)

    suggestions, reason = suggest_related(db, term)
    return SearchResponse(query=term, total=total, groups=groups, suggestions=suggestions, suggestion_reason=reason)


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def suggest_related(db: Session, term: str, limit: int = 4) -> tuple[list[SearchResult], str | None]:
    """Deterministic related-research suggestions based on shared keywords."""
    tokens = keywords(term)
    if not tokens:
        return [], None

    scored: list[tuple[int, SearchResult]] = []
    for insight in db.execute(select(Insight)).scalars():
        corpus = " ".join(
            [insight.title, insight.summary, insight.research_question or "", " ".join(insight.segments or [])]
        )
        overlap = tokens & keywords(corpus)
        if overlap:
            scored.append(
                (
                    len(overlap),
                    SearchResult(
                        id=insight.id,
                        entity_type="insight",
                        title=insight.title,
                        subtitle=f"Existing insight · {insight.status.replace('_', ' ')}",
                        snippet=f"Shares: {', '.join(sorted(overlap))}",
                        href=f"/insights/{insight.id}",
                        badges=["related research"],
                        project_id=insight.project_id,
                    ),
                )
            )

    for project in db.execute(select(ResearchProject)).scalars():
        corpus = " ".join([project.name, project.objective, " ".join(project.target_segments or [])])
        overlap = tokens & keywords(corpus)
        if overlap and not any(s.id == project.id for _, s in scored):
            scored.append(
                (
                    len(overlap),
                    SearchResult(
                        id=project.id,
                        entity_type="project",
                        title=project.name,
                        subtitle=f"Existing project · {project.status.replace('_', ' ')}",
                        snippet=f"Shares: {', '.join(sorted(overlap))}",
                        href=f"/projects/{project.id}",
                        badges=["related research"],
                        project_id=project.id,
                    ),
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    suggestions = [item[1] for item in scored[:limit]]
    reason = (
        "Related work already in the library, matched on shared keywords. Check it before commissioning new outreach."
        if suggestions
        else None
    )
    return suggestions, reason

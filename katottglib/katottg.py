"""Search over the KATOTTG codifier."""

from difflib import SequenceMatcher
import re

import pandas as pd

from katottglib.data import (
    CATEGORIES,
    SETTLEMENT_CATEGORIES,
    TOP_LEVEL_CATEGORIES,
    children_index,
    load_data,
    normalize,
    normalize_query,
    position_index,
)
from katottglib.entity import KatottgEntity

__all__ = [
    "find_by_name",
    "find_by_id",
    "find_children",
    "find_settlements",
    "find_top_level",
]

#: Below this similarity a fuzzy hit is noise rather than a suggestion.
DEFAULT_MIN_SIMILARITY = 0.6

_EXACT, _PREFIX, _WORD, _CONTAINS, _FUZZY = 0, 1, 2, 3, 4

#: A word of the name starting with the query: "Поляна" should find
#: "Червона Поляна" ahead of a name that merely contains those letters.
_WORD_BOUNDARY = r"(?:^|[\s\-'])"

_CATEGORY_BY_NAME = {normalize(name): code for code, name in CATEGORIES.items()}


def find_by_name(
    name: str,
    *,
    parent_id: str = None,
    category=None,
    limit: int = 5,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[KatottgEntity]:
    """
    Find codifier objects by name.

    :param name: name to search; an empty name lists the candidates
    :param parent_id: keep only descendants of this object, it excluded
    :param category: one code, several codes, a comma separated string,
        or a category name ('O', ('O', 'K'), 'O,K', 'Області та АРК')
    :param limit: maximum number of results
    :param min_similarity: similarity a fuzzy hit needs to be offered
    :return: KatottgEntity list, best match first
    """
    if limit <= 0:
        return []

    frame = load_data()
    candidates = _candidates(frame, parent_id, category)
    if candidates.empty:
        return []

    matches = _rank(candidates, normalize_query(name), limit, min_similarity)
    return _serialize(frame, matches)


def find_by_id(katottg_id: str) -> KatottgEntity | None:
    """Find one codifier object by its exact identifier."""
    frame = load_data()
    position = position_index(frame).get(katottg_id)
    if position is None:
        return None
    return _serialize(frame, frame.iloc[[position]])[0]


def find_children(
    parent_id: str,
    *,
    name: str = "",
    category=None,
    limit: int = 5,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[KatottgEntity]:
    """Descendants of ``parent_id``; the object itself is never returned."""
    return find_by_name(
        name,
        parent_id=parent_id,
        category=category,
        limit=limit,
        min_similarity=min_similarity,
    )


def find_top_level(
    name: str = "",
    *,
    limit: int = 30,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[KatottgEntity]:
    """
    The 27 objects a region picker must offer: 24 oblasts, Crimea, and
    the two cities with special status.
    """
    return find_by_name(
        name,
        category=TOP_LEVEL_CATEGORIES,
        limit=limit,
        min_similarity=min_similarity,
    )


def find_settlements(
    name: str = "",
    *,
    parent_id: str = None,
    limit: int = 15,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> list[KatottgEntity]:
    """
    Places a person can say they live in: the two cities with special
    status, cities, urban-type settlements, settlements and villages.
    """
    return find_by_name(
        name,
        parent_id=parent_id,
        category=SETTLEMENT_CATEGORIES,
        limit=limit,
        min_similarity=min_similarity,
    )


def parse_categories(category) -> list[str] | None:
    """
    Accept a code, a name, a comma separated string or an iterable.

    ``None`` and a blank value mean "no filter". A value that names no
    known category returns an empty list, which matches nothing: asking
    for a category that does not exist must not quietly return
    everything.
    """
    if category is None:
        return None
    if isinstance(category, str):
        parts = [part.strip() for part in category.split(",")]
    else:
        parts = [str(part).strip() for part in category]

    parts = [part for part in parts if part]
    if not parts:
        return None

    codes = []
    for part in parts:
        if part in CATEGORIES:
            code = part
        else:
            code = _CATEGORY_BY_NAME.get(normalize(part))
        if code is not None and code not in codes:
            codes.append(code)
    return codes


def _candidates(frame, parent_id, category) -> pd.DataFrame:
    if parent_id is not None:
        positions = children_index(frame).get(parent_id)
        if not positions:
            return frame.iloc[0:0]
        candidates = frame.iloc[positions]
    else:
        candidates = frame

    codes = parse_categories(category)
    if codes is not None:
        candidates = candidates[candidates["category"].isin(codes)]
    return candidates


def _rank(candidates, query, limit, min_similarity) -> pd.DataFrame:
    if not query:
        ordered = candidates.sort_values(
            by=["category_order", "sort_name", "id"]
        )
        return ordered.head(limit)

    names = candidates["search_name"]
    exact = names == query
    prefix = names.str.startswith(query) & ~exact
    word = (
        names.str.contains(_WORD_BOUNDARY + re.escape(query), regex=True)
        & ~prefix
        & ~exact
    )
    contains = names.str.contains(query, regex=False) & ~word & ~prefix & ~exact

    tier = pd.Series(_FUZZY, index=candidates.index, dtype="int8")
    tier[contains] = _CONTAINS
    tier[word] = _WORD
    tier[prefix] = _PREFIX
    tier[exact] = _EXACT

    matched = candidates[tier < _FUZZY].copy()
    matched["tier"] = tier[tier < _FUZZY]
    matched["similarity"] = 1.0

    #: Similarity is a fallback for a misspelling, not a filler for a
    #: short result list. Offering "Крива" to someone who typed "Київ"
    #: is how an oblast ends up in the settlement field.
    if matched.empty:
        matched = _fuzzy(candidates, query, limit, min_similarity)
    if matched.empty:
        return candidates.iloc[0:0]

    ordered = matched.sort_values(
        #: Within a tier the broader object comes first — a city before a
        #: village of the same name — then the name closest in length to
        #: the query, then a stable order.
        by=[
            "tier",
            "similarity",
            "category_order",
            "name_length",
            "sort_name",
            "id",
        ],
        ascending=[True, False, True, True, True, True],
    )
    return ordered.head(limit)


def _fuzzy(candidates, query, limit, min_similarity) -> pd.DataFrame:
    """
    Similarity pass over the candidates that open with the same two
    characters as the query. A typo in the opening is not worth scanning
    30k names, and without that anchor a four letter query such as
    "Київ" scores "Крива" above 0.6 purely on shared letters.
    """
    if candidates.empty or limit <= 0:
        return candidates.iloc[0:0]

    anchor = query[:2]
    narrowed = candidates[candidates["search_name"].str.startswith(anchor)]
    if narrowed.empty:
        return candidates.iloc[0:0]

    matcher = SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(query)

    scores = []
    for name in narrowed["search_name"]:
        matcher.set_seq1(name)
        if (
            matcher.real_quick_ratio() < min_similarity
            or matcher.quick_ratio() < min_similarity
        ):
            scores.append(0.0)
            continue
        scores.append(matcher.ratio())

    scored = narrowed.copy()
    scored["similarity"] = scores
    scored["tier"] = _FUZZY
    scored = scored[scored["similarity"] >= min_similarity]
    return scored.nlargest(limit, "similarity")


def _serialize(frame, matches) -> list[KatottgEntity]:
    positions = position_index(frame)
    results = []

    for row in matches.itertuples():
        entity = KatottgEntity(
            row.id, row.name, row.category_name, category_code=row.category
        )
        for ancestor_id in reversed(row.ancestors):
            position = positions.get(ancestor_id)
            if position is None:
                continue
            ancestor = frame.iloc[position]
            entity.add_parent(
                KatottgEntity(
                    ancestor["id"],
                    ancestor["name"],
                    ancestor["category_name"],
                    category_code=ancestor["category"],
                )
            )
        results.append(entity)

    return results

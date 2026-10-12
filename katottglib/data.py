"""Loading, normalising and indexing of the KATOTTG codifier."""

import os
import pickle
import re
import tempfile
import unicodedata

import pandas as pd

__all__ = [
    "CATEGORIES",
    "CATEGORY_ORDER",
    "TOP_LEVEL_CATEGORIES",
    "children_index",
    "load_data",
    "normalize",
    "normalize_query",
    "position_index",
    "reset_cache",
]

#: Category code -> human readable name, in the official hierarchy order.
CATEGORIES = {
    "O": "Області та АРК",
    "K": "Міста зі спеціальним статусом (Київ та Севастополь)",
    "P": "Райони в областях та в АРК",
    "H": "Територіальні громади",
    "M": "Міста",
    "T": "Селища міського типу",
    "C": "Села",
    "X": "Селища",
    "B": "Райони в містах",
}

#: Category code -> sort weight. Broader objects come first.
CATEGORY_ORDER = {code: i for i, code in enumerate(CATEGORIES)}

#: The real top level of the codifier: 24 oblasts + Crimea, and the two
#: cities with special status (Kyiv, Sevastopol). A region picker that
#: offers only "O" cannot represent Kyiv or Sevastopol.
TOP_LEVEL_CATEGORIES = ("O", "K")

LEVEL_COLUMNS = (
    "Перший рівень",
    "Другий рівень",
    "Третій рівень",
    "Четвертий рівень",
    "Додатковий рівень",
)
CATEGORY_COLUMN = "Категорія об’єкта"
NAME_COLUMN = "Назва об’єкта"

SOURCE_FILE = "kodifikator.xlsx"
CACHE_PREFIX = "katottglib-cache"
CACHE_DIR_ENV = "KATOTTGLIB_CACHE_DIR"

#: Bump whenever _prepare() changes the shape of the frame, so an
#: upgrade cannot be served a cache built by the previous release.
LAYOUT_VERSION = 3

#: Settlement type prefixes a person types but the codifier does not store.
_QUERY_PREFIXES = re.compile(
    r"^(м|с|смт|сщ|c|m)[\.\s]+",
    re.IGNORECASE,
)
_APOSTROPHES = str.maketrans({c: "'" for c in "’ʼ`´‘"})
_WHITESPACE = re.compile(r"\s+")

_frame = None


def normalize(value) -> str:
    """Casefold, unify apostrophes and collapse whitespace."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = text.translate(_APOSTROPHES).strip().casefold()
    return _WHITESPACE.sub(" ", text)


def normalize_query(value) -> str:
    """Normalise a user query and drop a leading settlement type."""
    return _QUERY_PREFIXES.sub("", normalize(value)).strip()


def _source_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), SOURCE_FILE)


def _cache_key() -> str:
    stat = os.stat(_source_path())
    return (
        f"{CACHE_PREFIX}-v{LAYOUT_VERSION}-{pd.__version__}"
        f"-{int(stat.st_mtime)}-{stat.st_size}.pkl"
    )


def _cache_directories() -> list[str]:
    """Writable directories to try, most specific first.

    The package directory is a last resort: it is often read only, and a
    cache written there outlives the install it belongs to.
    """
    directories = []
    override = os.environ.get(CACHE_DIR_ENV)
    if override:
        directories.append(override)
    directories.append(os.path.join(tempfile.gettempdir(), "katottglib"))
    directories.append(os.path.dirname(os.path.abspath(__file__)))
    return directories


def _cache_candidates() -> list[str]:
    key = _cache_key()
    return [os.path.join(d, key) for d in _cache_directories()]


def _purge_stale(current: str) -> None:
    """Remove cache files left by another data or pandas version."""
    for directory in _cache_directories():
        try:
            names = os.listdir(directory)
        except OSError:
            continue
        for name in names:
            if not name.startswith(CACHE_PREFIX) or not name.endswith(".pkl"):
                continue
            path = os.path.join(directory, name)
            if path == current:
                continue
            try:
                os.remove(path)
            except OSError:
                continue


def _read_cache() -> pd.DataFrame | None:
    for path in _cache_candidates():
        try:
            with open(path, "rb") as handle:
                return pickle.load(handle)
        except (OSError, pickle.PickleError, EOFError, AttributeError):
            continue
    return None


def _write_cache(frame: pd.DataFrame) -> None:
    for path in _cache_candidates():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                pickle.dump(frame, handle, protocol=pickle.HIGHEST_PROTOCOL)
            _purge_stale(path)
            return
        except (OSError, pickle.PickleError):
            continue


def _read_source() -> pd.DataFrame:
    """
    Read the workbook as the ministry publishes it.

    The published file carries a title block above the table and the odd
    trailing note below it, so the header row is located rather than
    assumed. A file that has already been trimmed reads just as well.
    """
    raw = pd.read_excel(_source_path(), header=None, dtype=str)
    header = _header_row(raw)
    if header is None:
        raise ValueError(
            f"{SOURCE_FILE}: no header row holding {LEVEL_COLUMNS[0]!r}"
        )

    frame = raw.iloc[header + 1 :].copy()
    frame.columns = [normalize(value) for value in raw.iloc[header]]
    frame = frame.rename(
        columns={
            normalize(column): column
            for column in (*LEVEL_COLUMNS, CATEGORY_COLUMN, NAME_COLUMN)
        }
    )

    missing = [
        column
        for column in (*LEVEL_COLUMNS, CATEGORY_COLUMN, NAME_COLUMN)
        if column not in frame.columns
    ]
    if missing:
        raise ValueError(f"{SOURCE_FILE} is missing columns: {missing}")

    frame = frame[frame[CATEGORY_COLUMN].isin(CATEGORIES)]
    frame = frame[frame[NAME_COLUMN].notna()]
    for column in (*LEVEL_COLUMNS, CATEGORY_COLUMN, NAME_COLUMN):
        frame[column] = frame[column].str.strip()
    return frame.reset_index(drop=True)


def _header_row(raw: pd.DataFrame) -> int | None:
    wanted = normalize(LEVEL_COLUMNS[0])
    for position in range(min(len(raw), 20)):
        if any(normalize(value) == wanted for value in raw.iloc[position]):
            return position
    return None


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    levels = frame[list(LEVEL_COLUMNS)]

    identifier = levels[LEVEL_COLUMNS[0]]
    for column in LEVEL_COLUMNS[1:]:
        identifier = levels[column].fillna(identifier)

    prepared = pd.DataFrame(
        {
            "id": identifier,
            "name": frame[NAME_COLUMN],
            "category": frame[CATEGORY_COLUMN],
        }
    )
    prepared["category_name"] = prepared["category"].map(CATEGORIES)
    prepared["category_order"] = (
        prepared["category"].map(CATEGORY_ORDER).fillna(len(CATEGORIES))
    )
    prepared["search_name"] = prepared["name"].map(normalize)
    prepared["name_length"] = prepared["name"].astype(str).str.len()
    #: Ancestors from the broadest down to the direct parent, self
    #: excluded. Levels repeat for objects such as Kyiv's districts,
    #: where levels 1..4 all hold the city id, so they are deduplicated.
    prepared["ancestors"] = [
        _ancestors(row, own_id)
        for row, own_id in zip(levels.to_numpy(), identifier)
    ]
    return prepared.reset_index(drop=True)


def _ancestors(levels, own_id) -> tuple:
    seen = []
    for value in levels:
        if not isinstance(value, str) or value == own_id or value in seen:
            continue
        seen.append(value)
    return tuple(seen)


def load_data() -> pd.DataFrame:
    """Return the prepared codifier frame, loading it at most once."""
    global _frame
    if _frame is None:
        frame = _read_cache()
        if frame is None:
            frame = _prepare(_read_source())
            _write_cache(frame)
        _frame = frame
    return _frame


def reset_cache() -> None:
    """Drop the in-process frame. Intended for tests."""
    global _frame
    _frame = None
    _position_index.cache_clear()
    _children_index.cache_clear()


def _build_position_index(frame: pd.DataFrame) -> dict[str, int]:
    return {
        identifier: position
        for position, identifier in enumerate(frame["id"])
        if isinstance(identifier, str)
    }


def _build_children_index(frame: pd.DataFrame) -> dict[str, list[int]]:
    index: dict[str, list[int]] = {}
    for position, ancestors in enumerate(frame["ancestors"]):
        for ancestor in ancestors:
            index.setdefault(ancestor, []).append(position)
    return index


class _Memo:
    """A tiny memo so the indexes follow whichever frame is loaded."""

    def __init__(self, builder):
        self._builder = builder
        self._frame_id = None
        self._value = None

    def __call__(self, frame):
        if self._frame_id != id(frame):
            self._value = self._builder(frame)
            self._frame_id = id(frame)
        return self._value

    def cache_clear(self):
        self._frame_id = None
        self._value = None


_position_index = _Memo(_build_position_index)
_children_index = _Memo(_build_children_index)


def position_index(frame: pd.DataFrame) -> dict[str, int]:
    """id -> row position, built once per frame."""
    return _position_index(frame)


def children_index(frame: pd.DataFrame) -> dict[str, list[int]]:
    """ancestor id -> row positions of its descendants, self excluded."""
    return _children_index(frame)

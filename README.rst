===========
KATOTTG lib
===========

Quick start
-----------

- Install with ``pip install katottglib``
- Import with ``import katottglib``

.. code-block:: python

    from katottglib import (
        find_by_id,
        find_by_name,
        find_children,
        find_top_level,
    )

    find_by_name("Львів")                     # best matches, any level
    find_by_name("Київ", category=("O", "K"))  # regions only
    find_by_id("UA80000000000093317")           # exact identifier
    find_children("UA32000000000030281", name="Бориспіль")
    find_top_level()                            # the 27 regions

Picking a region
................

The top level of the codifier is **not** category ``O`` alone. It is 24
oblasts plus Crimea (``O``) **and** the two cities with special status,
Kyiv and Sevastopol (``K``). A picker built on ``category="O"`` cannot
represent the capital, and the people who live there pick the
surrounding oblast instead. Use ``find_top_level()``, or pass both
categories.

Categories
..........

``katottglib.CATEGORIES`` maps every code to its name, in the official
order: ``O`` oblasts and Crimea, ``K`` cities with special status, ``P``
raions, ``H`` hromadas, ``M`` cities, ``T`` urban-type settlements, ``C``
villages, ``X`` settlements, ``B`` city districts. ``category`` accepts a
code, several codes, a comma separated string or a category name.

How a match is chosen
.....................

Candidates are filtered by ``parent_id`` and ``category``, then ranked:
exact name, name prefix, name substring, and only when none of those
matched, a similarity pass over names that open with the same two
characters. Similarity never pads a short result list — a query with no
plausible match returns nothing rather than the nearest noise. Queries
are matched case-insensitively, apostrophe forms (``'`` ``’`` ``ʼ``
``` ` ```) are equivalent, and a leading settlement type (``м.``, ``с.``,
``смт``) is ignored.

Caching
.......

The codifier is parsed once per process and cached on disk between runs,
keyed by the data file, the pandas version and the frame layout. Set
``KATOTTGLIB_CACHE_DIR`` to choose where; the system temporary directory
is used by default.

Release notes
-------------

v1.1.0 (2026-10-13)
...................

The pieces an address picker had to re-implement on top of 1.0.0.

Added

- ``find_settlements()`` — the places a person can say they live in: the
  two cities with special status, cities, urban-type settlements,
  settlements and villages. ``SETTLEMENT_CATEGORIES`` holds the codes.
- ``collation_key()`` — a sort key in Ukrainian alphabetical order.
  Unicode orders ``і`` after ``я``, which buries every ``Бі...`` name at
  the end of a plain sort.
- A word-start tier in the ranking, between prefix and substring:
  ``Збур'ївка`` reaches ``Нова Збур'ївка`` ahead of ``Новозбур'ївка``.
- ``normalize()`` and ``normalize_query()`` are exported. A caller that
  enforces a minimum query length needs the query the library will
  actually search for: ``normalize_query("м.")`` is empty, because the
  settlement type is not part of a name.

Changed

- Names are ordered with ``collation_key`` everywhere the library sorts
  them, so ``Білоцерківський`` precedes ``Бориспільський``.
- Within a tier the broader object now comes before the shorter name:
  ``Іва`` answers with Івано-Франківськ rather than the village Івахи.
  Unfiltered, ``Херсо`` answers with the oblast; ``find_settlements``
  answers the same query with the city.

v1.0.0 (2026-10-12)
...................

First stable release. Searching no longer invents results, and it is
two to three orders of magnitude faster. Anything built against 0.3.x
should expect different — correct — answers to the same calls.

Breaking

- Results are ranked differently, so a query can resolve to a different
  object: ``"Миколаївка"`` now gives the city, ``"Червона Поляна"`` a
  село rather than a селище. Anything that pinned a first result should
  be re-checked.
- ``limit`` is a cap, no longer a quota: a query is allowed to return
  fewer results, or none.
- A ``category`` naming no known code now matches nothing instead of
  silently returning the whole codifier.
- ``KatottgEntity`` gained a ``category_code`` attribute. Consumers that
  serialise ``__dict__`` — such as KSU24's ``AddressService`` — will see
  one new key.
- ``python_requires >= 3.10``.
- ``katottglib.test`` is gone from the installed package; the suite
  lives in ``tests/`` in the repository.

Fixed

- A parent matched its own ``parent_id`` filter, so an oblast was
  returned among the settlements of that oblast. Anything built on this
  offered "Київська" in a settlement field, and it was stored as one.
- ``find_by_id`` matched a **substring** of an identifier, so
  ``find_by_id("UA8")`` returned Kyiv. It is an exact match now.
- Ancestors are deduplicated: Kyiv repeats its own identifier across
  levels 1 to 4, which produced a four deep chain of "Київ" and four
  copies of every district.
- The intended category order was computed and then never used; results
  were sorted by the raw category letter descending, which put
  settlements above villages and villages above cities. An empty query
  returned ``X`` objects in reverse alphabetical order.
- Similarity had no threshold, so ``limit=100`` always returned 100 rows
  however little they resembled the query.

Added

- ``find_top_level()`` — the 27 objects a region picker must offer.
- ``find_children(parent_id, ...)`` — descendants, the object excluded.
- ``category`` accepts several codes: ``"O,K"``, ``("O", "K")``.
- ``katottglib.CATEGORIES`` and ``TOP_LEVEL_CATEGORIES`` are exported,
  so consumers stop re-declaring the mapping.
- ``KatottgEntity.category_code``, ``.parents``, ``.path``,
  ``.is_top_level``, equality and ``repr``.
- Query normalisation: case, apostrophe forms and a leading settlement
  type.

Data

- ``kodifikator.xlsx`` updated from the edition of 19.01.2024 to the one
  published as 07.07.2026 (наказ № 1321): 7 objects gone, 580 renamed,
  67 recategorised, 2 new cities, 31 744 objects in all. No identifier
  the tests pin was withdrawn.
- The workbook is now read as the ministry publishes it. Its title block
  and any trailing note are skipped, so updating means dropping the file
  in unedited.

Changed

- Ranking is exact, prefix, substring, then similarity, instead of a
  similarity score over every name. Some queries now return a different
  first result — ``"Миколаївка"`` resolves to the city, ``"Червона
  Поляна"`` to a village rather than a settlement.
- The disk cache moved out of the current working directory, is keyed by
  the data file and the frame layout, and prunes its own stale copies.
  ``kodifikator_data.pkl`` is no longer written next to whatever
  directory the process happened to start in.
- Loading happens once per process rather than once per call.
- ``python_requires >= 3.10``.
- Tests moved out of the installed package into ``tests/``.

v0.3.1 (2024-06-17)
...................

Unpin pandas and openpyxl versions - previous version was uninstallable if pandas 2.1 required.

v0.3.0 (2024-06-16)
...................

Update kodifikator.xlsx to 2024-01-19

v0.2.6 (2023-07-10)
...................

Try to fix continuation import errors on some installations.

v0.2.5 (2023-07-10)
...................

Fix import statements to be consistent.


v0.2.4 (2023-07-10)
...................

Fix installation by adding setup.py install_requires


v0.2.3 (2023-07-10)
...................

Fix installation by refining the structure

v0.2.2 (2023-07-10)
...................

Updated setup.py config


v0.2.1 (2023-07-09)
...................

Fixes and improvements to performance.

- data/kodifikator.xlsx is included into the dist.

v0.2.0 (2023-07-01)
...................

Fixes and improvements to performance.

- Dataframe is now persisted with Pickle.

v0.1.0 (2023-06-10)
...................

Initial release.

- Search by name with filter by level (``find_by_name``).
- Search by identifier (``find_by_id``)

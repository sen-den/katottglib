===========
KATOTTG lib
===========

Quick start
-----------

- Install with `pip install katottglib`
- Import `import katottglib`
- Search for entities with `find_by_name` `katottglib.find_by_name(name="Lviv")`

Release notes
-------------

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

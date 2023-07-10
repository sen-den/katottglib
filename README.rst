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

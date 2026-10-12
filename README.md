# koatuulib
KATOTTG (КАТОТТГ) lib for python

[Кодифікатор адміністративно-територіальних одиниць та територій територіальних громад](https://uk.wikipedia.org/wiki/Кодифікатор_адміністративно-територіальних_одиниць_та_територій_територіальних_громад)

# Update

The codifier is amended by order of the Ministry of Development several
times a year. The current edition and the whole history of them live on the
ministry's page:

- [Кодифікатор АТУ та територій територіальних громад](https://mininfra.gov.ua/diialnist/rozvytok-mistsevoho-samovriaduvannia/kodyfikator-administratyvno-terytorialnykh-odynyts-ta-terytorii-terytorialnykh-hromad)

Do not take it from `data.gov.ua`: that dataset has not been refreshed since
December 2021.

To update:

1. Download the newest `.xlsx` from the page above.
2. Replace `katottglib/kodifikator.xlsx` with it, exactly as published —
   the loader finds the header row itself and ignores the title block.
3. Run `make test` — the suite asserts against identifiers that must survive.
4. Note the edition date and the order number in the release notes.

The prepared frame is cached on disk, keyed by the data file, so replacing
the file is enough; no cache needs clearing. `KATOTTGLIB_CACHE_DIR` chooses
where that cache lives.

The file bundled with this release is the one published as the edition of
**07.07.2026** (наказ № 1321). Its own title block still cites наказ № 48 of
19.01.2024, which the ministry has not refreshed; the contents do differ from
that edition.

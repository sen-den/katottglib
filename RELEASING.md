# Releasing to PyPI

The version lives in exactly one place: `katottglib/__init__.py`
(`__version__`). `setup.cfg` reads it with `version = attr:`, so nothing else
needs editing.

## Once per machine

1. Create the API tokens. PyPI no longer accepts a username and password for
   uploads — it has to be a token.
   - <https://test.pypi.org/manage/account/token/>
   - <https://pypi.org/manage/account/token/>

   The first token for a brand new project has to be account-scoped, because
   the project does not exist yet. After the first upload, replace it with a
   token scoped to `katottglib` alone.

2. Put them in `~/.pypirc` (`%USERPROFILE%\.pypirc` on Windows), with the
   literal username `__token__`:

   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-...

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-...
   ```

   Make it readable only by you (`chmod 600 ~/.pypirc`).

3. Install the tooling:

   ```bash
   python -m pip install --upgrade build twine
   ```

## Every release

1. **Decide the version.** Semantic versioning: breaking change → major,
   new behaviour → minor, fix only → patch. Changing how a search ranks is
   a breaking change; a codifier data update usually is not, unless an
   identifier is withdrawn.

2. **Update `__version__`** in `katottglib/__init__.py` and add the release
   notes to the top of the `Release notes` section in `README.rst`. That file
   is the long description on the PyPI page, so what you write there is what
   people read.

3. **Check the tree is clean and the suite is green:**

   ```bash
   make format && make test && git status --porcelain
   ```

4. **Build, from an empty `dist/`:**

   ```bash
   rm -rf dist build *.egg-info && python -m build
   ```

   `dist/` must hold exactly two files, `katottglib-X.Y.Z.tar.gz` and
   `katottglib-X.Y.Z-py3-none-any.whl`. Stale artefacts from an earlier
   version are the classic way to upload the wrong thing: PyPI refuses to
   replace a file it already has, and the filename is all it goes by.

5. **Check the artefacts before anyone else sees them:**

   ```bash
   twine check dist/*
   python -c "import zipfile,glob; print(*sorted(zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist()), sep='\n')"
   ```

   `twine check` catches a long description that renders badly — the usual
   cause of a PyPI page that is a wall of raw reStructuredText. The listing
   must contain `katottglib/kodifikator.xlsx`, and must not contain `tests/`
   or any `.pkl`. The CI build job asserts the same thing.

6. **Upload to TestPyPI first** and install from there into a throwaway
   environment:

   ```bash
   twine upload --repository testpypi dist/*
   python -m venv /tmp/relcheck && /tmp/relcheck/bin/pip install \
       --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       katottglib==X.Y.Z
   /tmp/relcheck/bin/python -c "import katottglib; print(katottglib.__version__, len(katottglib.find_top_level()))"
   ```

   `--extra-index-url` is needed because pandas and openpyxl are not on
   TestPyPI. The smoke test must print the version and `27`.

7. **Upload to PyPI:**

   ```bash
   twine upload dist/*
   ```

8. **Tag and push:**

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin master --tags
   ```

## Things that go wrong

- **`File already exists`** — a version can only ever be uploaded once, and
  deleting a release does not free the filename. Bump the patch version and
  upload again. This is why TestPyPI goes first.
- **The data file is missing from the wheel** — `include_package_data` only
  ships what `MANIFEST.in` lists. `include katottglib/kodifikator.xlsx` must
  stay there, and step 5 is what catches it.
- **The PyPI page shows raw markup** — `long_description_content_type` must
  match `README.rst`, which is `text/x-rst`. `twine check` says so.
- **403 on upload** — the token is scoped to a project it cannot create, or
  `username` is not the literal `__token__`.
- **The sdist builds but the wheel is empty** — `[options.packages.find]`
  excludes `tests`; make sure a new top-level package is not excluded with it.

## Yanking

If a release turns out to be broken, do not delete it — that breaks anyone
who pinned it. Yank it on the PyPI project page: it stays installable for a
pin that names it exactly, and disappears from resolution for everyone else.

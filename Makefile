.DEFAULT_GOAL := pre_commit

pre_commit: format test

# Format
isort:
	isort .

black:
	black .

# Reformat all the code with project format rules
format: isort black

# Run the test suite
test:
	python -m unittest discover -s tests -t .

# Build the sdist and the wheel into dist/
build:
	python -m build

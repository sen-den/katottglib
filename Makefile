.DEFAULT_GOAL := pre_commit

pre_commit: format

# Format
isort:
	isort .

black:
	black .

# Reformat all the code with project format rules
format: isort black

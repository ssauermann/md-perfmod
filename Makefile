shell:
	python3 -m pipenv shell

install:
	python3 -m pipenv install -e .

test:
	python3 -m pytest tests

.PHONY: shell install test
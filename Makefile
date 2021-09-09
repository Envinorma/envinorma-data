.PHONY: clean build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

gen-docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/envinorma*.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ envinorma **/tests/
	$(MAKE) -C docs html

docs: ## generate Sphinx HTML documentation, including API docs, and serve to browser
	make gen-docs
	$(BROWSER) docs/_build/html/index.html

test:
	venv/bin/pytest --mypy-ignore-missing-imports


test-and-lint:
	make test
	venv/bin/flake8 --count --verbose --show-source --statistics
	venv/bin/black . --check -S -l 120
	venv/bin/isort . --profile black -l 120
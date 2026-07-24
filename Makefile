PYTHON ?= python3.13
UV ?= uv
VENV ?= .venv

TEST_REQUIREMENTS := requirements_test.txt
TEST_ENV_STAMP := $(VENV)/.test-requirements-installed

.PHONY: test
test: $(TEST_ENV_STAMP)
	$(VENV)/bin/python -m pytest tests

$(VENV)/bin/python:
	$(UV) venv --python $(PYTHON) $(VENV)

$(TEST_ENV_STAMP): $(TEST_REQUIREMENTS) $(VENV)/bin/python
	$(UV) pip install --python $(VENV)/bin/python --prerelease=allow -r $(TEST_REQUIREMENTS)
	touch $(TEST_ENV_STAMP)

PYTHON ?= .venv/bin/python
export PYTHONPATH := src

.PHONY: setup dev lock check tree smoke

setup:
	uv sync

dev:
	uv pip install --python $(PYTHON) pyyaml jsonschema pytest ruff

lock:
	uv lock

check:
	$(PYTHON) -m pytest -q

tree:
	$(PYTHON) scripts/check_tree.py

smoke:
	$(PYTHON) -m wikiwisata.experiments.harness \
		--config configs/experiments/b0_baseline.yaml --dry-run

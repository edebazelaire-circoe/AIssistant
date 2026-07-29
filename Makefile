.PHONY: install test run demo-workbook architecture package

install:
	python -m pip install -e ".[dev]" --no-build-isolation

test:
	pytest

architecture:
	python scripts/check_architecture.py

run:
	python -m jarvis_agent.web.api

demo-workbook:
	python scripts/create_demo_workbook.py

package:
	python scripts/package_release.py

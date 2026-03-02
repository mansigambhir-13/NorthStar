.PHONY: install test lint format run benchmark demo clean serve

install:
	pip install -e ".[dev,web]"

test:
	pytest tests/ -v

lint:
	ruff check northstar/ tests/
	mypy northstar/

format:
	ruff format northstar/ tests/
	ruff check --fix northstar/ tests/

run:
	northstar --help

benchmark:
	python benchmarks/run_demos.py --benchmark

demo:
	python benchmarks/run_demos.py --demo

serve:
	northstar serve

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

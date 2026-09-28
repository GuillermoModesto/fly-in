VENV        = .venv
PYTHON      = $(VENV)/bin/python
PIP         = $(VENV)/bin/pip
MAIN        = fly_in.py
<<<<<<< HEAD
MAP         = maps/01_linear_path.txt
=======
MAP         = maps/example.txt
>>>>>>> 45a99c5edc2fa3228068c074d2348e2b7d589709

MYPY_FLAGS  = --warn-return-any \
              --warn-unused-ignores \
              --ignore-missing-imports \
              --disallow-untyped-defs \
              --check-untyped-defs

.DEFAULT_GOAL := run
.PHONY: install run visual debug lint lint-strict clean fclean

$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -q flake8 mypy
	@echo "venv ready. Activate with: source $(VENV)/bin/activate"

install: $(VENV)/bin/python

run: $(VENV)/bin/python
	$(PYTHON) $(MAIN) $(MAP)

visual: $(VENV)/bin/python
	$(PYTHON) $(MAIN) --visual $(MAP)

debug: $(VENV)/bin/python
	$(PYTHON) -m pdb $(MAIN) $(MAP)

lint: $(VENV)/bin/python
	@fail=0; \
	$(VENV)/bin/flake8 . || fail=1; \
	$(VENV)/bin/mypy . $(MYPY_FLAGS) || fail=1; \
	exit $$fail

lint-strict: $(VENV)/bin/python
	@fail=0; \
	$(VENV)/bin/flake8 . || fail=1; \
	$(VENV)/bin/mypy . --strict || fail=1; \
	exit $$fail

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)

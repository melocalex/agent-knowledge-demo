PYTHON ?= python3

.PHONY: deps test test-invoicing lint check-skills

deps:
	@echo "No dependencies. Python 3.10+ standard library only."

test: test-invoicing
	$(PYTHON) -m unittest discover -s tests -v

test-invoicing:
	$(PYTHON) -m unittest discover -s services/invoicing/tests -v

lint:
	$(PYTHON) tools/check_agent_knowledge.py

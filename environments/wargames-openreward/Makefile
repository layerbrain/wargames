ifneq (,$(wildcard ../../local.env))
	include ../../local.env
	export
endif

.PHONY: prepublish conformance parity smoke-local

prepublish: parity conformance smoke-local

parity:
	cd ../.. && source venv/bin/activate && python -m unittest tests.harness tests.evaluation

conformance:
	cd ../.. && source venv/bin/activate && python -m unittest environments.wargames-openreward.tests.conformance

smoke-local:
	cd ../.. && source venv/bin/activate && python -m wargames tasks --game redalert --split debug

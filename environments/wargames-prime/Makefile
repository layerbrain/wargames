ifneq (,$(wildcard ../../local.env))
	include ../../local.env
	export
endif

.PHONY: publish parity conformance

publish: parity conformance
	@test -n "$$LAYERBRAIN_PRIME" || (echo "ERROR: LAYERBRAIN_PRIME not set" && exit 1)
	PRIME_API_KEY="$$LAYERBRAIN_PRIME" prime env push --team layerbrain --visibility PUBLIC

parity:
	cd ../.. && source venv/bin/activate && python -m unittest tests.harness tests.evaluation

conformance:
	cd ../.. && source venv/bin/activate && python -m unittest discover -s environments/wargames-prime/tests/conformance

ifneq (,$(wildcard ../../local.env))
	include ../../local.env
	export
endif

.PHONY: publish parity conformance source-archive

publish: parity conformance source-archive
	@test -n "$$LAYERBRAIN_PRIME" || (echo "ERROR: LAYERBRAIN_PRIME not set" && exit 1)
	PRIME_API_KEY="$$LAYERBRAIN_PRIME" prime env push --name wargames --team layerbrain --visibility PUBLIC --auto-bump

parity:
	cd ../.. && source venv/bin/activate && python -m unittest tests.harness tests.evaluation

conformance:
	cd ../.. && source venv/bin/activate && python -m unittest discover -s environments/prime/tests/conformance

source-archive:
	cd ../.. && source venv/bin/activate && python environments/prime/scripts/check_source_archive.py

ifneq (,$(wildcard ../../local.env))
	include ../../local.env
	export
endif

.PHONY: prepublish conformance parity smoke-local docker-build publish

prepublish: parity conformance smoke-local docker-build

parity:
	cd ../.. && source venv/bin/activate && python -m unittest tests.harness tests.evaluation

conformance:
	cd ../.. && source venv/bin/activate && python -m unittest discover -s environments/wargames-openreward/tests/conformance

smoke-local:
	cd ../.. && source venv/bin/activate && python -m wargames tasks --game redalert --split debug

docker-build:
	docker build --platform linux/amd64 -t wargames-openreward:local .

publish: prepublish
	@test -n "$$LAYERBRAIN_OPENREWARD" || (echo "ERROR: LAYERBRAIN_OPENREWARD not set" && exit 1)
	(cd ../.. && source venv/bin/activate && OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd get layerbrain/wargames >/dev/null 2>&1) || \
		(cd ../.. && source venv/bin/activate && OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd create wargames \
			--namespace layerbrain \
			--description "Defense-aligned Red Alert computer-use environment for RL and agent evaluation.")
	(cd ../.. && source venv/bin/activate && OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd link layerbrain/wargames layerbrain/wargames \
		--subdirectory environments/wargames-openreward \
		--cpu-memory 2:4 \
		--concurrency 20 \
		--max-scale 2) || \
	(cd ../.. && source venv/bin/activate && OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd update-link layerbrain/wargames \
		--subdirectory environments/wargames-openreward \
		--cpu-memory 2:4 \
		--concurrency 20 \
		--max-scale 2)

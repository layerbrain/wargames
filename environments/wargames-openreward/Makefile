ifneq (,$(wildcard ../../local.env))
	include ../../local.env
	export
endif

.PHONY: prepublish conformance parity smoke-local publish

prepublish: parity conformance smoke-local

parity:
	cd ../.. && source venv/bin/activate && python -m unittest tests.harness tests.evaluation

conformance:
	cd ../.. && source venv/bin/activate && python -m unittest discover -s environments/wargames-openreward/tests/conformance

smoke-local:
	cd ../.. && source venv/bin/activate && python -m wargames tasks --game redalert --split debug

publish: prepublish
	@test -n "$$LAYERBRAIN_OPENREWARD" || (echo "ERROR: LAYERBRAIN_OPENREWARD not set" && exit 1)
	OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd get layerbrain/WarGamesRedAlert >/dev/null 2>&1 || \
		OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd create WarGamesRedAlert \
			--namespace layerbrain \
			--description "Defense-aligned Red Alert computer-use environment for RL and agent evaluation."
	OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd link layerbrain/WarGamesRedAlert layerbrain/wargames \
		--subdirectory environments/wargames-openreward \
		--cpu-memory 2:4 \
		--concurrency 20 \
		--max-scale 2 || \
	OPENREWARD_API_KEY="$$LAYERBRAIN_OPENREWARD" orwd update-link layerbrain/WarGamesRedAlert \
		--subdirectory environments/wargames-openreward \
		--cpu-memory 2:4 \
		--concurrency 20 \
		--max-scale 2

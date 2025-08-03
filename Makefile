.PHONY: demo eval-defs eval-concepts eval-trouble perf dist sbom

demo:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite defs --dataset sample --json /tmp/defs.demo.json --repeats 1 --strict || true
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite concepts --dataset sample --json /tmp/concepts.demo.json --repeats 1 --strict || true
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite trouble --dataset sample --json /tmp/trouble.demo.json --repeats 1 --strict || true
	@python -c "import json,sys;from pathlib import Path;p=Path('/tmp');files=['defs.demo.json','concepts.demo.json','trouble.demo.json'];r=[json.loads((p/f).read_text()) for f in files];ok=all(x['counts']['total']>=1 for x in r);print('DEMO:', 'PASS' if ok else 'FAIL');sys.exit(0 if ok else 1)"

eval-defs:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite defs --dataset sample --json eval_defs.json --repeats 3 --strict

eval-concepts:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite concepts --dataset sample --json eval_concepts.json --repeats 3 --strict

eval-trouble:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite trouble --dataset sample --json eval_trouble.json --repeats 3 --strict

eval-defs-m1:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite defs --dataset m1 --json eval_defs_m1.json --repeats 3 --strict

eval-concepts-m1:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite concepts --dataset m1 --json eval_concepts_m1.json --repeats 3 --strict

eval-trouble-m1:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite trouble --dataset m1 --json eval_trouble_m1.json --repeats 3 --strict

eval-negatives-m1:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite negatives --dataset m1 --json eval_negatives_m1.json --repeats 3 --strict

eval-amb-m1:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite ambiguous --dataset m1 --json eval_amb_m1.json --repeats 3 --strict

docker-build:
	docker build -t aev2:local .

docker-run:
	docker compose up -d
	sleep 5
	curl -sf http://localhost:8001/healthz | jq .

perf-http:
	python scripts/perf_http.py --base http://localhost:8001 --total 30 --concurrency 4 --json perf_http.json --metrics

perf:
	AE_INDEX_DIR=$(PWD)/data/index ENABLE_DENSE=0 python -m ae2.eval.run --suite defs --dataset sample --json /tmp/perf_defs.json --repeats 10

ci-local:
	ENVIRONMENT=development DEBUG=true ENABLE_DENSE=0 AE_INDEX_DIR=$$(pwd)/data/index AE_BIND_PORT=8001 \
	./scripts/sync_rfc_min.sh && \
	python scripts/build_index.py && \
	pytest -q --maxfail=1 --disable-warnings -rA

dist:
	python -m build

sbom:
	cyclonedx-bom -o sbom.json .

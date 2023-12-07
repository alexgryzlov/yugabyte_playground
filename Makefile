DATA_DIR := $(shell pwd)/.yugabyte_data
DOCKER_COMPOSE := docker-compose -f "$(shell pwd)/docker/docker-compose.yml"
DOCKER_COMPOSE_TEST := docker-compose -f "$(shell pwd)/docker/docker-compose.test.yml"

.PHONY: start_local
start_local:
	yb-ctl start --replication_factor=1 --data_dir=${DATA_DIR} --tserver_flags "${TSERVER_FLAGS}"

.PHONY: destroy_local
destroy_local:
	yb-ctl destroy --data_dir=$(DATA_DIR)

.PHONY: start_docker
start_docker:
	${DOCKER_COMPOSE} up -d

.PHONY: down_docker
down_docker:
	${DOCKER_COMPOSE} down

.PHONY: destroy_docker
destroy_docker:
	${DOCKER_COMPOSE} down --remove-orphans --volumes
	sudo find ${DATA_DIR} -maxdepth 1 -name "yb-*" -exec rm -rf {} \;  

.PHONY: start_with_instrumentation
start_with_instrumentation:
	export TSERVER_FLAGS="-enable_rpc_dumps=true --ysql_log_statement=all ${TSERVER_FLAGS}" && export MASTER_FLAGS="-enable_rpc_dumps=true ${MASTER_FLAGS}" && ${DOCKER_COMPOSE_TEST} up -d

.PHONY: test
test:
	poetry run pytest tests

.PHONY: collect_test_rpcs
collect_test_rpcs: test
	poetry run sudo python3 yugabyte_playground/parse_logs.py 
	


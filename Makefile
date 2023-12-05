DATA_DIR := $(shell pwd)/.yugabyte_data
DOCKER_COMPOSE := docker-compose -f "$(shell pwd)/docker/docker-compose.test.yml"

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

.PHONY: test
test:
	poetry run pytest


DATA_DIR := $(shell pwd)/.yugabyte_data

.PHONY: start_cluster
start_cluster:
	yb-ctl start --replication_factor=3 --data_dir=$(DATA_DIR) --tserver_flags ysql_enable_packed_row=false

.PHONY: destroy
destroy:
	yb-ctl destroy --data_dir=$(DATA_DIR)
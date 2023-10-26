DATA_DIR := $(shell pwd)/.yugabyte_data

.PHONY: start_cluster
start_cluster:
	yb-ctl start --replication_factor=3 --data_dir=$(DATA_DIR) --tserver_flags ysql_enable_packed_row=false

.PHONY: start_cluster_log_docdb_writes
start_cluster_log_docdb_writes:
	yb-ctl start --replication_factor=3 --data_dir=$(DATA_DIR) --tserver_flags "ysql_enable_packed_row=false,TEST_docdb_log_write_batches=true"

.PHONY: destroy
destroy:
	yb-ctl destroy --data_dir=$(DATA_DIR)

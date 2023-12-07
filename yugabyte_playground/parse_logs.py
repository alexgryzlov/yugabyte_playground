import re
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

from pathlib import Path


@dataclass(frozen=True)
class PgStatement:
    timestamp: datetime
    statement: str


class RPCType(Enum):
    PROXY_REQUEST = 1
    PROXY_RESPONSE = 2
    UNKNOWN = 3


@dataclass
class RPCDump:
    type: RPCType
    uuid: str
    timestamp: datetime
    method: str
    payload: str


DATEFORMAT = "%H:%M:%S.%f"
PG_LOG_DIR = Path(".yugabyte_data/yb-tserver-n1/yb-data/tserver/logs")
TSERVER_LOG_PATH = Path(".yugabyte_data/yb-tserver-n1/yb-data/tserver/logs/yb-tserver.INFO")
MASTER_LOG_PATH = Path(".yugabyte_data/yb-master-n1/yb-data/master/logs/yb-master.INFO")


def get_pg_statements(log_path: str) -> list[PgStatement]:
    with open(log_path) as f:
        pg_log = f.read().split("\n")

    pg_statements: list[PgStatement] = []

    for line in pg_log:
        if "statement: " not in line:
            continue

        match = re.search(r"\d{2}:\d{2}:\d{2}\.\d{1,6}", line)
        if match is None:
            continue

        ts = datetime.strptime(match.group(), DATEFORMAT)
        statement = line.split("statement: ")[1]
        if len(statement) > 5:
            pg_statements.append(PgStatement(timestamp=ts, statement=statement))
    return pg_statements


def find_proxy_rpc(log_path: str, pg_statements: list[PgStatement], rpc_trace: dict[PgStatement, list[RPCDump]]):
    with open(log_path) as f:
        tserver_log = f.read().split("\n")

    pg_ptr = 0
    for line in tserver_log:
        match = re.search(r"\d{2}:\d{2}:\d{2}\.\d{1,6}", line)
        if match is None:
            continue

        ts = datetime.strptime(match.group(), DATEFORMAT)

        if ts < pg_statements[pg_ptr].timestamp:
            continue

        if pg_ptr + 1 < len(pg_statements) and pg_statements[pg_ptr + 1].timestamp <= ts:
            pg_ptr += 1

        type = RPCType.UNKNOWN
        if "[PROXY RESPONSE]" in line:
            type = RPCType.PROXY_RESPONSE
        elif "[PROXY REQUEST]" in line:
            type = RPCType.PROXY_REQUEST
        else:
            continue

        message = line.split("] ")[-1]
        match message.split(maxsplit=2):
            case [uuid, method, payload]:
                rpc_dump = RPCDump(type=type, timestamp=ts, uuid=uuid, method=method, payload=payload)
            case [uuid, method]:
                rpc_dump = RPCDump(type=type, timestamp=ts, uuid=uuid, method=method, payload="")
            case _:
                raise RuntimeError("Unexpected RPC dump line")

        if rpc_dump.method in [
            "yb.master.MasterService.TSHeartbeat",
            "yb.tserver.PgClientService.Heartbeat",
            "yb.consensus.ConsensusService.RunLeaderElection",
        ]:
            continue
        rpc_trace[pg_statements[pg_ptr]].append(rpc_dump)

def unite_related_responses(rpc_trace: dict[PgStatement, list[RPCDump]]) -> dict[PgStatement, list[RPCDump]]:
    uuid_to_statement: dict[str, PgStatement] = dict()
    for pg_statement, rpcs in rpc_trace.items():
        for rpc in rpcs:
            if rpc.type == RPCType.PROXY_REQUEST:
                uuid_to_statement[rpc.uuid] = pg_statement

    updated_trace: dict[PgStatement, list[RPCDump]] = defaultdict(list)

    for pg_statement, rpcs in rpc_trace.items():
        for rpc in rpcs:
            if rpc.uuid not in uuid_to_statement:
                continue
            updated_trace[uuid_to_statement[rpc.uuid]].append(rpc)

    return updated_trace

def replace_ids_with_names(master_log_path, rpc_trace: dict[PgStatement, list[RPCDump]]):
    table_names: dict[str, str] = {}

    with open(master_log_path) as f:
        master_log = f.read().split("\n")

    for line in master_log:
        table_name = re.search(r"table_name: \"([a-z0-9\.]+)\"", line)
        if table_name is not None:
            table_id = re.search(r"table_id: \"([a-z0-9]+)\"", line)
            assert table_id is not None

            table_names[table_id.group(1)] = table_name.group(1)

    for _, rpcs in rpc_trace.items():
        for rpc in rpcs:
            table_id = re.search(r"table_id: \"([a-z0-9]+)\"", rpc.payload)
            if table_id is not None and table_id.group(1) in table_names.keys():
                rpc.payload = re.sub(table_id.group(1), table_names[table_id.group(1)], rpc.payload)
                


if __name__ == "__main__":
    pg_statements: list[PgStatement] = []
    rpc_trace: dict[PgStatement, list[RPCDump]] = defaultdict(list)

    for pg_log in PG_LOG_DIR.glob("postgresql-*"):
        pg_statements.extend(get_pg_statements(pg_log))
        find_proxy_rpc(pg_log, pg_statements, rpc_trace)

    find_proxy_rpc(TSERVER_LOG_PATH, pg_statements, rpc_trace)
    find_proxy_rpc(MASTER_LOG_PATH, pg_statements, rpc_trace)

    rpc_trace = unite_related_responses(rpc_trace)
    replace_ids_with_names(MASTER_LOG_PATH, rpc_trace)


    DUMP_DIR = Path("rpc_dumps")
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(rpc_trace)} PG statements. Dumping to {DUMP_DIR}")

    for i, (pg_statement, rpcs) in enumerate(rpc_trace.items()):
        rpcs.sort(key=lambda rpc: rpc.timestamp)
        with open(DUMP_DIR / str(i), "w") as f:
            f.write(f"STATEMENT: {pg_statement.statement}\n")
            for j, rpc in enumerate(rpcs):
                f.write(
                    f"{j}: [{rpc.uuid}] [{rpc.type}] [{rpc.timestamp.strftime(DATEFORMAT)}] method: {rpc.method} payload:"
                    f" {rpc.payload}\n"
                )


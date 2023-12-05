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
    SERVICE_REQUEST = 3
    UNKNOWN = 4

@dataclass
class RPCDump:
    type: RPCType
    timestamp: datetime
    method: str
    payload: str


DATEFORMAT = "%H:%M:%S.%f"
PG_LOG_PATH = ".yugabyte_data/yb-tserver-n1/yb-data/tserver/logs/postgresql-2023-12-05_145741.log"
TSERVER_LOG_PATH = ".yugabyte_data/yb-tserver-n1/yb-data/tserver/logs/yb-tserver.INFO"
MASTER_LOG_PATH = ".yugabyte_data/yb-master-n1/yb-data/master/logs/yb-master.INFO"


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
        elif "[SERVICE REQUEST]" in line:
            type = RPCType.SERVICE_REQUEST
        else:
            continue

        rpc_dump = RPCDump(type=type, timestamp=ts, method="", payload="")
        if type == RPCType.SERVICE_REQUEST:
            message = line.split("[SERVICE REQUEST] Call ")[1]
            message = message.split()[0]
            rpc_dump.method = message
        else:
            message = line.split("] ")[-1]
            match message.split(maxsplit=1):
                case [method, payload]:
                    rpc_dump.method, rpc_dump.payload = method, payload
                case [method]:
                    rpc_dump.method = method
                case _:
                    raise RuntimeError("Unexpected RPC dump line")

        if rpc_dump.method in ["yb.master.MasterService.TSHeartbeat", "yb.consensus.ConsensusService.RunLeaderElection"]:
            continue
        rpc_trace[pg_statements[pg_ptr]].append(rpc_dump)


pg_statements = get_pg_statements(PG_LOG_PATH)
rpc_trace: dict[PgStatement, list[RPCDump]] = defaultdict(list)

find_proxy_rpc(TSERVER_LOG_PATH, pg_statements, rpc_trace)
find_proxy_rpc(MASTER_LOG_PATH, pg_statements, rpc_trace)
find_proxy_rpc(PG_LOG_PATH, pg_statements, rpc_trace)


DUMP_DIR = Path("rpc_dumps")
DUMP_DIR.mkdir(parents=True, exist_ok=True)

for i, (pg_statement, rpcs) in enumerate(rpc_trace.items()):
    rpcs.sort(key=lambda rpc: rpc.timestamp)
    with open(DUMP_DIR / str(i), 'w') as f:
        f.write(f"STATEMENT: {pg_statement.statement}\n")
        for j, rpc in enumerate(rpcs):
            f.write(f"{j}: [{rpc.type}] [{rpc.timestamp.strftime(DATEFORMAT)}] method: {rpc.method} payload: {rpc.payload}\n")

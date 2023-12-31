
# yugabyte_playground

## Установка
 
1. [yugabyte](https://docs.yugabyte.com/preview/quick-start/linux/) / docker-compose
2. [poetry](https://python-poetry.org/docs/#installation)
3. poetry install

## Запуск
Для локального запуска/завершения кластера из 3-х нод:
```
$ make start_local
$ make destroy_local
```

Для запуска/завершения кластера из 3-х нод, используя docker-compose, где destroy так же удаляет все volume'ы.
```
$ make start_docker
$ make down_docker
$ make destroy_docker
```

При помощи переменной окружения можно контроллировать флаги tserver'а:
```
$ export TSERVER_FLAGS="..." && make start_docker
```

Полезные флаги:
- TEST_docdb_log_write_batches - логировать все записи в DocDB
- ysql_enable_packed_row=false - отключить [packed row format](https://docs.yugabyte.com/preview/architecture/docdb/persistence/#packed-row-format), удобно для просмотра SSTable'ов

Запустить тесты с инструментацией и объединить RPC вызовы по PG запросам:
```
$ make start_with_instrumentation
$ make collect_test_rpcs
```

## Работа с кодом yugabyte
Необходимые для сборки yugabyte из исходных файлов [зависимости](https://docs.yugabyte.com/preview/contribute/core-database/build-from-src-almalinux/) собраны в [Dockerfile'е](docker/Dockerfile.dev). Все дальнейшие команды необходимо запускать из корня репозитория yugabyte.

Для сборки исходного кода: `./yb_build.sh release`.

Для сборки релизного пакета: `./yb_release`.

Для создания docker image'а после сборки релизного пакета: `./docker/images/build_docker.sh -f <package path>`

## Чтение SSTable
Зафлашить SST на диск:
```console
> yb-admin -init_master_addrs=localhost:7100 flush_table_by_id <table_id>
```
Чтобы найти id таблицы:
```console
> yb-admin -init_master_addrs=localhost:7100 list_tables include_table_id
```
либо использовать админ UI на 7000 порту.

Далее при помощи пропатченной утилиты RocksDB [sst_dump](https://github.com/facebook/rocksdb/wiki/Administration-and-Data-Access-Tool#sst-dump-tool), можно посмотреть содержимое конкретного таблета:
```console
> sst_dump --command=scan --file=<yb-data/tserver/data/rocksdb/<table-id>/<tablet-id>> --output_format=decoded_regulardb

Sst file format: block-based
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [HT{ physical: 1698329848930113 }]) -> DEL
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [SystemColumnId(0); HT{ physical: 1698332266023410 }]) -> null
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [SystemColumnId(0); HT{ physical: 1698329700942223 }]) -> null
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [ColumnId(1); HT{ physical: 1698333823076423 }]) -> "Sw"
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [ColumnId(1); HT{ physical: 1698332266023410 w: 1 }]) -> "Switzerland"
SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [ColumnId(1); HT{ physical: 1698329700942223 w: 1 }]) -> "Switzerland"
```
Аналогично можно посмотреть устройство таблицы, которая соответствует индексу:
```
Sst file format: block-based
SubDocKey(DocKey(0x152c, ["Sw"], [EncodedSubDocKey(DocKey(0xb1f1, ["Geneva"], []), [])]), [SystemColumnId(0); HT{ physical: 1698333824777313 }]) -> null
```

Так же можно посмотреть содержимое IntentsDB, зафлашив таблицу до того, как транзакция была закоммичена. Для просмотра IntentsDB необходим флаг output_format=decoded_intentsdb
```
Sst file format: block-based
SubDocKey(DocKey([], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 4 } -> TransactionId(f3e60244-170e-49ef-b361-861f55301f28) none
SubDocKey(DocKey(0xc0c4, [2], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 3 } -> TransactionId(f3e60244-170e-49ef-b361-861f55301f28) none
SubDocKey(DocKey(0xc0c4, [2], ["second"]), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 2 } -> TransactionId(f3e60244-170e-49ef-b361-861f55301f28) none
SubDocKey(DocKey(0xc0c4, [2], ["second"]), [SystemColumnId(0)]) [kStrongRead, kStrongWrite] HT{ physical: 1698773324277400 } -> TransactionId(f3e60244-170e-49ef-b361-861f55301f28) WriteId(0) null
SubDocKey(DocKey(0xc0c4, [2], ["second"]), [ColumnId(2)]) [kStrongRead, kStrongWrite] HT{ physical: 1698773324277400 w: 1 } -> TransactionId(f3e60244-170e-49ef-b361-861f55301f28) WriteId(1) "sample data"
TXN META f3e60244-170e-49ef-b361-861f55301f28 -> { transaction_id: f3e60244-170e-49ef-b361-861f55301f28 isolation: SNAPSHOT_ISOLATION status_tablet: 07c0d974865b4e4eb724fe4666a956a1 priority: 11251738716710026248 start_time: { physical: 1698773324266943 } locality: GLOBAL old_status_tablet: }
TXN REV f3e60244-170e-49ef-b361-861f55301f28 HT{ physical: 1698773324277400 } -> SubDocKey(DocKey(0xc0c4, [2], ["second"]), [SystemColumnId(0)]) [kStrongRead, kStrongWrite] HT{ physical: 1698773324277400 }
TXN REV f3e60244-170e-49ef-b361-861f55301f28 HT{ physical: 1698773324277400 w: 1 } -> SubDocKey(DocKey(0xc0c4, [2], ["second"]), [ColumnId(2)]) [kStrongRead, kStrongWrite] HT{ physical: 1698773324277400 w: 1 }
TXN REV f3e60244-170e-49ef-b361-861f55301f28 HT{ physical: 1698773324277400 w: 2 } -> SubDocKey(DocKey(0xc0c4, [2], ["second"]), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 2 }
TXN REV f3e60244-170e-49ef-b361-861f55301f28 HT{ physical: 1698773324277400 w: 3 } -> SubDocKey(DocKey(0xc0c4, [2], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 3 }
TXN REV f3e60244-170e-49ef-b361-861f55301f28 HT{ physical: 1698773324277400 w: 4 } -> SubDocKey(DocKey([], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698773324277400 w: 4 }
```

### Полный пример
```
$ export TSERVER_FLAGS="--ysql_enable_packed_row=false" && make start_docker
$ psql --host=localhost --port=5433 --username=yugabyte --dbname=postgres
psql# create table example(id1 INTEGER NOT NULL, id2 TEXT, data TEXT, PRIMARY KEY(id1, id2));
psql# insert into example values (1, "first", "sample data");
$ docker-compose -f docker/docker-compose.yml exec yb-tserver-n1 yb-admin -init_master_addrs=yb-master-n1:7100,yb-master-n2 list_tables include_table_id | grep example

postgres.example 000033f3000030008000000000004000

$ docker-compose -f docker/docker-compose.yml exec yb-tserver-n1 yb-admin -init_master_addrs=yb-master-n1,yb-master-n2,yb-master-n3 flush_table_by_id 000033f3000030008000000000004000

$ cd .yugabyte_data/yb-tserver-n1/yb-data/tserver/data/rocksdb/table-000033f3000030008000000000004000 
$ find . -name "*.sst"

./tablet-c2016b2f09ab48a18d343636a91aa580/000010.sst

$ cd tablet-c2016b2f09ab48a18d343636a91aa580
$ sst_dump --command=scan --file=. --output_format=decoded_regulardb

psql# begin transaction;
psql# insert into example values (2, 'second', 'sample data');

... flush table and find relevant tablet ...

$ cd tablet-eca8da23ea07484baf418eb190778436.intents
$ sst_dump --command=scan --file=. --output_format=decoded_intentsdb
```


### Ссылки
1. [Описание формата хранения строк в виде документов внутри DocDB](https://docs.yugabyte.com/preview/architecture/docdb/persistence/#primary-key-columns)
2. [DocKey vs SubDocKey](https://github.com/yugabyte/yugabyte-db/wiki/Low-level-DocDB-key-encoding-format)
3. [Документация к yb-admin](https://docs.yugabyte.com/preview/admin/yb-admin/#list-tables)

## Распределенные транзакции 
Для поддержания распределенных транзакций (таких транзакций, которые затрагивают более одного шарда таблицы), Yugabyte поддерживает две разных DocDB: RegularDB для уже закоммиченных данных и IntentsDB для поддержания промежуточного состояния транзакций.

При помощи дебаг-флага TEST_docdb_log_write_batches TServer'а можно отслеживать все write'ы отправленные в одно из этих хранилищ.

Сетап:
```
tail -F .yugabyte_data/node-1/disk-1/yb-data/tserverlogs/yb-tserver.INFO

psql# create table cities (name text primary key, country text);
```

Single-shard транзакция (fast-path)
```
psql# insert into cities values ('Geneva','Switzerland');

I1026 15:51:02.350379 26977 tablet.cc:1456] T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7: Wrote 2 key/value pairs to kRegular RocksDB:
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [R]: 1. PutCF: SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [SystemColumnId(0); HT{ physical: 1698335462341012 }]) => null
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [R]: 2. PutCF: SubDocKey(DocKey(0xb1f1, ["Geneva"], []), [ColumnId(1); HT{ physical: 1698335462341012 w: 1 }]) => "Switzerland"
```
(Потенциально) Multi-shard транзакция
```
psql# begin transaction;
psql# insert into cities values ('Lausanne','Switzerland');
psql# commit;
```
После insert записи попадают только в IntentsDB:
```
I1026 15:54:25.909626 27093 tablet.cc:1456] T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7: Wrote 9 key/value pairs to kIntents RocksDB:
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 1. PutCF: TXN META 528be375-03fb-4602-a0e4-fd26f7cd9978 => { transaction_id: 528be375-03fb-4602-a0e4-fd26f7cd9978 isolation: SNAPSHOT_ISOLATION status_tablet: 5d1899446f25446a8c9d59228f35e882 priority: 7365349237094446351 start_time: { physical: 1698335665895501 } locality: GLOBAL old_status_tablet: }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 2. PutCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [SystemColumnId(0)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 } => TransactionId(528be375-03fb-4602-a0e4-fd26f7cd9978) WriteId(0) null
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 3. PutCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 } => SubDocKey(DocKey(0xae01, ["Lausanne"], []), [SystemColumnId(0)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 4. PutCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [ColumnId(1)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 w: 1 } => TransactionId(528be375-03fb-4602-a0e4-fd26f7cd9978) WriteId(1) "Switzerland"
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 5. PutCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 1 } => SubDocKey(DocKey(0xae01, ["Lausanne"], []), [ColumnId(1)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 w: 1 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 6. PutCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 2 } => TransactionId(528be375-03fb-4602-a0e4-fd26f7cd9978) none
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 7. PutCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 2 } => SubDocKey(DocKey(0xae01, ["Lausanne"], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 2 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 8. PutCF: SubDocKey(DocKey([], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 3 } => TransactionId(528be375-03fb-4602-a0e4-fd26f7cd9978) none
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 9. PutCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 3 } => SubDocKey(DocKey([], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 3 }
```
После commit - ненужные записи удаляются из IntentsDB, и закомиченные данные попадают в RegularDB
```

I1026 15:54:28.902546 26977 tablet.cc:1456] T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7: Wrote 2 key/value pairs to kRegular RocksDB:
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [R]: 1. PutCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [SystemColumnId(0); HT{ physical: 1698335668893418 }]) => null
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [R]: 2. PutCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [ColumnId(1); HT{ physical: 1698335668893418 w: 1 }]) => "Switzerland"
I1026 15:54:28.902638 28101 tablet.cc:1456] T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7: Wrote 9 key/value pairs to kIntents RocksDB:
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 1. SingleDeleteCF: TXN META 528be375-03fb-4602-a0e4-fd26f7cd9978
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 2. SingleDeleteCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 3. SingleDeleteCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [SystemColumnId(0)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 4. SingleDeleteCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 1 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 5. SingleDeleteCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), [ColumnId(1)]) [kStrongRead, kStrongWrite] HT{ physical: 1698335665904754 w: 1 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 6. SingleDeleteCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 2 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 7. SingleDeleteCF: SubDocKey(DocKey(0xae01, ["Lausanne"], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 2 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 8. SingleDeleteCF: TXN REV 528be375-03fb-4602-a0e4-fd26f7cd9978 HT{ physical: 1698335665904754 w: 3 }
  T 1b095ad181804b51a0e560d75d67e6bf P 0a50692371d2442699c8b53810f58fc7 [I]: 9. SingleDeleteCF: SubDocKey(DocKey([], []), []) [kWeakRead, kWeakWrite] HT{ physical: 1698335665904754 w: 3 }
  ```
  
### Ссылки
1. [Transaction isolation levels](https://docs.yugabyte.com/preview/architecture/transactions/isolation-levels/)
2. [Distributed transactions](https://docs.yugabyte.com/preview/architecture/transactions/distributed-txns/)
3. [Transactional I/O path](https://docs.yugabyte.com/preview/architecture/transactions/transactional-io-path/)
4. [Distributed SQL Summit: Transaction Internals: Fast Path versus Multi-Shard](https://www.youtube.com/watch?v=ppY2d4hjULU)

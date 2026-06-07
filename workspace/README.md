# Workspace benchmark

Все команды в этом каталоге запускаются только внутри контейнера:

```zsh
cd /root/workspace
```

Python runners проверяют контейнерный запуск через `/.dockerenv` и ожидают
workspace в `/root/workspace`.

## Быстрый smoke

```zsh
./run-all-small.py
```

По умолчанию small suite использует `20hz_10_samples` и одного subscriber, чтобы
быстро проверить, что все транспорты собираются и стартуют.

Более тяжелые варианты:

```zsh
./run-all-medium.py
./run-all.py
```

Общие опции:

```zsh
--config 20hz_10_samples
--num-subscribers 3
--clean
--no-perf
```

## Отдельные транспорты

ROS 2:

```zsh
./run-ros2-cyclone.py --config 20hz_10_samples --num-subscribers 1
./run-ros2-fast.py --config 20hz_10_samples --num-subscribers 1
./run-ros2-fast-loaned.py --config 20hz_10_samples --num-subscribers 1
./run-ros2-zenoh.py --config 20hz_10_samples --num-subscribers 1
```

Cyclone DDS и Fast DDS всегда запускаются с DDS tuning для локального benchmark:
Cyclone ограничивается loopback/unicast и увеличенным WHC, Fast DDS использует
SHM-only transport profile с размером сегмента, достаточным для больших payload.
`run-ros2-fast-loaned.py` использует отдельные fixed-size message types,
`borrow_loaned_message()`, `rcl_take_loaned_message()` и Fast DDS DataSharing
QoS. Runner явно выставляет `ROS_DISABLE_LOANED_MESSAGES=0`, потому что в ROS 2
subscription loaned messages по умолчанию отключены. Это strict true-zero-copy
check: если текущий RMW не умеет loaned subscription messages, benchmark
завершается ошибкой.

Native Rust:

```zsh
./run-rust-iceoryx2.py --config 20hz_10_samples --num-subscribers 1
./run-rust-iceoryx2-flatbuffers.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-quic.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-unixsock.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-shm.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-flatbuffers-tcp.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-flatbuffers-quic.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-flatbuffers-unixsock.py --config 20hz_10_samples --num-subscribers 1
./run-rust-zenoh-flatbuffers-shm.py --config 20hz_10_samples --num-subscribers 1
```

Zenoh варианты пишут результаты в разные каталоги `tmp/rust_zenoh_*`. SHM
варианты включают Zenoh shared-memory feature и проверяют, что payload пришел
как SHM buffer. QUIC runners генерируют временный self-signed CA/server cert в
`/tmp/transport-benchmark-zenoh-quic-certs` и прокидывают его в router/client
конфиг Zenoh. UDP runners удалены: текущий Zenoh UDP path не доставляет payload
больше 65536 bytes стабильно в этом benchmark-профиле.

ZMQ:

```zsh
./run-zmq-flatbuffers.py --with-tcp --config 20hz_10_samples --num-subscribers 1
./run-zmq-flatbuffers.py --with-ipc --config 20hz_10_samples --num-subscribers 1
./run-zmq-protobuf.py --with-tcp --config 20hz_10_samples --num-subscribers 1
./run-zmq-protobuf.py --with-ipc --config 20hz_10_samples --num-subscribers 1
./run-zmq-capnproto.py --with-tcp --config 20hz_10_samples --num-subscribers 1
./run-zmq-capnproto.py --with-ipc --config 20hz_10_samples --num-subscribers 1
```

## Конфиги

Конфиги лежат в `configs/<profile>/config/*.yaml`:

```yaml
payload_size_bytes: 1024
publish_period_ms: 50
number_of_samples: 10
```

Перегенерировать стандартные профили:

```zsh
./configs/generate-configs.py --defaults --force
```

Создать новый профиль:

```zsh
./configs/generate-configs.py --hz 100 --samples 100 --payload-sizes 256,1024,4096 --force
```

## Результаты

Latency:

```text
tmp/<transport>/latencies/
```

Perf:

```text
tmp/<transport>/perf_data/
```

`perf stat` запускается по PID publisher/subscriber. Если perf не смонтирован или
kernel perf policy не разрешает attach, runner пишет warning, а файлы perf могут
содержать ошибку ядра. Для честного прогона сначала выполните `../setup-host.sh`
на host и проверьте `perf stat -- sleep 0.1`.

## Честность сравнения

Этот стенд проверяет работоспособность и дает полезный профиль по transport path,
но не является идеально одинаковым сравнением всех middleware.

Важные отличия:

- ROS 2 RMW включает overhead `rclcpp`, executor, ROS message path и RMW layer.
- Native iceoryx2 raw ближе к измерению IPC/shared memory runtime.
- Native Zenoh запускается отдельными вариантами: router TCP, QUIC, Unix socket,
  а также SHM payload поверх TCP control path.
- ZMQ варианты измеряют еще и стоимость выбранного кодека: FlatBuffers,
  Protobuf или Cap'n Proto.
- Fan-out на несколько subscribers у разных транспортов реализован по-разному.
- `perf stat` attach-ится после старта процесса; сборка и начальная
  инициализация не измеряются.
- Host load, CPU governor, SMT, ASLR, kernel perf policy и host IPC/network
  напрямую влияют на результат.

Основная метрика этого стенда - end-to-end latency от timestamp в publisher до
обработки в subscriber. Способ доставки является частью измеряемого стека: если
ROS 2 RMW не использует true zero-copy на этом message path, это остается в
результате ROS 2, а не выносится за скобки.

Timestamp rule для benchmark-кода: publisher ставит timestamp до упаковки
сообщения в transport/codec representation; subscriber берет receive timestamp
после распаковки обратно в benchmark-структуру. Payload validation не выполняется
в hot path.

Для интерпретации полезно отдельно смотреть группы:

- ROS 2 RMW между собой: Cyclone DDS, Fast DDS, Zenoh RMW.
- Native/runtime варианты как самостоятельные end-to-end transport paths.
- Кодеки ZMQ между собой при одинаковом transport type (`tcp` или `ipc`).

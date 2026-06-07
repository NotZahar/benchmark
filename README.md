# Стенд benchmark транспорта

Этот репозиторий содержит контейнерный стенд для проверки transport/runtime путей:
ROS 2 RMW, native iceoryx2, native Zenoh и ZMQ-варианты с разными кодеками.

Актуальный базовый стек:

- Ubuntu 26.04
- ROS 2 Lyrical Luth (`ROS_DISTRO=lyrical`)
- Zenoh `1.9.0`
- iceoryx2 `0.9.1`

iceoryx1, RouDi, `rmw_iceoryx` и старый `ros2_iceoryx` benchmark удалены.

## Запуск окружения

На host машине:

```zsh
./env_run.sh
```

Скрипт собирает image при отсутствии `transport-benchmark-image:latest` или при
изменении `Containerfile`/`container-scripts`, создает или стартует контейнер
`transport-benchmark-container` и attach-ится в `/bin/zsh`. Compose больше не
используется.

Workspace монтируется в контейнер как `/root/workspace`. Benchmark runners внутри
`workspace` рассчитаны только на запуск из контейнера и завершаются ошибкой при
host-запуске; host-only maintenance scripts явно отмечены отдельно.

Можно передать команду в контейнер без интерактивного shell:

```zsh
./env_run.sh ./run-all-small.py --no-perf
```

Удаление контейнера:

```zsh
./env_delete.sh
```

Image по умолчанию не удаляется, чтобы следующий `./env_run.sh` не пересобирал
его без необходимости. Если нужно удалить и image:

```zsh
./env_delete.sh --image
```

## Host tuning

Перед честными замерами можно применить host-настройки:

```zsh
./setup-host.sh
```

Безопасная проверка без изменения host:

```zsh
./setup-host.sh --dry-run
```

Скрипт пытается включить governor `performance`, отключить SMT, ASLR, RT runtime
limit и открыть `perf_event` для `perf stat`. Если `cpupower` не установлен,
скрипт явно пишет warning.

Проверка perf на host:

```zsh
perf stat -- sleep 0.1
```

## Контейнер

Основной файл сборки: `Containerfile`.

Контейнерные install scripts лежат в `container-scripts/`. Основной shell внутри
контейнера: `zsh`; ROS окружение source-ится через `/opt/ros/$ROS_DISTRO/setup.zsh`.

`env_run.sh` запускает контейнер с:

- `--ipc host`
- `--network host`
- `--privileged`
- `SYS_NICE`, `IPC_LOCK`, `SYS_PTRACE`
- `memlock=-1:-1`
- bind mount `/usr/bin/perf`, если host perf существует

## Benchmark

После attach в контейнер:

```zsh
cd /root/workspace
./run-all-small.py
```

Отдельные runners и детали находятся в `workspace/README.md`.

Если после работы контейнера host видит файлы в `workspace` как root-owned,
запустите на host:

```zsh
./workspace/scripts-for-analysis/fix-host-ownership.sh
```

`run-analysis.py`, запущенный через `env_run.sh`, сам возвращает владельца
своего output-каталога host-пользователю.

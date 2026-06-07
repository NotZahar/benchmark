# Анализ результатов

Анализ запускать только внутри контейнера.

```zsh
./run-analysis.py /root/workspace/tmp /root/workspace/scripts-for-analysis/csv-and-plots
```

Результаты анализа пишутся в выбранный output-каталог, например:

```text
csv-and-plots/
```

После контейнерного запуска можно вернуть владельца файлов на host-пользователя:

```zsh
./fix-host-ownership.sh
```

Этот скрипт запускать на host, не внутри контейнера.

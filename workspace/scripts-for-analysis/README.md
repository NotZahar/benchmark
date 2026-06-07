# Анализ результатов

Анализ запускать только внутри контейнера.

```zsh
./run-analysis.py /root/workspace/tmp /root/workspace/scripts-for-analysis/csv-and-plots
```

Результаты анализа пишутся в выбранный output-каталог, например:

```text
csv-and-plots/
```

При запуске через `../../env_run.sh` владелец output-каталога автоматически
возвращается host-пользователю.

# data

- `results/`：实验 JSON 结果真文件。
- `campaigns/`：规则战役 JSONL 与批量数据。
- `sealed/`：明确封存、不可悄然改写的数据集。
- `runtime/`：runner 的 state/control/accumulator，可恢复但不是科学结论本体。
- `cache/`：可再生缓存。
- `logs/`：运行日志。

不要把局部 JSON 的 `PASS` 解读为 M3；阶段结论以 `docs/status/` 为准。

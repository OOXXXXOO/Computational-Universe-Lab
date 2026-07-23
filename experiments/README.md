# experiments

独立实验与证书脚本。为保护历史脚本间 import 和冻结 SHA，本目录保持平铺。

从仓库根目录运行：

```bash
python experiments/exp1_dirac_qca.py
python experiments/r25_laurent_complex.py
```

目录内的 JSON、`figs`、`campaigns`、`rulespace`、`rulespace_gpu` 是迁移兼容符号链接；真资产位于
`data/`、`visualizations/` 和仓库顶层核心包。不要把链接展开成副本。

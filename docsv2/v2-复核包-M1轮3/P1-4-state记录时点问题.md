# 复核包 P1-4:v2m1_state.json 内 guns hash 记录时点问题

*lane B 自查自报,2026-07-27。对应协调者补充披露项(泳道接线 agent 发现)。
结论:纯记录时点伪影,冻结件本体完整未动(以 git 提交为准绳逐位证实);
成因已字节级复原。*

## 1. 现象

`data/runtime/v2m1_state.json` 的 `hashes.v2m1_guns.json` 记录
`b8272aeee226d1e75f33e0e7f82eb211c8dd0e01a28d757954a4a68c767df68e`,
而冻结件 `data/results/v2m1_guns.json` 实测 sha256 =
`b94c99b3fcf7de70b01f9aa7ddf22623812d0670e12892f57b36d652a94f91d6`;
`hashes.v2m1_maxwell_loop_r3.json` 记录(`2cd50d89…51ceb57`)则与实测逐位一致。

## 2. 冻结件完整性(准绳 = git)

- `data/results/v2m1_guns.json` 工作树实测 sha256 与 **HEAD 提交 c2927c2 中的
  版本逐位一致**(均 `b94c99b3…4f91d6`)——冻结件自提交起未被改动;
- `data/results/v2m1_maxwell_loop_r3.json` 同证(`2cd50d89…51ceb57`,工作树 =
  c2927c2)。**完整性无问题。**

## 3. 成因复原(生成顺序时间线;已字节级验证)

v2m1_guns.py 尾部生成序(L564–568 与 L624–628):

1. `write_json(payload)`——guns.json 落盘**版本 V1**(尚无 `results_sha256` 字段);
2. `jsha = sha256(guns.json)`——算得 **V1 的 hash = b8272aee…**;
3. `payload["results_sha256"] = jsha; write_json(payload)`——guns.json 落盘
   **版本 V2**(含该字段),V2 的 hash = b94c99b3…(自指不可能让文件含自身
   hash,这是仓库既有惯例:"该字段 = 写入前一刻哈希",轮 1 草稿 §四 已注);
4. 随后组装 `state_doc` 时,`"v2m1_guns.json": jsha` **复用了第 2 步的旧变量**
   (V1 的 hash),而不是重新 `sha256_file(OUT)`;r3 的条目则是现场
   `sha256_file(R3_JSON)`(r3 早已终态),所以 r3 一致、guns 不一致。

**字节级验证**:把冻结 guns.json 剔除 `results_sha256` 键后按原 dump 参数
重序列化,其 sha256 **逐位等于** `b8272aee…`——即 b8272aee 恰是"guns.json
去掉 results_sha256 字段的版本"的哈希,与"hash 先算、终版后落盘"的复原
完全吻合。同法验证 r3:剔字段版 hash = r3 内嵌 `results_sha256`
(`765404a3…`),同一惯例,自洽。

## 4. 处置

- **更正引用**:小报告 hash 册以冻结件实测值为准:
  `v2m1_guns.json`(落盘终态)sha256 = `b94c99b3fcf7de70b01f9aa7ddf22623812d0670e12892f57b36d652a94f91d6`;
  `b8272aee…` 仅在"内嵌 results_sha256 字段(写入前一刻)"语义下有效,
  state 内旧值注为**记录伪影**;
- state.json 本体的订正(把 hashes 条目改为终态 hash 或双列语义标注)属泳道
  接线件,在冻结解除/收口流程中随泳道点亮一并处理,本包只披露不改写;
- 工程教训入册:state 类汇总文件引用他文件 hash 时必须现场重算
  (`sha256_file`),禁止复用中间变量。

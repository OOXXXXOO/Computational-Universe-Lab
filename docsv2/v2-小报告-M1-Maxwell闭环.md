# v2 小报告:M1′ Maxwell 闭环(任务书交付物 6,定稿)

*lane B,2026-07-27。合并轮 1/2/3 草稿(`v2-小报告-M1-轮1草稿.md` /
`v2-小报告-M1-轮2草稿.md` / `v2-小报告-M1-轮3草稿.md`,三件保留为历史底稿)+
车道A 复核包两审计注专项结论(`docsv2/v2-复核包-M1轮3/`)。*

**措辞红线(先于一切结论)**:本报告**不宣告 M1′ PASS、不表述"Maxwell 闭环
完成"**——按任务书 §6 与裁定 §四,判定 = 全门 + 全炮 + ε=1 实测 + 双环境
四者同时,且收口权在车道A 复核 + PI;本件为 lane B 宿主单环境交付状态 +
自查自报终件。

## 〇、一句话总结与当前落点

同一冻结自旋 1 候选(R23 放置字典组装,零 Maxwell 口味输入,CERT2 位级退化为
Yee),经三轮:预飞/构造冻结(轮 1)→ 主跑 7/8 门 + G6 FAIL-STOP 追因(轮 2)→
G6 观测窗重签重跑(轮 3):**八门全 PASS、七门零回退、T_cross 预言 4/4 命中
(最差 1.3%,牙 ±50%)、ε_DOF 实测=1.0(28/28)、σ 落 A=0 精确约束线**;
四炮 + P0 + endurance 已跑并全部按预期落位,**但 lane B 在复核包 P1-2 中自报:
炮组 C3 元判据 8.0→7.5 属"运行后调值",按指令 §三 第三落点炮组作废、
HALT 报 PI**——炮组交付以该自报为准,待车道A 裁定(重跑预注册草案已备)。
主跑八门与预言命中不受此项影响;判定逻辑已装入复核探针,独立重算全一致。

## 一、构造与预飞(轮 1;详见轮 1 草稿)

- **D-M1-1 = A-CONFIRMED**:R23 放置字典组装(D1 放置派生 == Yee 1966 放置、
  D2 R17 口味一行规则、D3 R19 时间配对 dt=0.5);hand_built=None(零 DOF 手搭)。
- **证书**:CERT0 结构逐字;CERT1 row2_r23 diff 1.78e-15;**CERT2 字典 step vs
  冻结 step_yee 位级 0.0**(涌现主张形态:"自旋 2 机器的自旋 1 特化自行落在
  教科书答案上");CERT3 谱层单位圆(2.9e-15)+ 酉性地位三层声明
  (辛格式,严格局域酉膨胀未构造未主张)。
- 预飞双行 PASS(判据字段 ≤1.78e-15 / 位级 0.0);构造冻结先于主跑,
  construction_sha256 = `b7daa970f0702c9e4e12603740d4f40de33dee92cec17036dd61b76bb7f29da8`。

## 二、主跑与 G6 追因(轮 2;详见轮 2 草稿)

- 每 L∈{16,24,32,48} 一条运行记录喂全部门(相位表 P0–P6;反事实参考分叉
  ref1/ref2/ref3 声明;控制行逐位 0.0);种子 20260726+L。
- **7/8 门 PASS**;关键实测:ε_DOF=1.0(j_inv≡0,28/28,非声明)、σ 分支 i
  (y_max ≤6.8e-14)、锥外泄漏位级 0.0(v=0.25c)、p=2.0019、H 漂移 ≤1.4e-15。
- **G6 任务书强化线(1e-12)FAIL**:6/24 (k,L) 格 7.4e-13–7.8e-12,曲线纯指数
  无底板;R36 继承线(1e-3)全过。**FAIL-STOP,零调参重跑**,追因初判仪器病
  (窗按试飞 e-fold 标定,实测迟时 e-fold 长 2–3×),报车道A。计数 1。

## 三、G6 观测窗重签重跑(轮 3;裁定取①,门线一字不动;详见轮 3 草稿)

- **窗规则函数化预注册**:T_PK(L)=ceil(2.0·τ_late·ln(R0/1e-12)),τ_late/R0 =
  本轮标定段实测(R² 0.997–0.999);**先预言后验证**:轮 2 在册率外推预言
  T_cross={5323,7374,9581,14282},实测 {5328,7376,9592,14472},
  比 1.001/1.000/1.001/1.013,**4/4 命中**;分支 A/B/C 与底板检测器预写死。
- **八门全 PASS,七门零回退**(对照表与新旧种子见复核包 P2):G6 残余全 L 落
  1e-12 线内(最差 9.2e-14,余量 ≥1 量级),纯指数无底板,floor 检测器未触发;
  **分支 A 落位,G6 计数停 1**。
- 炮组同轮补跑:C1 关放置(Nyquist N_prop=0 + 色散崩)、C2 Proca
  (N_prop=3 + m_eff²=0.159–0.161 vs 0.16)、C3 非守恒源(连续性 2.0 vs 门
  1e-12)、C4 无阻尼(τ 无定义);P0 正控位级 0.0 + row2 1.8e-15;endurance
  T=20000 有界(H 3.5e-16)。**炮组判定地位见 §四-2 自报。**

## 四、两审计注专项结论(复核包 `docsv2/v2-复核包-M1轮3/`;自查自报)

1. **改脚本重启 + % 转义(P1-1/P1-3)——自报第一落点:合法披露,
   记"整改-合规"注。** 首跑完成全部物理段与 G7 扫描后死于 verdict 文案
   `±50%` 未转义(报告层);修复 = 单处 `%%` + 6 行披露注(diff 全文在案,
   字节账 73011→73470 精确闭合);预注册字段(窗规则/预言表/门线/判据核/
   三分支)逐字未动;确定性:L=16 段两次重跑与冻结件**逐位一致**(含 5 个相位
   态 sha256),首跑崩溃日志(留存)与重跑日志全部物理读数逐字一致。
   如实声明:pre-fix 源与 15:33 版中间 JSON 未保留,上述为重构性等价证据链,
   终裁在车道A。
2. **C3 元判据 8.0→7.5(P1-2)——自报第三落点:运行后调值 → 轮 3 炮组作废,
   HALT 报 PI。** 8.0 为预注册本意(脚本头 `末/首 >= 8` 自证,笔误论证不成立),
   实测 7.999999999999999(1 ULP)判"未击穿"后改 7.5 使总判翻转
   (**双值不同判**;主判据层 cont=2.0/gauss=2.0/单调则双值同判击穿)。
   缓解事实(1 ULP 零 fp 裕度规格缺陷、物理击穿无歧义、首跑 hash cbe7be76…
   全程透明入册)如实陈列但不改变归类。**炮组重跑预注册草案已备
   (P1-2 §6),未执行,等车道A 裁定与解冻。**
3. **state 内 guns hash 记录时点问题(P1-4,协调者补充项)**:纯记录伪影
   ("hash 先算、终版后落盘",字节级复原验证);冻结件与 git c2927c2 逐位一致,
   完整性无损;本报告 hash 册按冻结件实测值引用(§六)。
4. **复核探针(P3)**:`experiments/v2m1_verdict_probe.py` 只读两冻结 JSON,
   独立重算八门 verdict + T_cross 命中 + 分支重放 + 四炮/P0 判定
   (零演化重跑,<1 s)——**与落盘全部一致(mismatches=[])**;C3 双值对照
   数字(8.0 下 False / 7.5 下 True)在探针 JSON 中列明。

## 五、诚实边界(全程合并)

1. **判定地位**:M1′ PASS 未判、未收口;"双环境"沙盒位 PENDING(归车道A);
   炮组按 §四-2 自报作废待裁。ε_DOF=1.0 与 σ=A=0 为闭环级实测读数,其
   (ε,σ)=(1, A=0) 落图动作待复核 + PI 收口(裁定 §四:收口前不升级表述)。
2. **单环境**:全部读数 = 宿主 darwin/arm64/Accelerate,numpy 2.0.2 fp64。
3. **酉性**:候选为辛格式 + 逐 k 单位圆谱;严格局域酉膨胀未构造、未主张
   (轮 1 §三 三层声明)。
4. **谱系相关性**:候选与件10 同为 Yee 家族(CERT2 位级 0.0),正控对拍谱系
   相关性高——判据的牙由炮组独立保证,而炮组现处自报作废待裁状态,故
   "判据有牙"的证明地位与炮组同悬。
5. **G6 语义**:1e-12 为任务书对 R36 自带 1e-3 门的强化线(裁定 ③ 存档审计:
   线保留);Nyquist k 预注册排除于包集(零群速,R36 保护通道先例);窗末
   r_max 尾段趋平在 1e-12 线下,属 fp 减法底非物理底板(检测器未触发)。
6. **L=64 未跑**(预算红线,两轮同处置);Accelerate GEMM 伪 RuntimeWarning
   (einsum 交叉自检 6.9e-16 在册);P1 清除段慢群速带缘模诊断列如实入册。
7. **计数与禁令**:G6 连续不过计数停 1;M2′/M3′ 执行禁令持续(D2);
   本报告不含任何"GR/Maxwell 已涌现"式表述。

## 六、hash 总册(冻结件以实测/git 为准)与复现

**冻结科学件(data/results,自指令起冻结)**:

| 文件 | sha256(落盘终态实测 = git c2927c2) | 内嵌 results_sha256(写入前一刻,repo 惯例) |
|---|---|---|
| v2m1_maxwell_loop_r3.json | `2cd50d89e5dee3407db911da1a462c14292049559bc2aaa968c04b45951ceb57` | `765404a3408d931c6f0d5ec57f76e36ebbdd71aa4e8ed651581918ce5c07eb57` |
| v2m1_guns.json | `b94c99b3fcf7de70b01f9aa7ddf22623812d0670e12892f57b36d652a94f91d6` | `b8272aeee226d1e75f33e0e7f82eb211c8dd0e01a28d757954a4a68c767df68e`(state 内旧引用即此值,记录伪影,见复核包 P1-4) |
| v2m1_maxwell_loop.json(轮 2) | `256f25fad41ade0cd76e79c7f4df0691181377f45476a96cdcbfd84593f01e2c` | `a97e2fab136ea0e265945e078ae4d83366879be0fe5a2dc2d30f40ea76f6e674` |
| v2m1_candidate.json | (内嵌)`adbdcb4c622e76a49375c06dace29a84b85290486d23a6aee5d8256b297b385a` | — |
| v2m1_preflight.json | `6736cd758b3dffbebdbb0a6ae6f687e053feeba42688846eb603da9833e55284` | `d80c4dde110b0a7c7e057653f415c81b0464c9dc7db9375dc93e25eb8c6c1f75` |
| 炮组首跑 JSON(已被正式跑覆盖,未保留) | — | `cbe7be7672cf3004368b15f87a4b711082c7fd9b51d6dc13582651d40b2dc46c`(审计节在册) |

**脚本(source_sha256)**:
- v2m1_candidate.py `8aa00b0a9847ec0a6c05b857f6d8375e6d13879fd639342623d6f95b7f96b1ac`
- v2m1_preflight.py `3dfef16aac712d2726226185cf03ed2638ce15abcd76ac37358809598fe8d563`
- v2m1_maxwell_loop.py `91f26ea76c8237a851a2c101fc77a2eb6276a69ab0e5de075d7b24fa25448852`
- v2m1_maxwell_loop_r3.py `d8535f912ed3d18521c681b1846cd98a0adf4bf1e1999e69549f804c911f2ce1`
  (pre-fix 重构版 `97a240dee5b550f24c927f7896e1a0ceaf0395f19ef2c0f1eaa7abc168fbc1a3`,scratchpad 存档)
- v2m1_guns.py `855d5a615b6230460e5dd6cebbb313767db6c6176813bef8112955f5731836c0`
- v2m1_verdict_probe.py `0c23b280957d6f004d0eb48c216a07c871c4407b7dbc4fe15841c05e71bf2a4f`
  → v2m1_verdict_probe.json `3d87c499da193e4cf44b07db50eb5c8035dc15564a0baca5d1053ff109efb37c`

**支撑件**:rulespace_v2/spin1.py `69317d39ce304740b4e096df63a85ccfd63beb2a3094038ba9ebd2d923b17384`;
construction_sha256 `b7daa970f0702c9e4e12603740d4f40de33dee92cec17036dd61b76bb7f29da8`;
冻结 15 件 + M0′ 注册表运行时逐位校验在两 JSON `hash_verification` 节。

**复现命令**(冻结期间前四条**不得运行**——会写冻结路径;列此为收口后复现依据):

```bash
source .venv/bin/activate
RULESPACE_BACKEND=numpy python experiments/v2m1_preflight.py          # ~2 s
RULESPACE_BACKEND=numpy python experiments/v2m1_candidate.py          # ~0.1 s
RULESPACE_BACKEND=numpy python experiments/v2m1_maxwell_loop_r3.py    # ~670 s(轮 3 主跑)
RULESPACE_BACKEND=numpy python experiments/v2m1_guns.py               # ~20 s(现自报作废待裁)
RULESPACE_BACKEND=numpy python experiments/v2m1_verdict_probe.py      # <1 s(只读,冻结期间可跑)
```

## 七、冻结声明与下一步

- **冻结声明**:自车道A 指令(2026-07-26)起,`data/results/v2m1_*` 全部结果
  文件与炮组数据冻结,lane B 复核期间未重写任何冻结路径(新增文件仅
  `v2m1_verdict_probe.json`,指令明许;复核包与本报告为 docsv2 文档)。
- **下一步**:车道A 依复核包出判读报告(尤其 P1-2 自报落点的裁定:维持炮组
  作废 + 批准重跑预注册,或另裁)→ 炮组处置执行 → PI 收口 → 泳道点亮;
  届时方可使用"Maxwell 闭环完成 / M1′ PASS"表述,ε=1 锚点升级为
  "完整闭环级"入 (ε,σ) 地图。lane B 停在本位;M2′ 仅预注册草拟许可,执行禁。

# 小报告:tier-2 太松 + emergence 成本墙(车道B → 车道A,2026-07-20)

*(a) 子循环已在 tensor_qca 实装并验证(good cg2=1 全过 newton/defl=2.000,falsifier→4.000/FAIL)。compose ①② 过。但 ③ 转化率暴露 tier-2 结构问题,不能放 10⁵。*

## 现象(numpy fp64)
- compose ①金标准端到端 lawful ✓;②判伪两级都杀 ✓。
- ③ 转化率:1024 跑到 batch3 时 screened=149、lawful_tensor=**149 → 100% 转化**(触发契约 >80% 警戒)。
- 定位(64 条随机先验):tier-1 过 12/64(19%);**tier-2(evaluate_tensor_rule)过 53/64(83%)**;tier-2 在 tier-1 **拒掉**的 52 条里过 **41(79%)**。

## 根因:tier-2 唯一的牙是迹反转
83% ≈ 先验 P(tr_sign=1)=0.85。`evaluate_tensor_rule` 的 fact1/2/3 对**任何 tr_sign=1 且稳定**的规则基本都过:fact2 h00/φ=2 只依赖迹反转、fact1 TT=2 对稳定规则通用、fact3=2 跟迹反转走;gw_speed / G / sigma / cg2 / gamma 都不进它的判定。**漏斗方向反了——tier-1 比 tier-2 严。**

## 我的 tier-2 接线不完整(诚实)
契约(回执 point 3/4)的 tier-2 = `evaluate_tensor_rule` **+ 收紧 gw 到 1e-2(null-box 群速 vs walker 物质速)+ judge_emergence(N_prop=2)`。我只接了第一个(最松的)。**真正有牙的是 emergence**(手搭规则大多挂它,N_prop=6)——**但成本墙**:judge_emergence ~6min/条,对 19% 的 10⁵(~1.9万条)= ~79 天,per-survivor 完全不可行。

## 请车道A拍板(两级架构的重标定)
四选一(或组合):
1. **tier-1 大幅收紧**,让幸存者数 ×(降到能上 emergence 的量级,比如全场 <几百条),tier-2 = evaluate + gw(1e-2) + emergence 全套跑得起;
2. **给 tier-2 一个便宜的强判据**替代 emergence:比如 tier-2 的 gw(1e-2 null-box 群速)+ 一个廉价的 N_prop 代理(不跑全 SVD),把 83% 压到健康带;
3. **三级漏斗**:tier-1(cheap,19%)→ tier-2(evaluate+gw-1e-2,收紧到 O(10%))→ tier-3(emergence,只在 tier-2 少量幸存者上,成本可付);
4. 明确接受 tier-2=evaluate 只判"迹反转+稳定",把 lawful_tensor 定义为"tier-1∧迹反转"、emergence 另设一个**小样本审计**(如每万条抽 N 条跑 emergence 给一个涌现率估计)——但要在报告里写清 lawful_tensor 不含 emergence。

## harness 侧现状
- (a) 子循环 tensor_qca 已实装(SUB=0.5/SUB2=0.25;fact1 用 cg2_sim 归一化、比值 sub-cycle 不变;fact2 cg2_sim+gamma_sim+步数×4、**源保持物理**;fact3 继承)。cg2 稳定域到 4/3,cg2=1 在域内。
- tier-2 接口是一行,任何上面的方案(加 gw-1e-2 / emergence-proxy / 三级)我都能接。
- **另一实测问题**:tier-2 ~1.8s/条(子循环 ×4 步),numpy 下 10⁵ 的 tier-2 是小时~天级;放 10⁵ 需 MLX GPU 命令给用户,或成本封顶。
- resume(子循环后)逐位一致尚未重验(compose ④,被 ③ 阻断,待架构定了一起验)。

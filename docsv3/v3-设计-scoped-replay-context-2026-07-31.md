# V3-M0 Scoped Replay Context 设计

> 日期：2026-07-31  
> 状态：设计冻结，等待实现  
> 适用范围：Task 10 动力学证书 build / hydrate 的单次顶层调用

## 1. 问题与实测证据

当前 opaque capability 的每个 consumer 都独立重放完整 authority DAG。一次
exact-zero 谱审计的 cProfile 记录为：

- 99.96 秒、873,675,549 次函数调用；
- `prestructure.reverify` 33 次，累计 85.05 秒；
- `parent_freeze.reverify` 114 次，累计 81.25 秒；
- 完整 parent manifest validation 115 次，累计 69.84 秒；
- `canonical_sha` 89,348 次，递归 `encoded_chunks` 约 3.56 亿次；
- 单次 coverage build 与 verify 各约 20 秒，真正的谱标量运算不在前 45 个热点中。

C04 非零 support 的 full-64 硬谱核已经在 64 个点上得到正 covered margin；当前分钟级乃至
十分钟级耗时来自同一顶层证书调用内对同一不可变 live capability 的重复完整验证，而不是
Root64、64 点网格或标量 Gauss–Jordan / Cholesky。

## 2. 目标与非目标

目标是在**不减少任何独立顶层回放**的前提下，把一次 certificate build 或 hydrate 内对同一
opaque capability 的完整 authority replay 从多次收敛为一次。

必须保持：

1. 每次 public 顶层 build 和每次 public 顶层 hydrate 都各自至少完整验证一次；
2. full-64 网格、14 个 hard columns、sidecar 重构、Laurent residual、bridge 和 power
   audit 均不跳过；
3. fake、expired、错误 exact type、token/body/seal 篡改和 exposed wire 原位深层篡改仍
   fail-closed；
4. raw wire 不作为跨 consumer 的可信缓存值；
5. scope 不跨顶层调用、不跨线程，异常退出后不残留。

非目标：

- 不做跨调用、跨 scenario、跨进程或持久化缓存；
- 不缓存 caller 提交的 raw certificate / manifest；
- 不改谱网格密度、门限或证书 schema；
- 不用 canonical SHA 的通用 memoization 替代 capability 验证；
- 不改变现有 public API 的参数或返回类型。

## 3. 方案选择

采用独立的 `rulespace_v3/replay_scope.py` 和 `ContextVar` 作用域。

未采用的方案：

- 为每个 builder 增加 validated-view 参数：静态边界最强，但会扩散到整个 authority DAG，
  改动和回归面过大；
- 给 `canonical_sha` 增加 identity cache：会把 raw wire 当作可信对象，并可能掩盖
  `object.__setattr__` 篡改，不可接受。

## 4. 核心模型

`replay_scope.py` 只保存“这个 opaque capability 在当前顶层调用中已经完整验证”的证明项。
缓存 key 至少包含：

```text
(namespace, exact wrapper type, wrapper identity)
```

每个证明项强持有：

```text
wrapper strong reference
exact wrapper type
issuance token identity
exposed body object identity tuple
wrapper seal
authority record identity
authority fingerprint/digest snapshot
```

证明项不保存 caller raw wire，也不把第一次 verifier 返回的 raw clone 当成后续可信返回值。
命中后仍由该模块自己的 closure registry 取得 authority-owned record，并从该 record 返回
verified view 或新 clone。

## 5. Miss、Hit 与篡改防线

每个接线后的 opaque reverifier 继续按现有顺序完成：

1. exact wrapper type；
2. live weak registry identity；
3. 读取 private token、exposed body、seal；
4. 取得 closure 内 authority record。

scope miss 时执行原有完整 replay，成功后才登记证明项。

scope hit 时必须逐项执行：

1. wrapper strong reference 与 identity 相同；
2. exact type 相同；
3. token identity 相同；
4. 每个 exposed body 的 object identity 相同；
5. seal 相同；
6. authority record identity 与 fingerprint/digest snapshot 相同；
7. 调用该 capability 模块注册的 cheap validator。

cheap validator 至少验证：

```text
exposed == authority.snapshot
```

以及该模块原有的不需要递归 parent replay 的 exact schema / immutable guard。这个相等检查
必须覆盖完整 exact wire，因此 body identity 未变化但任一深层 scalar 被
`object.__setattr__` 原位修改时仍会拒绝。若某类 authority leaf 不能安全、确定地做完整
equality，则该类命中时重算 authoritative digest；安全优先于加速。

任何 guard 不一致都直接抛出 typed validation error，不得降级为 cache miss 后重新签发。

## 6. Context 生命周期

只有以下 public 顶层入口显式开启 scope：

- `certify_transition_dynamics(...)`
- `verify_dynamics_certificate(...)`

外层没有 scope 时创建新 scope；同线程嵌套调用复用当前 scope。最外层使用
`ContextVar.set()` 返回的 token，并在 `finally` 中无条件 `reset()`。因此成功、普通验证
失败和异常路径都不会把证明项留给下一次顶层调用。

scope 记录 owner thread identity。普通新线程看不到调用方的 context；显式复制 context
到另一线程时，scope helper 直接访问旧 context 必须拒绝。若该线程调用 public 顶层入口，
入口必须遮蔽旧 context、建立 owner 为当前线程的全新 scope，并在退出时恢复而不是复用旧
证明项。

状态采用 immutable replacement：新增证明项时给当前 context 写入新 state，不原位修改共享
dict。这样异步复制的 context 不会通过共享可变容器互相污染；同一执行上下文中的正常嵌套仍
能看到最新 state。

## 7. 模块接线边界

第一阶段先独立实现和测试 `replay_scope.py`，不改正在收口的
`calibration_authority.py`、`prestructure.py` 等共享文件。

authority 生产文件冻结后，按从根到叶的顺序接线：

1. `parent_freeze.py`
2. `registry.py`、`window.py`
3. `calibration_authority.py`
4. `prestructure.py`、`factory.py`
5. `dynamics.py`
6. `certificate.py` 顶层 build / hydrate scope

各 `_make_*_authority` closure 通过默认参数捕获 scope helper，避免运行时 monkeypatch
替换模块全局 helper 绕过验证。

## 8. RED / GREEN 合同

独立 scope 单元测试必须先证明：

1. 同一 scope 中，同一 capability 的 full validator 只执行一次；
2. 两次独立顶层 scope 各执行一次；
3. 同线程嵌套 scope 复用同一证明项；
4. full validator 抛异常时不登记，scope 退出后无残留；
5. fake、expired 和错误 exact type 拒绝；
6. 首次 full verify 后替换 token、body identity、seal 或 authority record 均拒绝；
7. 首次 full verify 后保持 body identity、只原位篡改任意深层 scalar，第二次拒绝；
8. 显式复制 context 到另一线程不能复用证明项；
9. raw wire 不出现在 scope entry；
10. monkeypatch 模块全局 helper 不能改变已构造 reverifier 的行为。

集成测试必须证明：

1. 单次 certificate build 中 parent full validation 精确为 1；
2. 紧接着的独立 hydrate 中 parent full validation再次精确为 1；
3. C04 full-64 build、verify、重签 hard-column 篡改拒绝和 hydrate 全部通过；
4. exact-zero 旧路径仍通过；
5. build 与 hydrate 各自计时，确认热点不再是重复 ParentFreeze replay。

## 9. 完成判据

只有同时满足以下条件才可把 scoped replay 标为 GREEN：

- 所有安全 RED 转为 GREEN；
- C04 full-64 certificate 与 hydrate 均完成；
- 每个顶层调用的 parent full validation 计数为 1，而不是 0；
- 独立调用之间没有命中；
- 性能剖析显示重复 parent canonicalization 不再支配 Task 10；
- `compileall`、目标测试、`git diff --check` 和静态无 FFT / 无硬路径 LAPACK 审计通过。

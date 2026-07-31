# V3-M0 Scoped Replay Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不减少任何独立 certificate build / hydrate 完整回放的前提下，使同一顶层调用内
同一 opaque live capability 的昂贵 authority replay 最多执行一次。

**Architecture:** 新建独立的 context-local replay proof 内核。它只缓存当前 scope 内“首次
完整验证已经成功”的 opaque proof，不缓存 caller raw wire；每次命中仍检查 live registry
之后取得的 wrapper/token/body identity/seal/authority identity，并调用模块自己的完整 wire
equality 或 authoritative digest cheap validator。public build/hydrate 才开启 scope。当前
Parent/Task14 合同正在修正，因此 Phase A 独立完成内核，Phase B 必须等待新的 production
freeze。

**Tech Stack:** Python 3.9、`contextvars.ContextVar`、immutable dataclass、
`types.MappingProxyType`、`threading.get_ident`、`unittest`、weak-reference authority
fixture。

---

## 文件边界

Phase A：

- Create: `rulespace_v3/replay_scope.py` — context 生命周期、proof key/entry、hit/miss
  守卫和统计；不得 import 任何 authority 模块。
- Create: `tests/test_v3m0_replay_scope.py` — 独立 miniature opaque authority，覆盖完整
  安全合同。

Phase B（新的 Parent production freeze 后才执行）：

- Modify: `rulespace_v3/parent_freeze.py`
- Modify: `rulespace_v3/registry.py`
- Modify: `rulespace_v3/window.py`
- Modify: `rulespace_v3/calibration_authority.py`
- Modify: `rulespace_v3/prestructure.py`
- Modify: `rulespace_v3/factory.py`
- Modify: `rulespace_v3/dynamics.py`
- Modify: `rulespace_v3/certificate.py`
- Modify/Create focused integration tests under `tests/`

Phase B 不改变任何 public wire schema、函数参数、返回类型、网格、门限或 source closure。

### Task 1: 写 miniature authority 与核心安全 RED

**Files:**

- Create: `tests/test_v3m0_replay_scope.py`

- [ ] **Step 1: 写缺失模块 RED fixture**

测试中的 miniature authority 必须模拟真实 closure registry：

```python
@dataclass(frozen=True)
class _Leaf:
    value: int


@dataclass(frozen=True)
class _Body:
    leaf: _Leaf


@dataclass(frozen=True)
class _AuthorityRecord:
    snapshot: _Body
    seal: str


class _Wrapper:
    __slots__ = ("__weakref__", "_token", "_body", "_seal")


class _MiniAuthority:
    def __init__(self) -> None:
        self.full_validation_count = 0
        self.fail_full_validation = False
        self._live = {}
        self._lock = threading.RLock()

    def issue(self, value: int = 1) -> _Wrapper:
        exposed = _Body(_Leaf(value))
        snapshot = copy.deepcopy(exposed)
        wrapper = _Wrapper()
        wrapper._token = _TOKEN
        wrapper._body = exposed
        wrapper._seal = _SEAL
        identity = id(wrapper)
        reference = weakref.ref(
            wrapper,
            lambda ref, key=identity: self._remove(key, ref),
        )
        self._live[identity] = (
            reference,
            _AuthorityRecord(snapshot=snapshot, seal=_SEAL),
        )
        return wrapper
```

`reverify()` 必须先做 exact type、live weak registry、private field 读取；然后调用尚不存在的
`_cached_replay_is_valid(...)`。miss 执行完整 equality/seal 验证，成功后调用尚不存在的
`_record_successful_replay(...)`。hit 直接从 closure authority snapshot 返回 fresh
`deepcopy`，不从 scope 取 raw result。

- [ ] **Step 2: 写行为 RED**

至少写成以下独立测试：

```python
def test_same_scope_runs_full_validation_once()
def test_independent_scopes_each_run_full_validation_once()
def test_nested_scope_reuses_outer_proof()
def test_exception_does_not_record_or_leak_scope()
def test_wrong_exact_type_fake_and_expired_wrapper_are_rejected()
def test_token_body_seal_and_authority_identity_changes_are_rejected()
def test_in_place_deep_scalar_mutation_is_rejected_on_cache_hit()
def test_copied_context_cannot_reuse_proof_in_another_thread()
def test_public_scope_in_copied_thread_starts_an_independent_scope()
def test_scope_entry_has_no_raw_wire_or_cached_result_field()
def test_statistics_report_hits_misses_and_full_records()
```

deep mutation 测试必须保持 exposed body identity 不变：

```python
with _scoped_replay_context():
    authority.reverify(wrapper)
    object.__setattr__(wrapper._body.leaf, "value", 2)
    with self.assertRaises(ValueError):
        authority.reverify(wrapper)
```

跨线程测试必须使用 `contextvars.copy_context()` 显式复制 active context，避免只测普通新线程
默认没有 ContextVar 值的简单情形。

- [ ] **Step 3: 运行 RED 并确认失败原因**

Run:

```bash
/Users/prismer/workspace/science/ca-universe-lab/.venv/bin/python \
  -m unittest tests.test_v3m0_replay_scope -v
```

Expected: FAIL/ERROR，唯一根因是 `rulespace_v3.replay_scope` 尚不存在；不得出现 fixture
语法错误或错误 import。

### Task 2: 实现 immutable context-local proof 内核

**Files:**

- Create: `rulespace_v3/replay_scope.py`
- Test: `tests/test_v3m0_replay_scope.py`

- [ ] **Step 1: 定义 immutable key、entry、state 与统计**

实现以下私有数据边界：

```python
@dataclass(frozen=True)
class _ReplayKey:
    namespace: str
    wrapper_type: type
    wrapper_identity: int


@dataclass(frozen=True)
class _ReplayEntry:
    wrapper: object
    token: object
    exposed_body_identities: tuple[int, ...]
    seal: str
    authority: object
    authority_digest: str


@dataclass(frozen=True)
class _ReplayScopeState:
    owner_thread_identity: int
    entries: Mapping[_ReplayKey, _ReplayEntry]
    hits: Mapping[str, int]
    misses: Mapping[str, int]
    full_records: Mapping[str, int]


@dataclass(frozen=True)
class ReplayScopeStatistics:
    entry_count: int
    hits: tuple[tuple[str, int], ...]
    misses: tuple[tuple[str, int], ...]
    full_records: tuple[tuple[str, int], ...]
```

所有 mapping 均由新 `dict` 包装成 `MappingProxyType`；更新时替换整个
`_ReplayScopeState`，禁止原位改共享 dict。`_ReplayEntry` 不得包含 `raw_wire`、`body`、
`snapshot`、`result` 或 verifier 返回值。

- [ ] **Step 2: 实现 scope 生命周期**

```python
_ACTIVE_REPLAY_SCOPE: ContextVar[Optional[_ReplayScopeState]] = ContextVar(
    "v3m0_active_replay_scope",
    default=None,
)


@contextmanager
def _scoped_replay_context() -> Iterator[None]:
    current = _ACTIVE_REPLAY_SCOPE.get()
    owner = threading.get_ident()
    if current is not None and current.owner_thread_identity == owner:
        yield
        return
    token = _ACTIVE_REPLAY_SCOPE.set(_empty_state(owner))
    try:
        yield
    finally:
        _ACTIVE_REPLAY_SCOPE.reset(token)
```

若复制来的 active context owner 不等于当前线程，public scope 创建并遮蔽一个全新 state；
直接调用 hit/record/statistics helper 时 owner 不匹配则抛 `RuntimeError`。

- [ ] **Step 3: 实现 miss/hit 守卫**

`_cached_replay_is_valid` 使用 keyword-only 参数：

```python
def _cached_replay_is_valid(
    *,
    namespace: str,
    wrapper: object,
    expected_type: type,
    token: object,
    exposed_bodies: tuple[object, ...],
    seal: str,
    authority: object,
    authority_digest: str,
    cheap_validator: Callable[[], None],
) -> bool:
```

无 active scope 时返回 `False`。active miss 时只增加该 namespace 的 miss 计数并返回
`False`。active hit 时逐项检查：

```python
entry.wrapper is wrapper
type(wrapper) is expected_type
entry.token is token
entry.exposed_body_identities == tuple(id(body) for body in exposed_bodies)
entry.seal == seal
entry.authority is authority
entry.authority_digest == authority_digest
```

然后无条件调用 `cheap_validator()`；只有它成功返回才记 hit 并返回 `True`。任一 proof
guard 不一致直接 `ValueError`，不得退化为 miss。

- [ ] **Step 4: 实现成功登记与统计**

`_record_successful_replay` 接收与 hit 相同的 proof 字段，但不接收/保存 raw result。
active scope 外为 no-op；active scope 内如果同 key 已存在则抛 `RuntimeError`，否则 immutable
replacement 写 entry，并增加 `full_records`。

`_replay_scope_statistics()` 只允许在当前 owner 的 active scope 中调用，返回按 namespace
排序的 immutable tuples。

- [ ] **Step 5: 运行 GREEN**

Run:

```bash
/Users/prismer/workspace/science/ca-universe-lab/.venv/bin/python \
  -m unittest tests.test_v3m0_replay_scope -v
ruff check rulespace_v3/replay_scope.py tests/test_v3m0_replay_scope.py
```

Expected: 所有测试 `ok`，ruff `All checks passed!`。

- [ ] **Step 6: 对独立内核做 mutation self-review**

检查：

```bash
rg -n "raw_wire|snapshot|result|MutableMapping|default=\\{" \
  rulespace_v3/replay_scope.py
```

Expected: entry/state 不保存 raw wire、snapshot 或 result，不存在 ContextVar mutable default。

- [ ] **Step 7: 独立提交 Phase A**

```bash
git add rulespace_v3/replay_scope.py tests/test_v3m0_replay_scope.py \
  docsv3/v3-实施计划-scoped-replay-context-2026-07-31.md
git diff --cached --name-only
git commit -m "feat(v3m0): add scoped replay proof context"
```

暂不 stage Parent/Task14/Task10 full64 或其他代理文件。

### Task 3: 新 Parent freeze 后逐 authority 接线

**前置条件：** 总控明确宣布新的 Parent/Task14 production freeze 和 commit SHA。在此之前本
Task 保持 pending。

**Files:**

- Modify: `rulespace_v3/parent_freeze.py`
- Modify: `rulespace_v3/registry.py`
- Modify: `rulespace_v3/window.py`
- Modify: `rulespace_v3/calibration_authority.py`
- Modify: `rulespace_v3/prestructure.py`
- Modify: `rulespace_v3/factory.py`
- Modify: `rulespace_v3/dynamics.py`

- [ ] **Step 1: 为真实 parent 写计数 RED**

在 focused integration test 中 patch/wrap parent manifest 的 full validator。用外层 private
scope 包住一个真实 certificate build，断言 full validator 精确为 1；先观察当前值大于 1。

- [ ] **Step 2: 接线 parent reverifier**

在 live registry 查找和 private field 读取之后构造 proof。parent cheap validator 至少执行：

```python
type(manifest) is ParentFreezeManifest
manifest == authority.manifest
seal == authority.fingerprint
```

body identity 由 scope proof guard 中保存的 `id(manifest)` 检查；cheap validator 负责完整
wire equality。miss 保持原 `manifest_validator(..., require_closed_body=True)` 完整回放，
成功后才 record。hit 返回 `clone(authority.manifest)`。

- [ ] **Step 3: 逐层接线其余 opaque reverifier**

每个 `_make_*_authority` 用默认参数捕获 `_cached_replay_is_valid` 和
`_record_successful_replay`。每接一层即运行该模块既有 fake/object-new/expired/deep-tamper
安全测试；禁止一次性机械改完再测试。

- [ ] **Step 4: 运行真实 parent 计数 GREEN**

Expected: 单个 build scope 的 parent full validator 为 1；另一个独立 scope 再调用时累计为
2，证明没有跨顶层复用。

### Task 4: public certificate build / hydrate 接线

**Files:**

- Modify: `rulespace_v3/certificate.py`
- Test: focused certificate integration tests

- [ ] **Step 1: 用最薄 public wrapper 开启 scope**

将现有函数 body 移入 private implementation，public 签名保持不变：

```python
def certify_transition_dynamics(...):
    with _scoped_replay_context():
        return _certify_transition_dynamics_scoped(...)


def verify_dynamics_certificate(...):
    with _scoped_replay_context():
        return _verify_dynamics_certificate_scoped(...)
```

若上层已经开启同线程 scope，context manager 机械复用；否则每次 public 调用建立全新 scope。

- [ ] **Step 2: 验证失败与异常退出**

分别让 build 返回 typed failure、让 hydrate 抛 validation error，随后开启下一次独立调用；
统计必须从空 state 开始。

- [ ] **Step 3: 报告命中/未命中**

测试用外层 private scope 调 public 入口，在 scope 退出前读取
`_replay_scope_statistics()`；保存/汇报各 namespace 的 hit、miss、full_records，但不得把
这些运行时统计加入科学 certificate wire。

### Task 5: C04 full-64 性能与证据验收

**前置条件：** 新 Parent freeze 和 Task 10/12 production 文件均稳定。

- [ ] **Step 1: 跑 C04 build 并单独计时**

记录 wall/user/sys、parent full validation count、scope hit/miss/full_records，以及谱值：
point count、14/18 columns、covered `M/G` lower/condition、fill、derivative increment。

- [ ] **Step 2: 独立跑 hydrate 并单独计时**

hydrate 必须新建独立 scope，parent full validation count 再为 1；不得沿用 build proof。

- [ ] **Step 3: 跑真实重签篡改拒绝**

修改 full64 hard sidecar 一项、重算 sidecar/coverage SHA，verifier 必须因完整重构不一致拒绝。

- [ ] **Step 4: 回归 exact-zero 与静态纪律**

```bash
python -m compileall -q rulespace_v3
python -m unittest \
  tests.test_v3m0_spectral.ExactZeroSpectralAuditTests.test_exact_zero_coverage_has_root64_fill_and_fourteen_hard_columns \
  -v
ruff check rulespace_v3 tests/test_v3m0_replay_scope.py
git diff --check
```

并确认 production hard path 无 FFT、运行时 `sin/cos/exp`、`np.linalg.inv/cholesky`。

- [ ] **Step 5: 只提交所属文件并汇报 GPU checkpoint**

提交前列出 staged names，排除其他代理修改。汇报 build/hydrate 墙钟、parent full
validation=1/1、namespace hit/miss/full_records、C04 full64 数值门和 tamper/hydrate
证据。

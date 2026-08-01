# v3 设计勘误：Parent-v3 P-epoch 签发闭合

*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*

## 0. 裁定与边界

本文修正 `v3-设计勘误-C19-refreeze-v2-2026-08-01.md` §9 中尚未闭合的
`P → 双 review receipt → S → internal audit → Parent-v3` 协议。冲突处以本文为准。

当前 provisional `CurrentApplicationAuthorityV3` 的 construction dependency closure
读取工作树中的 live bytes；而 signing commit `S` 又必须把设计文档由 `DRAFT` 改为
`SIGNED`。若 candidate 在 `S` 上继续读取 live bytes，则 application/candidate root 必然相对
reviewers 在 `P` 上审阅的 root 漂移。这个漂移不能由重签、自哈希或 caller-supplied SHA
消除。

唯一获批修正为 **P-epoch Git-blob replay**：

1. `ParentFreezeCandidateV3Manifest` 的全部 source/dependency closure 都只读取 preparation
   commit `P` 中的 Git blobs；
2. `S` commit 中 immutable `SIGNED` document blobs只进入 `SignedSourceRefV2`，不回流
   candidate root；
3. `ParentSigningAuditV1` 以 strict `P..S` diff 把 reviewed P-epoch candidate 与 S-epoch
   signed sources 连接；
4. `ParentFreezeV3Manifest` 另行绑定 candidate、signed sources、receipts、audit 与 observed
   `S`，其 current Parent root 不回写 Git；
5. `VerifiedParentFreezeV3` 只能由零参 issuer 在 clean `S=HEAD` 上内部重放后签发。

本文只冻结 Parent-v3 的 raw/signing/opaque authority 合同，不签发 Parent，不改变
`HALT-V3M0-WINDOW`，不解锁 V3-M1、V3-M2、pilot、正式扫描或 GPU 长跑。

## 1. 路线比较与拒绝项

### A. live-HEAD closure

拒绝。`DRAFT→SIGNED` 会改变 closure 与 candidate root，复审对象不可重放。

### B. P-root 与 S-root 两套 candidate

拒绝。receipts 审阅 P-root、issuer 却发行 S-root，二者之间没有同一 exact candidate；即使
同时保存两个 hash，也只是记录漂移，不是关闭漂移。

### C. P-epoch candidate + S-epoch signed sources

采用。candidate 的科学/构造内容固定在 `P`；`S` 只改变允许的签字材料；audit 对两者建立
单向、无环、可机械重放的连接。

## 2. Epoch 与 Git 语义

### 2.1 Preparation commit `P`

`P` 必须是 clean、非 merge commit。它一次性包含：

- 全部 V3-M0 root-bearing schema、builder、verifier、issuer、orchestrator、tests；
- 四份待签设计文档的 DRAFT bytes；
- Parent-v3 candidate 与 source-closure builder；
- signing audit control flow；
- downstream calibration/materialization/transition/metric/grid/certificate/response/evidence
  的完整实现与攻击回归；
- signing literals 文件的未注入占位状态。

`P` 非 authority。创建 `P` 后若任一复审要求改变上述 body，旧 receipts 全部作废，必须产生
新的 `P`。

### 2.2 Signing commit `S`

`S` 必须满足：

```text
clean HEAD = S
S 恰有一个 parent
S^ = P
```

`S` 只允许：

1. 四份 mandatory signed sources 中下列 exact 状态行变换；
2. 两份 canonical review receipt JSON 的新增；
3. `rulespace_v3/parent_signing_literals_v1.py` 中 P/candidate/doc/receipt 的最终 literal 注入。

禁止修改 schema、数学、阈值、grid、executor、builder/verifier/issuer control flow、tests、
source-closure path set 或任何 runtime/scientific result。`S` 后任何提交都会使零参 issuer
fail closed；需再次发行时必须重新建立新的 `P/S` 周期。

### 2.3 P-epoch blob reader

P-epoch reader 唯一读取形式为：

```text
git cat-file blob P:<canonical repo-relative path>
```

它拒绝：不存在的 commit/blob、绝对路径、`..`、非 canonical POSIX path、symlink escape、
重复路径、非 UTF-8 文档，以及 caller 提供的 blob bytes/hash。candidate builder 在 `P` 上以
`HEAD` 为 observed P；issuer 在 `S` 上只以内审得到的唯一 `HEAD^` 为 observed P。不存在
可传入 arbitrary P 的 production issuer API。

authority-neutral verifier 可以重放 raw candidate 自带的 `preparation_commit_sha`，但其返回值
仍是 raw dataclass，不产生 capability。

本仓库 object format 冻结为 SHA-1；`P`、`S` 与所有 Git blob OID 都是 exact 40 位 lowercase
hex，evidence/content SHA 仍是 exact 64 位 lowercase SHA-256，两类字段不得共用 validator。
reader 必须以 `git cat-file -t` 证明 P/S object type 为 `commit`，证明 `S^=P` 且 P 是 S 的
直接祖先；以 `git ls-tree -z` 证明 reviewed/source paths mode 仅为 regular blob `100644` 或
`100755`，拒绝 symlink `120000`、submodule `160000`、tree、missing path 与 P→S 非 allowlisted
mode change。

issuer 的初始/最终 clean 定义唯一为
`git status --porcelain=v1 -z --untracked-files=all --ignore-submodules=none` 输出 exact empty bytes，
exit code 为零且 stderr 为空；ignored files不属于 clean gate，但不得位于 source/review closure。
intent-to-add、untracked、conflict、submodule drift 全部使输出非空并阻断。

## 3. Mandatory signed sources

`signed_source_refs` 必须精确包含以下四项，按 relative path 的 UTF-8 bytes 严格升序排列：

```text
docsv3/v3-勘误-geometry-scenario-audit-2026-07-31.md
docsv3/v3-设计勘误-C19-refreeze-v2-2026-08-01.md
docsv3/v3-设计勘误-Parent-v3-P-epoch签发闭合-2026-08-01.md
docsv3/v3-设计勘误-metric-support-authority-v1-2026-08-01.md
```

冻结 role/scope 为：

| relative path | `source_role` | `source_scope` |
|---|---|---|
| geometry scenario audit | `SIGNED_INCREMENTAL_ERRATUM` | `C05_C18_SCENARIO_RESPONSE_GEOMETRY` |
| C19 refreeze v2 | `SIGNED_CONSTRUCTION_ERRATUM` | `C19_REAL20_REFREEZE_V2` |
| Parent-v3 P-epoch | `SIGNED_ISSUANCE_PROTOCOL` | `PARENT_V3_P_EPOCH_SIGNING` |
| metric-support authority | `SIGNED_RUNTIME_AUTHORITY_PROTOCOL` | `C19_METRIC_SUPPORT_AUTHORITY_V1` |

每份 S-epoch raw UTF-8 文档必须包含唯一状态标记 `状态：SIGNED / 已签发`，不得仍含状态标记
`状态：DRAFT`。普通正文中讨论字符串 `DRAFT` 不构成状态漂移。

四个 exact status transforms 唯一为：

```text
geometry audit:
*Computational Universe Lab · 2026-07-31 · 状态：DRAFT / 未签发 / 不生效*
→ *Computational Universe Lab · 2026-07-31 · 状态：SIGNED / 已签发 / 生效*

C19 refreeze v2:
*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit 或 scientific authority*
→ *Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit 或 scientific authority*

Parent-v3 P-epoch:
*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*
→ *Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*

metric-support authority:
*Computational Universe Lab · 2026-08-01 · 状态：DRAFT / 未签发 / 非 Parent、permit、runtime 或 scientific authority*
→ *Computational Universe Lab · 2026-08-01 · 状态：SIGNED / 已签发 / 非 Parent、permit、runtime 或 scientific authority*
```

## 4. Exact raw contracts

所有 dataclass 必须 `frozen=True`，拒绝 dict、subclass、未知/缺失 attribute、bool-as-int、
container subclass 与逐层 re-sign。所有 `*_sha` 是完整 canonical payload 的 SHA-256，payload
只排除本层 self-hash。

### 4.1 `SignedSourceRefV2`

schema ID：`v3m0.signed-source-ref.v2`。exact fields：

```text
source_ref_schema_version
source_role
source_scope
relative_path
raw_sha256
preparation_commit_sha
signing_commit_sha
source_ref_sha
```

`raw_sha256` 只绑定 S-epoch immutable document blob bytes；`preparation_commit_sha=P`、
`signing_commit_sha=S`。不得保存 P-epoch doc SHA 的第二个同义字段；P bytes 已由 candidate
source closure 绑定。

### 4.2 `ParentReviewReceiptV1`

schema ID：`v3m0.parent-review-receipt.v1`。exact fields：

```text
receipt_schema_version
review_role
reviewer_id
reviewer_key_id
signature_algorithm
preparation_commit_sha
reviewed_candidate_sha
reviewed_path_closure
reviewed_path_closure_sha
verdict
signed_statement_sha
signature_armor
receipt_sha
```

唯一两个 review roles：

```text
MATHEMATICS_AND_EVIDENCE_CONTRACT_REVIEW
AUTHORITY_AND_BOUNDARY_REVIEW
```

`verdict` 唯一允许 `PASS`。`reviewed_path_closure` 是 exact tuple of
`(canonical relative path, P-blob SHA-256)`，按 path UTF-8 bytes 排序、非空、不重复；必须包含
candidate source closure、四份 signed-source DRAFT、相关 tests 和所有 Parent-v3
root-bearing implementation。两份 receipt 必须绑定同一 P、candidate 和 path closure，角色
不同，receipt SHA、reviewer identity 与 key 均不同。

首版不允许 reviewer 自选子集：`reviewed_path_closure` 必须逐项等于 candidate
`source_closure` 去掉 Git mode 后的 exact `(path, blob_sha256)` projection。因而两份 receipt
审阅同一完整 P closure，不存在遗漏路径、不同 closure 或 caller-supplied review scope。

P 中必须冻结 `rulespace_v3/parent_reviewer_keys_v1.py` 的 exact trusted-key registry。每个 role
唯一映射到一个非空 `reviewer_id`、一个由 OpenSSH public key bytes 计算的
`reviewer_key_id` 与一把不同的 Ed25519 public key；private keys 不得进入仓库、P/S、receipt、
runtime artifact 或 source closure。`signature_algorithm` 唯一为 `openssh-ed25519-v1`，签名
namespace 唯一为 `culab-parent-v3-review-v1`。

`signed_statement_sha` 是 receipt 前述字段中除 `signed_statement_sha`、`signature_armor`、
`receipt_sha` 外完整 canonical payload 的 SHA-256。`signature_armor` 必须是
`ssh-keygen -Y sign` 对该 canonical payload UTF-8 bytes 产生的 exact ASCII-armored signature；
issuer 以 P-blob trusted-key registry 和 `ssh-keygen -Y verify` 重放 identity、namespace 与
signature。S 提交者不持有两把 private keys是治理前提；机械门证明的是“两把 P 预注册的不同
key 分别签署两个不同 role”，不夸称它能证明现实世界的人类身份或组织独立性。

canonical receipt 文件路径唯一为：

```text
data/results/v3m0_parent_v3_review_mathematics.json
data/results/v3m0_parent_v3_review_authority.json
```

JSON 必须由
`json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False)` 的 UTF-8 bytes 加单个 `\n` 构造；字段与 dataclass exact fields 一致，tuple
按 JSON array 编码，拒绝 duplicate keys、BOM、多余 whitespace、额外尾随 bytes、非有限数、
超过 4 MiB 的文件、超过 128 层递归、超过 4096 项的任一 array 或超过 1 MiB 的任一 string。
receipt 文件只允许在 `S` 新增；`receipt_sha` 是除本层 self-hash 外完整 receipt payload 的
canonical SHA-256。

### 4.3 `ApplicationSupersessionV3`

schema ID：`v3m0.application-supersession.v3`。exact fields：

```text
supersession_schema_version
control_case_id
superseded_application_instance_id
superseded_application_authority_v2_sha
replacement_application_instance_id
replacement_application_authority_v3_sha
reason_id
supersession_sha
```

首版必须恰有一项：C19 historical V2 authority 被 C19 real-20 v3 authority 取代，
`reason_id=C19_REAL20_PARENT_WIRE_REFREEZE_V2`。superseded body 只留在历史分栏，不得同时出现在
current registry。

### 4.4 `ParentFreezeCandidateV3Manifest`

schema ID：`v3m0.parent-freeze-candidate.v3`。exact fields：

```text
candidate_schema_version
authority_state                   = PROVISIONAL_NOT_ISSUED
program_id                        = projective-rule-space-v3m0-v3
preparation_commit_sha
historical_parent_v1
reviewed_candidate_v1
reviewed_candidate_v2
inherited_current_application_authorities_v2
superseded_application_authorities_v2
refrozen_current_application_authorities_v3
application_supersessions
block_success_scenario_ids
source_closure
source_closure_sha
candidate_sha
```

Candidate current registry 由
`inherited_current_application_authorities_v2 + refrozen_current_application_authorities_v3`
按冻结的 Parent-v1 application 顺序组成；control/application/scenario IDs 不得重复或缺失。
`inherited...v2` 必须排除 C19，`superseded...v2` 必须恰含 historical C19，
`refrozen...v3` 必须恰含 C19 real-20。`CurrentApplicationAuthorityV3.authority_state` 在 candidate
和 Parent body 中始终保持 `PROVISIONAL_NOT_ISSUED`；它是被 Parent 递归审阅的 raw construction
body，authority 来自外层 `VerifiedParentFreezeV3`，不得逐层改写状态或重签。

继承分栏只允许复用 Parent-v2 的 **authority-neutral exact raw bodies 与 fresh closed replay**，
不得要求或接受 `VerifiedParentFreezeV2`。为避免导入 private helper，
`parent_freeze_v2.py` 必须新增且只新增下列 raw handoff API：

```python
build_reviewed_current_application_authorities_v2_raw(
) -> tuple[CurrentApplicationAuthorityV2, ...]
verify_reviewed_current_application_authorities_v2_raw(
    authorities: tuple[CurrentApplicationAuthorityV2, ...],
) -> tuple[CurrentApplicationAuthorityV2, ...]
```

这两个 API 不进入 `parent_authority.py`，不签 capability，不读取 Parent-v2 signing constants；
V3 candidate builder 必须 fresh replay 全量 raw tuple，再机械分离 historical C19，不能由 caller
传入已删减 tuple。C01–C18 的 raw source mapping 继承该 tuple 的 exact Parent-v1 ordinal 与
Candidate-v2 refreeze，C19 是唯一 supersession；分析专用 C20 不伪造 application authority。

C19 current body 在 P/S 两端的唯一内部入口为：

```python
_replay_c19_current_application_authority_v3_at_preparation_commit(
    preparation_commit_sha: str,
) -> CurrentApplicationAuthorityV3
```

它把 P-blob dependency reader 一直传入 construction closure builder，再从该 closure 构造
`application_authority_sha`；禁止先调用 live builder、事后替换 closure 并重签。该入口保持
private，production P 只来自 observed `HEAD` 或 audited `S^`。

`source_closure` 仅由 P tree/blobs 构造，包含所有决定 candidate、Parent issuance 和 V3-M0
downstream authority 的 docs/source/test/result-prerequisite paths。唯一 owner
`parent_candidate_v3.py` 必须从 P tree 机械选择以下 **全部 tracked regular blobs**，再把显式
canonical path tuple 保存为 `PARENT_V3_SOURCE_CLOSURE_PATHS` 的 runtime snapshot；payload 中不
保存 glob、目录或选择器：

每个 exact entry 唯一为 `(relative_path, git_mode, raw_sha256)`；`git_mode` 只允许字符串
`100644`/`100755`，不是 int，`raw_sha256` 是 P blob bytes 的 SHA-256。

```text
docsv3/*.md
formal/v3m0/**                         # 排除 .lake；只接受 tracked regular blob
rulespace_v3/**/*.py
rulespace_gpu/v3_*.py
tests/test_v3m0_*.py
tests/test_v3_gpu_*.py
experiments/v3m0_*.py
data/results/v3m0_*.json               # 仅 P tree 已存在的 prerequisite artifacts
```

此外，fresh-interpreter completeness audit 必须以 Python audit hook 记录 candidate build/replay
期间加载的每个 repository-local module `__file__` 与读取的每个 repository-local regular file；
observed set 必须是 source closure 子集。任何从未纳入上述集合的动态 import/file read、ignored
path、symlink、目录、worktree fallback 或 caller path 都阻断 P。选择规则和完整显式 tuple 在 P
后逐位冻结；S replay只枚举 P tree，因此 S 新增 receipts不会回流 candidate root。

唯一 public authority-neutral APIs：

```python
build_v3m0_parent_freeze_candidate_v3() -> ParentFreezeCandidateV3Manifest
verify_parent_freeze_candidate_v3(
    candidate: ParentFreezeCandidateV3Manifest,
) -> ParentFreezeCandidateV3Manifest
```

builder 仅在 clean `HEAD=P` 且 HEAD 尚非符合 signing shape 的 `S` 时构造 review candidate；
verifier 从 candidate 声明的 P blobs fresh replay。内部 `_replay_..._at_preparation_commit(P)` 不在
`__all__`。

### 4.5 `ParentSigningAuditV1`

schema ID：`v3m0.parent-signing-audit.v1`。exact fields：

```text
audit_schema_version
preparation_commit_sha
signing_commit_sha
review_receipt_shas
diff_digest
diff_allowlist_id
signed_source_refs_root_sha
reviewed_candidate_sha
reviewed_path_closure_sha
source_closure_sha
audit_sha
```

`review_receipt_shas` 按冻结 role 顺序，不按 hash 排序。`diff_allowlist_id` 唯一为
`parent-v3-signing-diff-v1`。`diff_digest` 不哈希受 Git config/quoting 影响的人类 patch；它是
schema `v3m0.parent-signing-tree-diff.v1` 下列 canonical body 的 SHA-256：

```text
entries = tuple sorted by UTF-8 path bytes of:
  (relative_path,
   old_mode, new_mode,
   old_git_blob_oid | null, new_git_blob_oid | null,
   old_blob_sha256 | null, new_blob_sha256 | null)
```

changed-path enumeration 只用 `LC_ALL=C`、`GIT_CONFIG_NOSYSTEM=1` 下的
`git -c core.quotePath=false -c diff.renames=false diff-tree --no-commit-id -r --raw -z
--no-renames P S --`；非零 exit、任意 stderr、rename/copy、非 40 位 SHA-1 OID 均拒绝。最终门
不信任 raw stdout 内容本身：它以 `git ls-tree` 与 `git cat-file` 重取每项 mode/blob，重建上述
canonical record，再对 P/S blob bytes 执行 exact transformation。不得用文本 hunk 解析替代
byte comparison。

### 4.6 `ParentFreezeV3Manifest`

schema ID：`v3m0.parent-freeze.v3`。exact fields：

```text
parent_freeze_schema_version
authority_state                  = CURRENT_PARENT_V3_ISSUED
program_id                       = projective-rule-space-v3m0-v3
preparation_commit_sha
signing_commit_sha
reviewed_candidate_v3
signed_source_refs
review_receipts
signing_audit
current_application_registry_sha
parent_freeze_v3_sha
```

`current_application_registry_sha` 机械哈希 candidate 中 canonical current registry 的完整 tagged
payload；不得只哈希 roots 的字符串拼接。manifest 不接受 caller-supplied candidate、refs、receipts、
audit、commit 或 SHA。

以下 root 的 canonical owner/schema 唯一为：

```text
current_application_registry_sha:
  current_application_registry_v3_payload()
  schema = v3m0.current-application-registry.v3
  entries = Parent-v1 ordinal 中的 tagged entries
  tag ∈ {INHERITED_CURRENT_V2, REFROZEN_CURRENT_V3}

signed_source_refs_root_sha:
  signed_source_refs_v2_root_payload()
  schema = v3m0.signed-source-ref-tuple.v1
  entries = 四个完整 SignedSourceRefV2 payload，按 §3 path 顺序

reviewed_path_closure_sha:
  reviewed_path_closure_v1_payload()
  schema = v3m0.parent-reviewed-path-closure.v1
  entries = 完整 path/P-blob-SHA pairs，按 UTF-8 path bytes 顺序

source_closure_sha:
  parent_v3_source_closure_v1_payload()
  schema = v3m0.parent-v3-source-closure.v1
  preparation_commit_sha = P
  entries = 完整 path/P-mode/P-blob-SHA records，按 UTF-8 path bytes 顺序
```

tagged registry 的旧 C19 application/scenario IDs 必须在 historical C19 ordinal 原位删除，并在
同一 ordinal 插入 C19 real-20 v3 application 及其唯一新 success scenario ID；旧 ID 仅在
superseded 历史分栏可达。`block_success_scenario_ids` 同样在旧 C19 success ID 的原 ordinal
原位替换新 ID，C20 不进入该 tuple。上述四个 payload 函数是唯一 owner，其他模块只可调用，
不得复制同义 hashing record。

## 5. Opaque authority 与唯一 issuer

opaque type 唯一为 `VerifiedParentFreezeV3`。它沿用 module-private token、weak live registry、
immutable seal 与 detached snapshot view，但不得继承/subclass `VerifiedParentFreezeV2`，不得提供
public constructor、hydrator、promoter、resigner 或 V1/V2 adapter。

public APIs 唯一为：

```python
issue_v3m0_parent_freeze_v3() -> VerifiedParentFreezeV3
require_current_parent_v3(
    parent: VerifiedParentFreezeV3,
) -> ParentFreezeV3Manifest
```

issuer 必须零参，并按顺序：

1. 记录 clean `HEAD=S` snapshot；
2. 证明 S single-parent P；
3. 从 P blobs fresh replay candidate/source closure，并证明执行中的所有 root-bearing Python
   `__file__` bytes 等于 audited S blob，且除 signing literals 外 S blob 等于 P blob；
4. 从 immutable S Git blobs 重建四份 signed refs；live tree只参与 clean gate，不作为 authority
   bytes 来源；
5. 从 immutable S Git blobs fresh 解析并重验两份 canonical JSON receipts 与 Ed25519 signatures；
6. 逐 path/逐 blob exact-transform 审计 P..S allowlist；
7. 重算 candidate、registry、signed-source tuple、receipt/path/source closure roots；
8. 生成 module-private signing-audit capability 与 raw audit record；
9. 构造并重验完整 Parent manifest，但尚不注册 wrapper；
10. 再次证明 tree clean、`HEAD=S` 未变；
11. 仅在第二次 snapshot 通过后注册 opaque wrapper 并返回。

第 1 或第 10 步不一致、Git 命令失败、repo dirty、merge S、错误 parent、receipt role 重复、
任何 root/splice/drift 均在 wrapper 注册前 fail closed。

`VerifiedParentFreezeV3` 采用 **process-local audited-S snapshot authority**：issuer 成功后，运行
写入 `data/results/`、`data/runtime/` 或 `visualizations/` 不会使已有 wrapper失效；但
`require_current_parent_v3()` 每次都必须重验 wrapper exact type/live registry/seal、`HEAD=S`，
以及全部 code/doc/test 受保护 execution paths 的 live bytes 与 S blob一致。P-epoch prerequisite
result blobs 已递归进入 candidate，运行后不得再次从其可变 live path读取。`require` 不重跑全局 clean gate，
从而允许结果输出；任一 HEAD 变化、受保护 path drift、wrapper/registry/seal drift立即拒绝。
所有 downstream authority 模块必须在 Parent issuer 初始 replay时 import 并纳入 closure，禁止签发
后从未审计路径 lazy-import root-bearing code。

由于 Git 不提供阻止任意外部进程改写工作树的强制全局锁，本文的机械威胁模型不声称抵抗
拥有同一文件系统写权限、专门在两次系统调用之间实施 ABA 的恶意进程。immutable P/S blobs、
双 snapshot 与 per-require protected-path replay 消除正常并发/误操作导致的证据混用；检测到任何
可见漂移即 fail closed。

## 6. P→S allowlist

allowlist 是 exact path + exact transform，不是目录或 glob：

- 四份 mandatory docs：只允许一处状态行从本文 §2.2 的 DRAFT literal 变为 SIGNED literal；
  其余 bytes 逐位相同；
- 两个 receipt JSON paths：P 中必须不存在，S 中必须为 §4.2 exact canonical PASS body；
- `rulespace_v3/parent_signing_literals_v1.py`：只允许预冻结的 `None`/零值 literal 赋值行被
  exact P/candidate/doc/receipt values 替换；AST 去除这些 literal 后必须逐位等价；
- 其他 path：禁止出现于 diff。

signing literals 文件的 public constants、P placeholders 与 S value types 唯一为：

```python
PARENT_V3_PREPARATION_COMMIT_SHA: str | None = None
PARENT_V3_REVIEWED_CANDIDATE_SHA256: str | None = None
PARENT_V3_REVIEWED_PATH_CLOSURE_SHA256: str | None = None
PARENT_V3_SIGNED_SOURCE_SHA256_BY_PATH: tuple[tuple[str, str], ...] = ()
PARENT_V3_REVIEW_RECEIPT_SHA256_BY_ROLE: tuple[tuple[str, str], ...] = ()
```

S 中前三项分别变为 exact 40-hex、64-hex、64-hex string；后两项分别变为 §3 path 顺序的
四个 `(path,64-hex)` 与 §4.2 role 顺序的两个 `(role,64-hex)`。literal auditor 以 Python
`ast.parse` 比较 P/S module：只把上述五个 `AnnAssign.value` 规范化为 sentinel 后要求
`ast.dump(..., include_attributes=False)` 完全相等；同时逐 byte证明除五个 RHS span外无变化。
禁止新增/删除/reorder statement、改 annotation、name、docstring、import、comment、encoding或
newline。issuer 只把这些 literals 与从 immutable P/S blobs重算的值比较；candidate builder与
source/root payload不读取 S 值。

signing literals 文件的 **S-epoch 注入值** 不得进入 candidate/source-closure hash 的值依赖；
candidate source closure 可以且必须绑定该文件的 P-epoch placeholder blob，reviewed path closure
也必须包含它。candidate builder/verify payload 与 current application roots 均不得读取 S-epoch
注入值。否则会重新形成 candidate↔S 环。

## 7. Fail-closed 攻击合同

至少必须拒绝：

- candidate 在 S 上读取 live docs 或将 signed source SHA 回写 candidate；
- P blob/live worktree 混用、P 不存在、dirty P/S、merge S、`HEAD^ != P`、audit 前后 HEAD 漂移；
- 缺任一四份 signed source、role/scope/path 顺序漂移、仍为 DRAFT、正文越权改动；
- 缺/重复 reviewer、不同 P/candidate/path closure、非 PASS、raw dict/subclass/re-sign receipt；
- receipt 在 P 已存在、S 新增第三份 receipt 或 canonical JSON 漂移；
- source closure 漏 root-bearing source/test、重复/乱序、工作树 fallback；
- historical C19-v1 与 refrozen C19-v2 同时进入 current registry，或 C19 缺失；
- `CurrentApplicationAuthorityV3` 内层伪装为 issued state；
- Parent-v1/v2、raw manifest、object-new、伪 token、死 registry、seal/body独立篡改；
- caller-supplied P/S/candidate/ref/receipt/audit/root；
- audit 只验 path 不验 hunk，或只验 digest 不重放 exact transform；
- issuer 中途 repo/HEAD 变化的 TOCTOU。

正向测试必须证明：在 P 上构造的 candidate，经四份文档的 exact DRAFT→SIGNED 模拟后，
P-epoch replay 的 `candidate_sha` 与 `source_closure_sha` 逐位不变；同时 S-epoch
`signed_source_refs_root_sha` 必须改变并由 audit 正确连接。

## 8. 实施与签发顺序

形成 P 前必须先做 semantic-state audit：四份 mandatory docs 的正文不得仍声称已在 P 中存在的
schema/module/API 为 `NOT IMPLEMENTED`、`MISSING` 或未来工作；它们必须准确写成
`IMPLEMENTED / REVIEW PENDING / NOT ISSUED`。这些正文修订属于 P 前普通 implementation
commits，不属于 S allowlist。audit 使用每份文档冻结的 expected-state table，不以宽泛 grep
决定语义；若实现仍缺失则保留真实缺口并禁止形成 P，不能为了通过文本门先改状态。

```text
本设计 DRAFT + focused implementation plan
→ Parent candidate P-epoch raw TDD
→ issuance records/signing-audit TDD
→ Parent opaque authority TDD
→ calibration/materialization/transition/metric/grid/certificate/response/evidence/orchestrator
→ 全 V3-M0 定向回归与 source-closure finalization
→ clean preparation commit P
→ 两名独立 reviewer 对同一 P/candidate/path closure 复审
→ allowlisted signing commit S（四文档 SIGNED + receipts + literals）
→ zero-arg Parent-v3 issuer live replay
→ V3-M0 运行；按状态机签发 READY 或 exact HALT
```

不得在 downstream V3-M0 code 尚会改变时提前建立真实 P/S。任何测试 fixture 中的临时 Git
仓库仅验证 audit 算法，不构成当前仓库发行。

## 9. 自审与当前状态

- candidate 与 S-epoch signed bytes 已单向拆开，无 doc/root/commit 自引用；
- reviewers 审阅的 candidate 与 issuer 在 S 上重放的 candidate 是同一 P-epoch body；
- C19 historical authority 保留可达，但 current registry 不重复；
- metric-support 设计与本签发协议均纳入 mandatory signed sources；
- raw current application 保持 provisional，不冒充独立 capability；
- 不改阈值、不跳过 V3-M0、不把 C19 当 physical anchor/family；
- 当前没有 P、receipts、S、audit capability 或 Parent-v3 issuer。

当前状态保持：

```text
Parent-v3 P-epoch signing design   DRAFT / NOT ISSUED
ParentFreezeCandidateV3            NOT IMPLEMENTED
VerifiedParentFreezeV3             NOT IMPLEMENTED / NOT ISSUED
HALT-V3M0-WINDOW                   unchanged
READY-V3-M1-ANCHOR-CERTIFICATION  NOT ISSUED
GPU formal scan                    LOCKED
```

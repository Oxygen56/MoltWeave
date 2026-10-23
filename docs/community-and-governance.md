# 完整 Trace 接入与固定治理边界

本页对应已实现的本地基础设施。它没有连接外部用户、采集真实会话或部署云服务，也没有把收到的 Trace 自动交给模型执行。持续进化是否改善模型效果，由主实验的独立验收决定。

## 数据路径和明确授权

`TraceClient` 只在显式调用时访问指定的本机 HTTP 服务，构造客户端不会上传。服务端的注册凭证绑定 `tenant_id/user_id`，上传不能自行选择租户。服务端拒绝与凭证冲突的 Trace 身份字段。同一租户的另一个用户也不能读取来源不属于自己的数据。

完整路径是：本地完整 Trace → 明确授权本次会话和用途 → 客户端凭据过滤 → 带鉴权的本机上传 → 服务端再次过滤 → 私有原始库 → 显式注册的派生经验／候选。

完整会话不是摘要。消息、工具参数和结果、记忆读写、检索等 JSON 字段原样保留，只有命中的凭据被替换。用户必须明确设置：

- `session_ids`：具体会话，不支持 `*`。
- `full_trace=True`：本端点接受完整会话内容的授权，不会静默改成仅摘要。
- `personal_evolution` 与 `general_evolution`：分别授权，默认都为假。完整记录上传不等于允许通用进化。
- `expires_at`：未来的 Unix 时间。
- `retention_days`：明确设置的保留天数，当前接口允许 1–3650 天。

服务端生成 Trace ID，凭证只保存 SHA-256 指纹。记录在 `private/<tenant-user-hash>/raw/` 下分开保存，文件权限为 `0600`。凭据过滤包括常见 credential 字段、Bearer 字符串和部分 API key 格式；它不是通用 PII 检测器，不能可靠识别任意编码的秘密。使用者仍须检查授权上传的内容。其他个人信息不会被偷偷摘要或自动删除。

当前服务仅接受 loopback 地址，客户端拒绝非本机目的地、重定向和环境代理，不会把鉴权头转发给重定向目标。单次默认请求上限 16 MiB，超限返回 413，不截断内容冒充完整记录。当前未实现分块大附件上传。

## 本地启动与客户端

以下代码是 API 示例；测试仅使用合成数据。

```python
import secrets
import time
from moltweave.community import TraceStore, TraceHTTPServer, TraceClient

store = TraceStore("state/community")
token = secrets.token_urlsafe(32)  # 通过受信任的本地配置交给实际使用者
store.register_client(token, tenant_id="demo-tenant", user_id="demo-user")

with TraceHTTPServer(store, port=0) as server:
    client = TraceClient(server.url, token)
    consent = client.grant_consent(
        session_ids=["demo-session"], full_trace=True,
        personal_evolution=True, general_evolution=False,
        expires_at=time.time() + 3600, retention_days=7,
    )
    receipt = client.upload({
        "session_id": "demo-session",
        "messages": [{"role": "user", "content": "Synthetic example"}],
        "tool_calls": [], "memory_reads": [],
    }, consent_id=consent["consent_id"])
    trace = client.get_trace(receipt["trace_id"])
```

`TraceHTTPServer(...).start()`、`.close()` 和 `.url` 也可用于 CLI 集成；长期运行可直接使用继承的 `serve_forever()`。注册／撤销客户端凭证是受信任的本地配置 API，不通过 HTTP 开放。

HTTP 路由：`POST /v1/consents`、`POST /v1/traces`、`GET /v1/traces/<id>`、`POST /v1/derivatives`、`GET /v1/derivatives/<id>`、`POST /v1/withdrawals`。`GET /health` 不返回用户数据。没有远程审批签发、代码执行或工具执行路由。

## 分用途的派生、撤回和保留期

进化工作应先调用 `store.eligible_traces(token, purpose="personal" 或 "general")`，读取时可进一步指定 `store.get_trace(token, trace_id, purpose=...)`。默认不提供跨用户合并入口。通用授权只表示本条记录可参与通用候选构造，不表示它已变成其他用户可读的数据或已获发布许可。

```python
derived = client.register_derivative(
    source_ids=[receipt["trace_id"]], kind="memory-candidate",
    content={"lesson": "Synthetic evidence-supported lesson"}, purpose="personal",
)
```

派生物可以继续派生，系统保存直接来源及所有原始 Trace 祖先。即使来源已经是派生经验，也会重新检查每个祖先对目标用途的授权，避免把个人经验包装一次就用于通用进化。

`client.withdraw(consent_id)` 立即撤销授权，删除对应原始 payload 及所有关联的派生 payload，并留下最小索引墓碑以阻止重新使用。后续上传、读取和派生均被拒绝。返回的 `affected_derivatives` 应交给主内核检查已采用的版本，选择停用、回滚或重新生成。这个基础设施不会声称“删除来源就自动消除了已采用机制所受的影响”。

服务运行时定期调用 `purge_expired()`，也可以离线显式调用。保留期到期或授权到期都会删除原始 payload、停用派生物。索引墓碑仍保留 ID、来源、时间和撤销原因，不含会话正文。已发送的外部操作不会被程序版本回滚自动撤销，需要单独补偿。

本实现只管理自己的状态目录；外部导出、系统备份和云存储未实现，不能承诺替使用者清理那些副本。当前没有加密静态内容、TLS、客户独立数据库或生产级多租户部署；这是单机自部署的逻辑隔离及操作系统文件权限边界。

## 固定治理与审批

`governance.py` 属于固定外层。Agent 可以提出受限表达式 IR 和 Prompt 的候选，但不能修改治理、鉴权、租户边界、评分器或任意引入 Python／shell 执行表面。表达式合法性和运行时工具权限仍由主内核校验，风险标签不能替代沙箱。

`risk_of(before, after)` 返回 `sensitive`、`blocked`、`classification`、`reasons`、`changed_paths` 和前后 hash。权限、上传／出站、共享、保留／删除、记忆读写策略及依赖变化需要 owner 审批；固定边界与任意执行表面直接拒绝。普通 Prompt 修改可以参与测量；疑似绕过审批、扩大权限或泄露秘密的 Prompt 被视为敏感。文本检测是保守启发式，不声称完美识别所有恶意意图。

审批使用 HMAC-SHA256；签名密钥保存在本地 `0600` 文件。签发 API 是受信任 owner 控制面的入口，调用者必须先验证 owner 身份；填写 `owner="..."` 本身不是身份认证。Trace 接入服务没有签发入口。

```python
from moltweave.governance import ApprovalStore, require_approval, stable_hash

approvals = ApprovalStore("state/approvals")
plan = {
    "candidate_hash": stable_hash(candidate),
    "base_hash": stable_hash(current),
    "dependencies": {"runner": "immutable-runner-hash"},
    "scope": {"tenant_id": "demo-tenant", "user_id": "demo-user"},
    "action": "adopt",
}
# 只有真实 owner 在核对完整差异、验证证据、数据/权限影响和回滚计划后调用：
ticket = approvals.issue(**plan, expires_at=time.time() + 600, owner="verified-owner")
# 内核在真正采用前执行；任何 plan 字段变化都不匹配，票据仅可消费一次：
receipt = require_approval(current, candidate, approval_store=approvals,
                           ticket=ticket, **plan)
```

候选 hash 覆盖完整可执行候选。完整评审方案（包括差异、测试证据、影响和回滚／补偿计划）可序列化为 `review_bundle`，把 `stable_hash(review_bundle)` 放入 `dependencies["review_bundle"]`，一起绑定签名。依赖 hash、作用范围、动作、到期时间和 nonce 全部签名。候选内容、基线、依赖、作用范围或动作变化后必须重新申请。跨线程／进程的票据消费通过文件锁串行化，并落盘防止重启后重放。`authorize(..., consume=False)` 仅供预检，不能作为执行许可；实际采用必须消费票据。失败后重试应重新签发，不能复用已消费票据。

`ApprovalError` 继承 `PermissionError`。`require_approval` 对敏感修改无票据时拒绝，对固定边界即使有票据也拒绝。审批通过不是效果证明，候选仍需通过固定评测并留下实际加载记录。该模块没有模型补丁执行入口。

## 上传内容与投毒边界

上传中的 `system` 消息、工具输出和“忽略所有规则”等内容都是存储的数据，不获得系统指令或 owner 权限。本模块不会执行它们，也不会自动生成／采用经验。后续研究工作进程应仅将其作为不可信证据，结合受控运行器和独立评测提出候选；真实用户反馈和模型自述不能伪装成受控运行器的验收回执。

不具备初始环境、版本、权限及状态快照的 Trace，只能支持观察和假设。拿旧工具返回重新问模型，不是候选已经真实重执行的证据。本服务不提供伪造这种执行结论的接口。

## 参考边界

- [OTel GenAI 内容记录](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md#capturing-instructions-inputs-and-outputs)：完整内容可以另外存储；关闭 span 内容不自动等于关闭所有外部上传 hook。
- [Langfuse 隔离](https://langfuse.com/security/data-isolation)、[删除](https://langfuse.com/docs/administration/data-deletion)、[保留期](https://langfuse.com/docs/administration/data-retention)：项目鉴权、数据集副本与原始 Trace 有不同生命周期。
- [Agent Lightning 轨迹聚合](https://microsoft.github.io/agent-lightning/stable/20-trainer-configuration/#trace-aggregator)：模型调用轨迹不自动包含完整环境快照。

## 实际验证记录

2026-10-23，仅使用临时目录、合成凭证与合成会话进行本机 HTTP 往返及攻击测试，没有真实用户内容。首轮治理测试有 1 个测试代码错误：未显式导入 `unittest.mock`；已修正。首轮 HTTP 通过，但发现 HTTPError 未关闭产生 ResourceWarning；已补关闭响应，并在后续运行将 ResourceWarning 作为错误检查。最终原始输出附在下方。

运行解释器为本机 Python 3.15；本轮未另外运行 Python 3.11。以下输出对应命令 `PYTHONPATH=src:tests python3 -W error::ResourceWarning -m unittest test_community test_governance -v`，退出码为 0。

```text
test_credentials_filtered_client_and_server_without_summarizing (test_community.CommunityHTTPTests.test_credentials_filtered_client_and_server_without_summarizing) ... ok
test_cross_tenant_and_same_tenant_other_user_cannot_read_or_derive (test_community.CommunityHTTPTests.test_cross_tenant_and_same_tenant_other_user_cannot_read_or_derive) ... ok
test_forged_trace_identity_and_stolen_consent_are_rejected (test_community.CommunityHTTPTests.test_forged_trace_identity_and_stolen_consent_are_rejected) ... ok
test_full_trace_opt_in_and_exact_session_scope_required (test_community.CommunityHTTPTests.test_full_trace_opt_in_and_exact_session_scope_required) ... ok
test_full_trace_roundtrip_authentication_and_private_raw_storage (test_community.CommunityHTTPTests.test_full_trace_roundtrip_authentication_and_private_raw_storage) ... ok
test_nonlocal_bind_and_client_destination_refused (test_community.CommunityHTTPTests.test_nonlocal_bind_and_client_destination_refused) ... ok
test_oversized_body_rejected_instead_of_silently_truncated (test_community.CommunityHTTPTests.test_oversized_body_rejected_instead_of_silently_truncated) ... ok
test_personal_and_general_consent_do_not_launder_through_derivatives (test_community.CommunityHTTPTests.test_personal_and_general_consent_do_not_launder_through_derivatives) ... ok
test_prompt_injection_remains_inert_trace_data (test_community.CommunityHTTPTests.test_prompt_injection_remains_inert_trace_data) ... ok
test_redirect_never_forwards_authorization (test_community.CommunityHTTPTests.test_redirect_never_forwards_authorization) ... ok
test_retention_purges_original_and_derived_payloads (test_community.CommunityHTTPTests.test_retention_purges_original_and_derived_payloads) ... ok
test_withdrawal_removes_transitive_payloads_and_stops_future_upload (test_community.CommunityHTTPTests.test_withdrawal_removes_transitive_payloads_and_stops_future_upload) ... ok
test_all_execution_plan_fields_are_bound (test_governance.GovernanceTests.test_all_execution_plan_fields_are_bound) ... ok
test_concurrent_consumption_across_store_instances_has_one_winner (test_governance.GovernanceTests.test_concurrent_consumption_across_store_instances_has_one_winner) ... ok
test_duplicate_nonce_and_nonfinite_json_are_rejected (test_governance.GovernanceTests.test_duplicate_nonce_and_nonfinite_json_are_rejected) ... ok
test_expiry_and_revocation (test_governance.GovernanceTests.test_expiry_and_revocation) ... ok
test_fixed_outer_boundary_cannot_be_approved (test_governance.GovernanceTests.test_fixed_outer_boundary_cannot_be_approved) ... ok
test_privilege_changing_prompt_is_not_an_ordinary_prompt_edit (test_governance.GovernanceTests.test_privilege_changing_prompt_is_not_an_ordinary_prompt_edit) ... ok
test_prompt_only_change_is_ordinary (test_governance.GovernanceTests.test_prompt_only_change_is_ordinary) ... ok
test_replay_prevention_survives_reopening_store (test_governance.GovernanceTests.test_replay_prevention_survives_reopening_store) ... ok
test_sensitive_diff_cannot_execute_without_owner_approval (test_governance.GovernanceTests.test_sensitive_diff_cannot_execute_without_owner_approval) ... ok
test_sensitive_new_subtree_and_list_are_detected (test_governance.GovernanceTests.test_sensitive_new_subtree_and_list_are_detected) ... ok
test_signature_tampering_including_expiry_and_nonce_rejected (test_governance.GovernanceTests.test_signature_tampering_including_expiry_and_nonce_rejected) ... ok

----------------------------------------------------------------------
Ran 23 tests in 5.379s

OK
```

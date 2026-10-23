# 已授权 Trace 如何真正进入改进提案

`feedback.py` 把社区接入的完整 Trace 接到两个模型请求：问题归因，然后生成与当前基线 schema 兼容的机制候选。候选只注册为隔离的派生材料；本模块没有执行、采用、签发 owner 审批或认证效果的入口。正式实验正在使用的 `governance.py`、`runtime.py`、`program.py`、`llm.py` 和评测代码均未为这条链路修改。

## 完整数据路径

1. 使用现有 `TraceClient` 上传到本机 `TraceHTTPServer`；服务器凭证决定租户和用户，Trace 自报身份无效。
2. 现有源授权决定完整上传、个人进化和通用进化的范围。反馈层通过 `TraceStore.get_trace(token, id, purpose=...)` 再次校验，而不是直接读取原始目录。
3. 另行明确授权第三方模型处理：绑定具体 Trace ID 与完整 payload hash、个人／通用用途、模型端点、模型名、到期时间和 `full_trace=True`。远程模型必须 `thirdparty=True`。Trace 正文中写着“我同意上传”不算这条授权。
4. 第一次 `ModelClient.complete` 接收完整来源，输出问题假设及实际 Trace 的 JSON pointer。固定校验器拒绝引用其他 Trace 或不存在的路径。路径存在只证明出处，不证明内容真实或归因正确。
5. 再次核验授权、来源版本及撤回状态，第二次 `complete` 接收完整 Trace、归因和当前基线，提出受限 IR／Prompt 修改。
6. 固定 `validate_program` 验证完整候选；`risk_of` 分类。普通候选标为 `proposed_not_executed`；敏感候选标为 `owner_review_required`；固定边界违规的材料不可执行。未知字段、任意 Python／shell、非法 IR、无实质修改直接拒绝。
7. 再次确认授权后，通过现有 `register_derivative` 保存候选和来源链。个人和通用授权不可互相替代，通用候选也不会自动变成其他用户可读的数据。

两次模型请求的 stage 各只能消费一次。失败后不能不受限制地重放同一授权；如果确需重新请求，应由使用者重新授权。底层 `ModelClient` 一次请求内部最多三次物理尝试的行为保持不变，回执保留每次尝试。授权撤回可以阻止后续阶段及候选保留，不能撤销已经发送给服务商的请求。

## 集成 API

```python
import time
from moltweave.feedback import FeedbackPipeline, ModelProcessingConsentStore
from moltweave.llm import ModelClient
from moltweave.program import baseline

# store 为正在接收完整 Trace 的同一个 TraceStore。
# token 是既有服务器凭证，trace_id 是服务器生成的 ID。
model = ModelClient()  # 专供这条反馈请求使用；不与其他实验并发共用实例
model_consents = ModelProcessingConsentStore("state/feedback-model-consents")

# 只有使用者明确确认第三方、完整内容、模型和用途后才能执行：
grant = model_consents.grant(
    store, token, trace_ids=[trace_id], purpose="personal",
    model_client=model, thirdparty=True, full_trace=True,
    expires_at=time.time() + 1800,
)

pipeline = FeedbackPipeline(store, model_consents, model)
candidate = pipeline.propose(
    token, trace_ids=[trace_id], purpose="personal",
    model_consent_id=grant["id"], base_program=baseline(),
)
# candidate["adopted"] 永远为 False。
# 独立执行和效果验收是后续流程，敏感修改还须先取得固定治理层的 owner 审批。
```

`grant` 和 `revoke` 是新增的本地受信任后端 API，目前没有新增第三方处理授权 UI 或 HTTP 路由。它们通过既有 TraceStore 凭证验证身份；调用方不能传一个自造的授权字典让 `propose` 信任。授权还绑定签发时的凭证指纹，轮换凭证后需要重新授权。模型端点或模型名改变也需要重新授权。

## 模型回执、派生撤回与外部处理

对于真实 `ModelClient`，反馈层在单次调用期间把回执写入私有临时目录，随后通过 TraceStore 注册为 `feedback-model-call-receipt` 派生物并清理临时原件。模型返回的候选、调用回执都继承原始 Trace 的来源；来源撤回会将这些派生 payload 一起停用和清除。必须使用专用 ModelClient 实例，避免其他调用同时修改该实例的输出目录。

模型不能自行决定效果。它返回的 `passed`、`success`、`approved`、`adopted`、`status`、`score` 只可能进入 `ignored_model_assertions`，不会变成宿主验收结果。宿主固定写入：

```json
{
  "evaluation": {
    "status": "not_executed",
    "trace_replay_performed": false,
    "effect_established": false,
    "success_certified": false
  },
  "adopted": false,
  "execution_allowed_by_this_artifact": false
}
```

缺少环境初态和外部状态的旧 Trace 只能支持假设，不能证明候选已重放成功。远程模型处理已经发生后，本地删除不代表服务商副本同步消失；服务商保留政策仍须在真正用户授权流程中说明。这条链路不会训练模型权重。

## 合成安全回归与真实模型边界

`tests/test_feedback.py` 的模型是明确标注的 `ScriptedModel`，只用于确定性测试：跨租户、盗用授权、个人／通用混用、缺少第三方授权、模型／端点变化、到期／撤销、请求阶段重放、伪造出处、非法 IR、敏感 Prompt 隔离，以及候选和真实格式回执的派生撤回。

这些单元攻击测试只说明固定程序边界在合成案例中工作，不能当成长时间真实模型投毒或 Prompt 注入防御的实证。

2026-10-23 本机运行 `PYTHONPATH=src:tests python3 -W error::ResourceWarning -m unittest test_feedback -v`，退出码为 0，实际结果为：

```text
Ran 13 tests in 6.770s

OK
```

另行进行的一次真实模型链路只使用明确标注的合成用户、合成会话和生成的反馈样例。完整公开回执保存在 `artifacts/feedback-synthetic-live-20261023/`（如目录已存在则增加独立后缀）。`run.json` 区分完成、失败、候选 schema 验证和未执行效果；`model-calls/` 保留真实请求／响应及物理尝试。最终状态以该目录中的实际回执为准，不以单元测试推定模型成功。

本次真实运行已经完成：使用环境既定的 `deepseek-flash` 和 `https://api.deepseek.com`，没有换模型；真实归因与提案各一次，候选通过固定 schema／IR 验证。候选 hash 为 `3feb046322c06f6d5baf914149168b742fc20278f78b8f1ba6f6419f3af9ebf1`，状态 `proposed_not_executed`。全部处理的是合成数据，明确第三方授权为真。未执行候选、未采用、未建立效果提升。

两次真实请求各仅一个物理尝试，归因记录 839 total tokens，提案记录 1,911 total tokens，合计 2,750。归因和提案耗时分别为 2.651 秒和 3.675 秒。

候选原件保留了模型的实际不足：它改动 `memory_score`、`memory_top_k` 和 Prompt，但 `memory_score` 的新增项包含 `age + (-age)`，且最终乘以安全除零得到的零，因此静态上会退化为原有的 overlap 排序。这不是有效记忆排序改进的证据。其余 Prompt 与 top-k 改动仍未执行评测；没有人工把这条模型输出修饰成“已提升效果”。这也说明结构合法、产生 diff 和机制真的改善是不同层次的事实。

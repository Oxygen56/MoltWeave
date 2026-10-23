# 模型传输与凭据绑定的发布修复

日期：2026-10-23。这是正式实验结束、v3/v4 源码归档后，由操作者明确授权的常规安全修复。它没有通过 RSI 自动产生，不构成新的任务效果或自进化收益。没有重跑正式实验。

发布版 `src/moltweave/llm.py` 默认拒绝全部重定向，关闭环境代理，要求 HTTPS。URL 中的 userinfo、fragment、query 和控制字符会在请求前被拒绝。`allow_env_proxy=True` 供操作者明确选择的受控部署使用；`allow_http_loopback=True` 仅放行本机合成测试的 HTTP 地址，仍不允许重定向。

密钥与目的地址按同一组解析，优先级为 MOLTWEAVE、OPENAI、ANTHROPIC。选中组缺少必要地址时直接报错，不继续借用另一组配置。模型使用显式 `model` 参数，其次该组的模型变量；没有组内模型变量时沿用项目默认 `deepseek-flash`，不会借用另一组模型配置。

| 凭据来源 | 可用地址 | 地址覆盖边界 |
|---|---|---|
| 显式 `api_key` 参数 | 显式 `base_url`，其次 MOLTWEAVE_API_BASE，最后项目默认 DeepSeek | 操作者显式提供的密钥可以配显式地址 |
| MOLTWEAVE_API_KEY | MOLTWEAVE_API_BASE，未设置时明确使用项目默认 DeepSeek | 不借 OPENAI_BASE_URL 或 ANTHROPIC_BASE_URL；额外的 `base_url` 必须与绑定地址一致 |
| OPENAI_API_KEY | 必须同时设置 OPENAI_BASE_URL | 不借默认地址或其他组地址；额外的 `base_url` 必须一致 |
| ANTHROPIC_API_KEY | 必须同时设置 ANTHROPIC_BASE_URL | 同上，保留成对配置的兼容入口 |

仅设置 legacy key，即使另一组存在地址，也会在创建传输对象前失败。若要把环境中绑定的密钥改发到其他地址，需要操作者同时显式提供 `api_key` 参数。

## 实际验证

最终离线回归：Python 3.15.0，24 项通过，包括 11 项传输／配置测试及 13 项反馈链路测试。原始输出保存在 [model-transport-tests-20261023.txt](model-transport-tests-20261023.txt)，机器摘要见 [JSON](model-transport-tests-20261023.json)。本次没有在其他 Python 版本重复运行新增测试。

- 两个真实本机 HTTP 服务使用合成凭据：从 `127.0.0.1` 重定向到 `localhost` 的另一个端口被拒绝；源服务收到一次请求，目标服务零请求，失败回执不含凭据。
- HTTPS→HTTP 对 301/302/303/307/308 使用同一固定处理器的单元验证；没有部署真实 TLS 攻击服务。HTTP 两服务测试仅通过显式 loopback 开关运行。
- 环境中设置实际本机代理服务、清空 no_proxy 后，默认请求仍直达目标，代理收到零请求；显式代理开关的配置得到检查。
- 非 HTTPS、非法 scheme、URL 凭据／片段／查询／控制字符以及事后改为 HTTP 的地址被拒绝。legacy key 缺少对应地址时不创建传输；三组配置不串用 key、base、model；OPENAI 与 ANTHROPIC 成对配置均能完成合成本机请求。

两次独立的真实公开问题连通验证均成功，每次只有一次物理请求、63 tokens，返回 `{"answer":4}`。第一次验证基本传输修复；追加凭据分组修复后，第二次专门复核当前 ANTHROPIC 成对配置仍可使用 `api.deepseek.com` 的 `deepseek-flash`。两次均默认禁代理、禁 HTTP、禁重定向，没有参与者内容。

公开摘要：[初次传输 smoke](model-transport-smoke-20261023.json)、[最终绑定配置 smoke](model-transport-bound-smoke-20261023.json)。完整消息、返回内容与物理尝试回执保存在被 Git 忽略的 `private/transport-smoke-20261023/`、`private/transport-bound-smoke-20261023/`；公开摘要保留原件路径和 SHA256。这里只验证连通与 JSON 返回，没有测量任务收益、长期投毒抵抗或新增 RSI 效果。

## 历史来源

[归档核验摘要](model-transport-source-boundary-20261023.json) 核对 joint/frozen-P 两臂的 v3、v4 共 28 个固定源码绑定，全部与各自历史 manifest 匹配。发布源码与 v4 的七个固定文件相比只有 `llm.py` 不同。没有修改任何 frozen-source、历史 manifest 或历史调用回执。

最终发布 `llm.py` 原始文件 SHA256：`0b626ee83a66fbb304be7dd974b21feff7955cbfba874250887160ee363d8416`。manifest 使用的是 `sha256(canonical_json(source_text))`，与原始文件 SHA256 的语义不同；不能混用两种 hash，也不能把旧实验结果说成已由这个新客户端重新执行。

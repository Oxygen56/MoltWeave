# 发布前审查与已授权修复

审查日期：2026-10-23。初次只读范围：当前 MoltWeave 工作目录中准备公开的源码、文档、研究示例、反馈合成回执及实验原始调用。初次审查只新增本报告。其后正式实验完成、来源归档，操作者明确授权修复发布版 `llm.py`，新增传输测试并做公开问题的真实连通验证；这些追加变更见下方记录。没有收集参与者数据或部署云服务。

结论：**指定快照未发现真实凭据泄露命中；模型重定向／代理边界与配置串用问题已在发布版修复，新增回归和真实公开问题验证通过。** README 接口名称、外部数据公开范围和实验终态也已校正。发布负责人已选择保留历史 manifest 的本机路径，作为原始非秘密实验元数据；路径文本不授予文件访问权。最终 Git 内容仍需以实际选入清单为准。这不是对任意未来用户数据或长期模型投毒防御的安全认证。

## 发现问题与处理状态

| 优先级 | 文件／字段 | 类别 | 必要修正 |
|---|---|---|---|
| P1，已修复 | `src/moltweave/llm.py`：模型请求；`src/moltweave/feedback.py`：初始 endpoint 绑定 | 凭据传输与第三方目的地边界 | 发布版禁全部重定向、默认禁环境代理、默认要求 HTTPS；URL userinfo／fragment 等请求前拒绝。合成两服务验证目标零请求、源一次请求，HTTPS 降级处理器验证通过。详见 `docs/verification/model-transport-20261023.md`。历史冻结客户端不改写。 |
| P1，已修复 | `src/moltweave/llm.py`：环境配置解析 | 凭据与地址串组 | 原逻辑独立选择 key 和 base，legacy key 缺少对应地址可能误发项目默认地址。发布版按 MOLTWEAVE／OPENAI／ANTHROPIC 成对解析；legacy key 必须有对应 BASE_URL，不借其他组，组内模型优先。隔离环境测试、两类 legacy 本机请求和一次当前配置的真实公开 JSON 复核均通过。 |
| P2，已校正 | `docs/external-evaluation.md`：开头 Status、原始 calls 公开说明 | 文档状态与 Git 公开范围不一致 | 现在明确 completed、48 次模型调用、24 题、零收益，并说明选定公开段落的原始回执会随许可发布；完整数据集仍在外部本地缓存。没有把公开 calls 说成 ignored／私有参与者 Trace。 |
| P2，已校正 | `README.md`：社区接口说明；`docs/community-and-governance.md` | 已实现接口表述 | README 现在写明社区 Python API／本机 HTTP 服务，未宣称不存在的 Community CLI。 |
| P2，负责人已接受保留 | `experiments/external-squad-v2/manifest.json`：`source.cache_path`；`experiments/component-attribution-v1/manifest.json`：`source_experiment`、`provenance.archive` | 本地绝对路径元数据 | 这些字段含本地用户目录信息，属于机器／路径元数据，不是 API key。发布负责人选择保留原始非秘密实验元数据，不篡改历史 manifest；路径文本不授予对应文件访问权。 |
| P2，终态已校正／最终清单待负责人确定 | `ITERATION_PLAN.md`：v3/v4 状态；最终 Git 清单 | 运行中状态与发布时点 | 正式实验已结束，进度表已写明 v3/v4 complete；本文没有重跑任何正式协议。初次审查时尚无已跟踪文件，因此本报告不能等同于对未来任意提交内容的认证。 |

最初的传输 P1 依据是对旧 ModelClient 调用方式以及本机 Python 3.15 标准库 `HTTPRedirectHandler.redirect_request` 的静态核对：其重定向构造只排除 Content-Length、Content-Type 等内容头，并未排除 Authorization。这是代码路径风险，**没有观察到真实调用已经泄露凭据，也没有发送真实凭据进行攻击验证**。追加攻击测试只使用合成凭据和本机服务。社区 TraceClient 原已拒绝重定向，这次修正的是另一条模型调用路径。

## 本次凭据检查结果

末次全量扫描读取了 5,656 个文本文件，解析 5,532 个 JSON，其中 5,165 个包含模型消息字段；运行中的实验仍可能继续新增文件。扫描未打印任何疑似值。

- 对本会话实际配置的模型密钥进行精确内容比对：无命中。
- 常见 provider key、GitHub token、云访问 key、JWT、PEM 私钥模式：无未解释命中。
- 凭据命名字段及敏感文件名检查：未发现实际审批 signing key 或可用的本地使用者 token；`.env.example` 的密钥字段为空。
- `private/` 中检查到的文件都被 Git 忽略；`.approval-key`、常见 key 文件和私有运行目录有忽略规则。
- UUID、Trace ID、consent ID、provider response ID、SHA／内容 hash、请求 hash 和凭据指纹没有被误当成可用凭据。反馈公开授权回执不包含实际认证 token 或其私有登记表。

这属于指定快照的模式／实际配置值扫描和来源核对，不能证明不存在任何未知格式秘密。未检查远端 Git 历史、云端存储、其他工作目录或未来上传内容。

## 原始内容的来源分类

| 路径 | 实际类别 | 核对到的边界 |
|---|---|---|
| `artifacts/feedback-synthetic-live-20261023/` | 明确生成的合成用户和会话，经过真实模型调用 | `run.json` 标明未使用外部用户数据，候选未执行／采用，效果未建立。source Trace 明确标注 synthetic；第三方完整处理授权为真，个人用途与通用用途分开。原始模型回执中的消息属于这份合成样例，不是参与者私有 Trace。 |
| `examples/research/` | 公开 arXiv 材料的精简投影 | 调用投影去掉完整 messages、完整 content 及物理尝试中的全文；证据包明确 code_inspected=false、experiments_reproduced=false、effect_status=not_measured。历史人工决定上下文未开启，selected_count=0；没有构造私人反馈或声称改善了人工判断。 |
| `experiments/joint-*`、`experiments/frozen-p-*` | 作者生成的合成机制任务及模型提案／修复 | manifest 说明 authored synthetic scope；任务上下文的用户、实体和事实由生成器构造。真实模型调用与模拟工具返回须分开解释：这些不是企业工单、真实参与者日志或生产服务执行。 |
| `experiments/external-squad-v2/` | 公开 SQuAD 1.1 的适配 RAG 读出 | 48 次真实 readout 请求含公开问题及选中的段落，不能笼统称合成任务。数据来源、commit、hash 和许可字段保留；`THIRD_PARTY_NOTICES.md` 已将这些数据材料与项目代码许可分开说明。它们不是用户私有 Trace，也不是原生／完整官方榜单评测。 |
| `experiments/*v1`、`*v2` 的失败／中止记录 | 历史基础设施尝试 | 原始失败继续保留，不应改写成效果收益。本次没有清理失败结果。 |

对一次中间快照的实验调用分类，5,035 条 task 调用均匹配合成生成器的任务上下文；48 条机制／策略提案与修复属于这些运行；48 条 external_squad_readout 属于公开 SQuAD 适配数据，没有未分类的 experiment 调用。数字与末次全量扫描不同是因为审查时实验仍在写入，不是将两次快照混成一份固定清单。

## 源码授权边界与效果声明

静态检查未发现上传文本能直接签发 owner 票据、修改固定治理程序或执行任意 Python 的入口。原始 Trace 存储、用途授权和模型处理授权分开；FeedbackPipeline 只产生可追踪候选，模型自报 passed／approved／score 不会成为宿主效果认证。源授权撤回后，派生内容和模型调用回执进入既有撤回链。

权限过滤必须继续在排序前执行。当前 `memory_score`、`rag_score` 和 P 的受限 IR 改变排序／搜索，不改变数据授权集合。工具侧当前是作者提供的本地合成状态，不应把 `read_only` 排序特征解释成已经完成生产写工具的权限控制。owner 标签本身不是登录身份，文档已经将受信任控制面鉴权列为生产补充要求。

README、架构与反馈文档总体保持了下列区别：结构测试不等于模型效果；命名空间迁移不等于跨真实业务系统；P 变更不等于 P 已改善；研究／反馈接通不等于其下游收益已经成立；没有宣称长期投毒和 Sybil 防御已验证。真实反馈候选中退化为原排序的表达式也在文档保留，没有被包装成效果提升。

## 追加修复验证与冻结来源保全

最初只读审查末次核对时，joint-v4 和 frozen-p-v4 的七个固定来源都与当时发布目录匹配。正式实验结束后，追加修复只改发布版 `llm.py`，没有改变冻结源码或旧回执。最终核对 joint/frozen-P 的 v3、v4 共 28 个冻结来源绑定，全部与各自历史 manifest 匹配；发布目录与 v4 的七个固定文件现在仅 `llm.py` 不同。机器结果见 `docs/verification/model-transport-source-boundary-20261023.json`。

最终离线回归实际运行 24 项通过，原始输出见 `docs/verification/model-transport-tests-20261023.txt`。两次真实连通验证各 63 tokens、一次物理请求，均只使用公开算术问题；第一次验证基本传输修复，第二次验证新增成对配置逻辑。完整回执只在被忽略的 `private/transport-smoke-20261023/` 和 `private/transport-bound-smoke-20261023/`，公开摘要在 `docs/verification/`。新增文件的实际配置密钥精确比对无命中，两个私有目录均被 Git 忽略。

这属于操作者授权的实验后常规安全修复，不算自动 RSI 改进。v3/v4 的结果继续归属于其 frozen-source，不能说成由修复后的客户端重新跑出。失败、未测和零收益记录继续保留；不能为让旧 manifest 匹配而覆盖旧源码或改写历史结果。

验证入口：[传输／配置规则与边界](verification/model-transport-20261023.md)、[24 项离线测试原始输出](verification/model-transport-tests-20261023.txt)、[最终真实 JSON smoke 摘要](verification/model-transport-bound-smoke-20261023.json)、[28 个冻结来源绑定核验](verification/model-transport-source-boundary-20261023.json)。发布负责人接手完整测试、暂存和最终 Git 清单扫描；本轮不自行发布或修改归档。

# MoltWeave

**让 Agent 持续改变自身机制，并保留每一次变化的证据。**

[English](README.md) · [完整架构](docs/v0.2-architecture.md) · [迭代计划](ITERATION_PLAN.md) · [评测协议](docs/v0.2-protocol.md)

项目研究机制层的递归自我改进：从自身运行、外部研究和自愿授权的使用 Trace 中发现问题，由模型提出对记忆、RAG、工具选择、失败处理和 Prompt 的修改；寻找改进机会的策略 P 也可以继续演化。

模型权重固定。权限、租户隔离、敏感审批、评分和最终集隔离由固定外层执行。初版使用可组合、可执行的受限表达式程序，尚不运行任意生成的 Python。

## 最重要的演示

沿着一条记录，看到“历史失败 → 自动生成补丁 → 新版本实际加载 → 后续决策改变 → 新任务真正执行 → 独立结果”。每一代都能查看差异、候选、拒绝原因、加载身份和结果。一次 P0→P1 的变化不算持续递归，P1 还必须运行并产生推动 P2 的新历史。

## 本轮实现与实验范围

核心运行器、机制 IR、模型提案、真实候选执行、版本记录、研究证据包、人工决策长期记录、自部署 Trace 接入、审批防重放和记忆纠正接口已实现。它们的结构测试与模型效果实验分开报告。

核心实验使用作者生成的公开合成任务。独立集与命名空间迁移集留出事实、实体、用户和查询表述；该迁移不等于不同真实业务系统。研究输入或社区反馈是否进一步提升 RSI、长期投毒能否被抵抗，需要后续单独实验，不能从接口已实现推出。v0.2 已接入可演化的记忆写入程序，其独立效果仍需正式读数。

## v0.2：记忆闭环与未来搜索

Agent 反复接触同一实体，写入事实、在没有文档或工具时回忆、接收更正，再回忆新事实；同时检验跨轮和延迟回忆。独立的真实模型调用提取事实，固定外层核验来源，M 决定怎么写、怎么读。P 可以改变诊断提示、候选生成提示、候选选择程序与改进算子；新 P 需要实际驱动一次成对未来搜索，取得开发阶段收益后才允许采用。

正式协议是 **20 轮 × 10 条任务流 × 三臂**：只积累记忆且固定 M/P、演化 M 但固定 P、联合演化 M/P。全部 21 代冻结后，从空记忆执行独立事件序列；末代另做禁用记忆和扩大上下文对照。P 的独立验收重新运行未来搜索，直接检查它是否更会产生后续改进。

实现及四轮端到端工程预检已完成。正式运行首次在 421 轮遇到模型账户余额不足（HTTP 402），验证恢复工具后续跑至 **501/600 轮**，再次被余额不足拒绝。全部版本仍未冻结，独立效果目前**不可用**。原始请求、已完成轮次和中断记录均保留，缺失数据不计零分。见[协议](docs/v0.2-protocol.md)、[架构](docs/v0.2-architecture.md)、[一条真实执行链的讲解](docs/v0.2-walkthrough.md)和[当前正式记录](experiments/continual-v02-main/RESULTS.md)。

## 历史 v0.1 结果

已完成两套冻结协议、每套两臂四轮演化，并保留全部版本、拒绝候选、真实调用和独立读数。最新联合演化在作者合成独立集上从 **39/70 提升到 65/70**，命名空间迁移从 **38/70 提升到 60/70**。固定 P 对照末代为 **67/70、65/70**，因此目前不能声称 P 自身带来独立收益。

每一代都能查看自动差异、实际加载、后续搜索决策和独立结果。末轮新 P 尚未驱动下一轮搜索；最终答题不运行 P，不能补成搜索证据。外部 SQuAD 24题检验没有提升；组件实验保留退化及相同请求下的模型波动。

[完整实验与边界](EXPERIMENTS.md) · [最新证据查看页](experiments/joint-v4/index.html) · [实际演化链](experiments/joint-v4/evidence-chain.json)

## 运行

Python 3.11+，无运行时依赖。安装和环境变量见 [English README](README.md#quick-start)。

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
moltweave evolve --output experiments/my-run --generations 4
moltweave evaluate --experiment experiments/my-run
moltweave report --experiment experiments/my-run
```

v0.2 连续实验另用以下入口，三个阶段依次执行：

```bash
moltweave continual run --output experiments/my-continual-run --rounds 20 --streams 10 --concurrency 32
moltweave continual evaluate --output experiments/my-continual-run --concurrency 32
moltweave continual analyze --output experiments/my-continual-run
```

演化和独立评测需要配置真实模型接口，会产生实际调用；分析只读取已有记录。默认不上传使用 Trace。敏感机制补丁在加载或执行前必须由 owner 批准具体版本；模型学习到的偏好不能替代批准。

完整终态与各项完成证据见 [ITERATION_PLAN.md](ITERATION_PLAN.md)。公开实验保留失败和退化，不把离线测试、历史回放或模拟答复当成新机制的实际效果。

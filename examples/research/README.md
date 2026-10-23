# 公开研究输入验证

这里保存真实公开源验证的精简回执，不包含私人 Trace 或虚构人工决定。

- [公开发现与去重](live-discovery-20261023.json)：2026-10-23，arXiv API 首次新增 3 篇及版本，第二次网络抓取新增均为 0。
- [Dream-RSI v2 模型证据包](dream-rsi-v2-model-evidence.json)：实际读取 [arXiv HTML v2](https://arxiv.org/html/2609.14858v2) 的 122,299 个字符，未截断，然后由配置的真实模型分析。公开文件只选取部分模型分析，不是完整响应；保留全文包的哈希。
- [模型调用回执](dream-rsi-v2-model-call-receipt.json)：一次真实请求成功，40,414 输入与 2,696 输出 tokens，结束原因为 `stop`；完整请求/响应保留在本地忽略目录 `private/research-validation/`，公开回执省略全文与完整生成内容。

这证明发现、全文文本提取、实际模型调用和结果保存能连通。它不证明模型理解正确、论文结论复现或人工判断改善；源码检查、实验复现和图表视觉核对均未执行。本次未启用历史决定上下文，也未创造人工反馈。

可重新执行（需要操作者自己配置模型凭据）：

```bash
PYTHONPATH=src python3 -m moltweave.research discover \
  --feed-url 'https://export.arxiv.org/api/query?id_list=2609.14858,2610.14224' \
  --max-results 2 --store private/research-validation
PYTHONPATH=src python3 -m moltweave.research review 2609.14858v2 \
  --store private/research-validation --full-text --model --max-chars 200000
```

`--use-decision-context` 是另外的显式发送开关，默认关闭；启用前应检查 actor、隔离范围、历史理由及模型服务商。其使用与边界见 [研究模块说明](../../docs/research-learning.md)。

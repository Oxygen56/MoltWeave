"""Offline evidence explorer generated exclusively from actual run artifacts."""
from __future__ import annotations
import html
import json
from pathlib import Path
from .common import read_json, write_json


def render_report(folder: Path) -> str:
    manifest = read_json(folder / "manifest.json")
    summary = read_json(folder / "summary.json")
    acceptance = read_json(folder / "independent.json") if (folder / "independent.json").exists() else {"reports": {}}
    versions = []
    for path in sorted((folder / "generations").glob("g*"), key=lambda p: int(p.name[1:])):
        def optional(name):
            return read_json(path / name) if (path / name).exists() else None
        versions.append({"name": path.name, "program": optional("program.json"), "transition": optional("transition.json"),
                         "decisions": optional("policy-decision.json"), "policy": optional("policy-proposal.json"),
                         "diff": (path / "changes.diff").read_text() if (path / "changes.diff").exists() else "No subsequent transition.",
                         "train": {k: v for k, v in (optional("train.json") or {}).items() if k != "traces"}})
    payload = {"manifest": manifest, "summary": summary, "acceptance": acceptance, "versions": versions}
    # Embedded content is data; JSON text cannot terminate the script element.
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MoltWeave · Evolution evidence</title>
<style>
:root{--paper:#f2f5f8;--ink:#193047;--muted:#60748a;--line:#c9d5df;--accent:#2468a0;--warm:#b96131;--panel:#fff}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1220px;margin:auto;padding:48px 32px}header{display:grid;grid-template-columns:1fr auto;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:25px}.wordmark{font:italic 800 58px/1 Georgia,serif;letter-spacing:-3px}small,.sub{color:var(--muted)}h1{font-size:24px;font-weight:550;margin:22px 0 8px}h2{font-size:19px;margin:0 0 12px}p{margin:8px 0}.badge{padding:5px 10px;border:1px solid var(--line);font-size:12px}.chart{width:100%;height:230px;background:var(--panel);border-bottom:1px solid var(--line);margin:25px 0 0}.legend{font-size:13px;display:flex;gap:24px;margin:8px 0 24px}.legend span:before{content:'●';margin-right:7px;color:var(--accent)}.legend span:last-child:before{color:var(--warm)}nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}button{cursor:pointer;border:1px solid var(--line);padding:10px 18px;color:var(--ink);background:var(--panel);font:inherit}button[aria-selected=true]{background:var(--ink);color:white;border-color:var(--ink)}button:focus-visible{outline:3px solid var(--warm);outline-offset:3px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}section{min-width:0;background:var(--panel);border:1px solid var(--line);padding:22px}.wide{grid-column:1/-1}pre{font:12px/1.7 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0;max-height:430px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px 7px;border-bottom:1px solid var(--line)}footer{margin-top:32px;font-size:13px;color:var(--muted)}#status{color:var(--accent);font-size:14px}details{margin-top:12px}summary{cursor:pointer}@media(max-width:720px){main{padding:24px 16px}.wordmark{font-size:44px}header{display:block}.badge{display:inline-block;margin-top:14px}.grid{grid-template-columns:1fr}.wide{grid-column:auto}.chart{height:190px}}
</style><main><header><div><div class="wordmark">MoltWeave</div><h1>每一次蜕变，都有证据。</h1><p class="sub">从失败、机制差异和实际加载，追到下一代决策与独立结果。</p></div><div><span class="badge" id="model"></span></div></header>
<p id="status"></p><svg class="chart" id="chart" viewBox="0 0 1100 230" role="img" aria-label="各代独立评测通过率"></svg><div class="legend"><span>独立验收</span><span>命名空间迁移检验</span></div><nav id="versions" aria-label="选择机制版本"></nav>
<div class="grid"><section class="wide"><h2 id="title"></h2><p id="metrics"></p><table><thead><tr><th>任务家族</th><th>独立验收</th><th>命名空间迁移</th></tr></thead><tbody id="families"></tbody></table></section><section><h2>这一代实际改变了什么</h2><pre id="diff"></pre></section><section><h2>改进策略如何改变下一步</h2><pre id="policy"></pre></section><section class="wide"><h2>加载身份与决策证据</h2><pre id="decisions"></pre><details><summary>查看完整机制程序</summary><pre id="program"></pre></details></section></div><footer>数据来自本次真实模型执行。任务为作者合成；迁移只改变实体、用户、事实与查询命名空间，不代表跨真实业务系统。P 的变化、决策变化与效果归因分别判断。最终结果不用于选择版本。</footer></main>
<script type="application/json" id="evidence">__DATA__</script><script>
const d=JSON.parse(document.getElementById('evidence').textContent), $=id=>document.getElementById(id), txt=(id,v)=>$(id).textContent=typeof v==='string'?v:JSON.stringify(v,null,2);
txt('model',d.manifest.model);txt('status',`实验 ${d.manifest.started_at ? new Date(d.manifest.started_at*1000).toLocaleString() : ''} · ${d.versions.length} 个冻结版本 · ${Object.keys(d.acceptance.reports).length ? '已读取独立结果' : '独立结果尚未运行'}`);
const reports=d.acceptance.reports;function cell(split,name){return reports[split]?.[name]};function rate(r){return r?`${r.passed}/${r.total} (${(r.rate*100).toFixed(1)}%)`:'尚未运行'};
function show(i){const v=d.versions[i];[...$('versions').children].forEach((b,n)=>b.setAttribute('aria-selected',String(n===i)));txt('title',v.name+' · 冻结机制版本');txt('metrics',`独立验收 ${rate(cell('final',v.name))}　｜　命名空间迁移 ${rate(cell('transfer',v.name))}`);txt('diff',v.diff);txt('policy',v.policy||'没有后续策略提案');txt('decisions',v.decisions||{loaded_program_hash:d.summary.final_program_hash,note:'末代程序见独立运行回执'});txt('program',v.program);$('families').replaceChildren();const a=cell('final',v.name)?.families||{};const b=cell('transfer',v.name)?.families||{};Object.keys(a).forEach(k=>{const tr=document.createElement('tr');[k,`${a[k].passed}/${a[k].total}`,b[k]?`${b[k].passed}/${b[k].total}`:'—'].forEach(s=>{const td=document.createElement('td');td.textContent=s;tr.append(td)});$('families').append(tr)})}
d.versions.forEach((v,i)=>{const b=document.createElement('button');b.textContent=v.name;b.onclick=()=>show(i);$('versions').append(b)});show(0);
const svg=$('chart'),ns='http://www.w3.org/2000/svg';function node(tag,attrs,text){const n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;svg.append(n);return n}
[0,.25,.5,.75,1].forEach(y=>{node('line',{x1:65,y1:190-y*150,x2:1050,y2:190-y*150,stroke:'#dce4eb'});node('text',{x:12,y:195-y*150,fill:'#60748a','font-size':12},`${y*100}%`)});
['final','transfer'].forEach((s,j)=>{const pts=[];d.versions.forEach((v,i)=>{const r=cell(s,v.name),x=85+i*900/Math.max(1,d.versions.length-1);if(r){const y=190-r.rate*150;pts.push(`${x},${y}`);node('circle',{cx:x,cy:y,r:5,fill:j?'#b96131':'#2468a0'})}if(j===0)node('text',{x:x-7,y:218,fill:'#193047','font-size':13},v.name)});node('polyline',{points:pts.join(' '),fill:'none',stroke:j?'#b96131':'#2468a0','stroke-width':3})});
</script></html>'''
    page = folder / "index.html"
    page.write_text(template.replace("__DATA__", encoded), encoding="utf-8")
    write_json(folder / "report-data.json", payload)
    rows = ["# Actual experiment readout", "", "Authored synthetic mechanism tasks; not official benchmark reproduction.", "",
            "| Version | Independent | Namespace transfer |", "|---|---|---|"]
    for version in versions:
        values = []
        for split in ("final", "transfer"):
            r = acceptance["reports"].get(split, {}).get(version["name"])
            values.append(f"{r['passed']}/{r['total']} ({r['rate']:.1%})" if r else "not run")
        rows.append(f"| {version['name']} | {' | '.join(values)} |")
    rows += ["", "Policy adoption is prospective. Changed code/decisions alone do not establish improved meta-search.",
             "All generation diffs, rejected candidates, measurement failures and receipts remain in the run directory."]
    (folder / "RESULTS.md").write_text("\n".join(rows) + "\n")
    return str(page.resolve())

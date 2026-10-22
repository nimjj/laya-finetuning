"""Build laya-finetuning/docs/AG50_DASHBOARD.html (one self-contained page, no network needed) from laya-finetuning/docs/ag50_stats.json.

    python laya-finetuning/eval/ag50_analysis.py && python laya-finetuning/eval/build_ag50_dashboard.py
"""
import json
import os

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT
with open(os.path.join(ROOT, "laya-finetuning", "docs", "ag50_stats.json"), encoding="utf-8") as f:
    DATA = json.load(f)

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AG50 Results Dashboard</title>
<style>
:root{
  color-scheme: light;
  --bg:#f6f5f2; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#7d7b75; --line:#e1dfd8; --grid:#ecebe5;
  --ft:#2a78d6; --ol:#eb6834; --st:#1baf7a; --miss:#6250d6; --fa:#52514e; --never:#c9c6bc; --good:#1a7f37;
}
@media (prefers-color-scheme: dark){
  :root:where(:not([data-theme="light"])){
    color-scheme: dark;
    --bg:#121211; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#908e86; --line:#33322f; --grid:#2a2926;
    --ft:#3987e5; --ol:#d95926; --st:#199e70; --miss:#9085e9; --fa:#c3c2b7; --never:#4a4944; --good:#3fb950;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#908e86; --line:#33322f; --grid:#2a2926;
  --ft:#3987e5; --ol:#d95926; --st:#199e70; --miss:#9085e9; --fa:#c3c2b7; --never:#4a4944; --good:#3fb950;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:18px;margin:36px 0 4px}
.sub{color:var(--ink2);margin:0 0 16px;max-width:75ch}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:16px 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px;border-top:4px solid var(--c)}
.tile .n{font-size:34px;font-weight:650;letter-spacing:-.02em;line-height:1.1}
.tile .l{color:var(--ink2);font-size:13px}
.tile .ci{color:var(--muted);font-size:12px;margin-top:2px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink2);margin:0 0 8px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--ink2);font:12px system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
svg .v{fill:var(--ink);font-weight:600}
.note{color:var(--ink2);font-size:13px;margin-top:8px}
.read{border-left:3px solid var(--ft);padding:2px 0 2px 12px;margin:10px 0;color:var(--ink)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600}
.tbl{overflow-x:auto}
.bar{display:inline-block;height:9px;border-radius:2px;vertical-align:middle;margin-left:6px}
details{margin-top:8px} summary{cursor:pointer;color:var(--ink2);font-size:13px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:6px 9px;border-radius:6px;font-size:12px;
  line-height:1.4;max-width:260px;opacity:0;transition:opacity .08s;z-index:10;white-space:pre-line}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;border:1px solid var(--line);color:var(--ink2)}
.sig{color:var(--good);font-weight:600}
footer{color:var(--muted);font-size:12px;margin-top:40px}
</style>
</head>
<body>
<main>
<h1>AG50: how the three engines did on 50 independent long calls</h1>
<p class="sub">50 support calls of 10 to 20 minutes, written and graded by Antigravity (a different AI from the one that wrote our training data). Nothing here is human-labelled. Every interval is a 95% bootstrap interval that resamples whole calls.</p>

<div class="tiles" id="tiles"></div>

<h2>1. The headline: how often does each engine agree with the key?</h2>
<p class="sub">Only the 7 model-judged items are a fair test of the models. The other 4 items are fixed rules that the app runs the same way whichever model is plugged in.</p>
<div class="card"><div id="c-head"></div><div class="read" id="r-head"></div></div>

<h2>2. Is the gap real or just luck?</h2>
<p class="sub">Paired comparison on the same 350 judged items. "Only A right" counts items where one engine was right and the other wrong. McNemar's exact test asks whether that split could be chance.</p>
<div class="card tbl"><table id="t-pairs"></table><div class="read" id="r-pairs"></div></div>

<h2>3. Item by item</h2>
<p class="sub">Balanced accuracy averages "catches real faults" and "leaves good calls alone". 0.50 is a coin flip, 1.00 is perfect. Whiskers are 95% intervals; with 10 to 19 faults per item they are wide.</p>
<div class="card"><div class="legend" id="lg1"></div><div id="c-items"></div><div class="read" id="r-items"></div></div>

<h2>4. What kind of mistakes?</h2>
<p class="sub"><b style="color:var(--miss)">Missed fault</b>: the key says FAIL and the engine said PASS. <b>False alarm</b>: the key says PASS and the engine said FAIL. Bars show counts out of 50 calls.</p>
<div class="card tbl"><table id="t-err"></table><div class="read" id="r-err"></div></div>

<h2>5. Where do the faults get lost? (fine-tuned Laya)</h2>
<p class="sub">Laya never sees a whole call. The app cuts out small snippets first. For each keyed fault, was it even shown to the model?</p>
<div class="card"><div class="legend" id="lg2"></div><div id="c-funnel"></div><div class="read" id="r-funnel"></div></div>

<h2>6. Final scores</h2>
<p class="sub">Each dot is one call. On the diagonal means the engine gave the same score as the key.</p>
<div class="card"><div class="legend" id="lg3"></div><div id="c-scatter"></div><div class="read" id="r-scatter"></div></div>

<h2>7. Does call length matter?</h2>
<div class="card"><div class="legend" id="lg4"></div><div id="c-len"></div><div class="read" id="r-len"></div></div>

<div id="probe-section"></div>

<h2>9. Speed</h2>
<div class="card tbl"><table id="t-speed"></table></div>

<footer>Generated by laya-finetuning/eval/build_ag50_dashboard.py from laya-finetuning/docs/ag50_stats.json. Key: Antigravity, not human-reviewed.</footer>
</main>
<div id="tip"></div>
<script>
const D = /*DATA*/null;
const E = D.engines, NICE = D.nice;
const COL = {"laya-ft":"var(--ft)","ollama":"var(--ol)","laya-stock":"var(--st)"};
const ORDER = ["laya-stock","laya-ft","ollama"];
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
const pct = (x,d=0) => (100*x).toFixed(d)+"%";
const f1 = x => x.toFixed(1);
function svg(w,h){const s=document.createElementNS(NS,"svg");s.setAttribute("viewBox",`0 0 ${w} ${h}`);s.setAttribute("role","img");return s}
function n(tag,attrs={},text){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(text!==undefined)e.textContent=text;return e}
const tip=$("tip");
function hover(el,txt){
  el.addEventListener("mousemove",ev=>{tip.textContent=txt;tip.style.opacity=1;
    tip.style.left=Math.min(ev.clientX+12,innerWidth-270)+"px";tip.style.top=(ev.clientY+14)+"px"});
  el.addEventListener("mouseleave",()=>tip.style.opacity=0);
}
function legend(id,items){ $(id).innerHTML=items.map(([c,t])=>`<span><i style="background:${c}"></i>${t}</span>`).join("") }
const ENG_LEG = ORDER.map(e=>[COL[e],NICE[e]]);

// ---- tiles
const H=D.headline;
$("tiles").innerHTML = ["laya-ft","ollama","laya-stock"].map(e=>{
  const h=H[e];
  return `<div class="tile" style="--c:${COL[e]}"><div class="l">${NICE[e]}</div>
    <div class="n">${pct(h.acc_judged)}</div><div class="l">of the 7 judged items match the key</div>
    <div class="ci">95% interval ${pct(h.acc_judged_ci[0])} to ${pct(h.acc_judged_ci[1])}</div>
    <div class="ci">${f1(h.mae)} points average score error · ${f1(h.sec_per_call)} s per call</div></div>`}).join("");

// ---- 1 headline bars with CI
(function(){
  const rows=["ollama","laya-ft","laya-stock"], W=900, rh=54, top=10, left=150, right=70, H_=top+rows.length*rh+34;
  const s=svg(W,H_), pw=W-left-right, x=v=>left+v*pw;
  for(const t of [0,.25,.5,.75,1]){
    s.append(n("line",{x1:x(t),x2:x(t),y1:top,y2:top+rows.length*rh,stroke:"var(--grid)"}));
    s.append(n("text",{x:x(t),y:top+rows.length*rh+18,"text-anchor":"middle"},pct(t)));
  }
  rows.forEach((e,i)=>{
    const h=H[e], y=top+i*rh+8;
    s.append(n("text",{x:left-10,y:y+17,"text-anchor":"end"},NICE[e]));
    const b=n("rect",{x:left,y:y,width:h.acc_judged*pw,height:24,rx:4,fill:COL[e]});
    hover(b,`${NICE[e]}\n${h.items_judged[0]} of ${h.items_judged[1]} judged items match\n95% interval ${pct(h.acc_judged_ci[0],1)} to ${pct(h.acc_judged_ci[1],1)}`);
    s.append(b);
    const ex=(v)=>x(v);
    s.append(n("line",{x1:ex(h.acc_judged_ci[0]),x2:ex(h.acc_judged_ci[1]),y1:y+12,y2:y+12,stroke:"var(--ink)","stroke-width":2}));
    for(const v of h.acc_judged_ci) s.append(n("line",{x1:ex(v),x2:ex(v),y1:y+5,y2:y+19,stroke:"var(--ink)","stroke-width":2}));
    s.append(n("text",{x:ex(h.acc_judged_ci[1])+8,y:y+17,class:"v"},pct(h.acc_judged)));
  });
  $("c-head").append(s);
  const p=D.pairs["laya-ft vs ollama"];
  $("r-head").innerHTML=`Ollama is ahead of fine-tuned Laya by ${(-100*p.diff_judged).toFixed(1)} points on the judged items. Fine-tuning moved Laya up by ${(100*D.pairs["laya-ft vs laya-stock"].diff_judged).toFixed(1)} points over the stock model. The whiskers of fine-tuned Laya and Ollama overlap, so look at the paired test below before drawing a conclusion.`;
})();

// ---- 2 pairs table
(function(){
  const rows=[["laya-ft vs ollama","Fine-tuned Laya vs Ollama"],["laya-ft vs laya-stock","Fine-tuned Laya vs stock Laya"],["ollama vs laya-stock","Ollama vs stock Laya"]];
  $("t-pairs").innerHTML="<tr><th>Comparison (A vs B)</th><th>A minus B</th><th>95% interval</th><th>Only A right</th><th>Only B right</th><th>McNemar p</th><th>Verdict</th></tr>"+
  rows.map(([k,t])=>{const p=D.pairs[k];const sig=p.mcnemar_p<0.05;
    return `<tr><td>${t}</td><td>${p.diff_judged>=0?"+":""}${(100*p.diff_judged).toFixed(1)} pts</td><td>${(100*p.diff_judged_ci[0]).toFixed(1)} to ${(100*p.diff_judged_ci[1]).toFixed(1)}</td>
    <td>${p.only_a_right}</td><td>${p.only_b_right}</td><td>${p.mcnemar_p<0.001?"&lt;0.001":p.mcnemar_p.toFixed(3)}</td>
    <td>${sig?'<span class="sig">real difference</span>':'<span class="pill">not distinguishable</span>'}</td></tr>`}).join("");
  const p=D.pairs["laya-ft vs ollama"];
  $("r-pairs").innerHTML=`Fine-tuned Laya vs Ollama: Ollama was right on ${p.only_b_right} items where Laya was wrong, and Laya on ${p.only_a_right} where Ollama was wrong. Probability of a split this lopsided by chance, if the two were equal: ${p.mcnemar_p.toFixed(3)}. That is a real, modest gap in Ollama's favour on this data. Fine-tuning's gain over stock Laya is also real.`;
})();

// ---- 3 per item grouped bars (balanced accuracy)
(function(){
  const items=["Empathy","Paraphrasing","Active listening","Ownership","Rapport","Probing","Resolved"];
  const W=900,Hh=320,top=14,left=40,bot=44,pw=W-left-8,ph=Hh-top-bot, gw=pw/items.length;
  const s=svg(W,Hh), y=v=>top+ph-v*ph;
  for(const t of [0,.25,.5,.75,1]){
    s.append(n("line",{x1:left,x2:W-8,y1:y(t),y2:y(t),stroke:t===.5?"var(--muted)":"var(--grid)","stroke-dasharray":t===.5?"4 4":""}));
    s.append(n("text",{x:left-6,y:y(t)+4,"text-anchor":"end"},t.toFixed(2)));
  }
  s.append(n("text",{x:W-12,y:y(.5)-5,"text-anchor":"end"},"coin flip"));
  items.forEach((it,i)=>{
    const g=left+i*gw, bw=Math.min(34,(gw-26)/3);
    s.append(n("text",{x:g+gw/2,y:Hh-bot+20,"text-anchor":"middle"},it));
    ORDER.forEach((e,j)=>{
      const r=D.per_item[it][e], bx=g+(gw-3*bw-8)/2+j*(bw+4);
      const b=n("rect",{x:bx,y:y(r.ba),width:bw,height:Math.max(0,y(0)-y(r.ba)),rx:3,fill:COL[e]});
      hover(b,`${NICE[e]} · ${it}\nbalanced accuracy ${r.ba.toFixed(2)} (95% ${r.ba_ci[0].toFixed(2)} to ${r.ba_ci[1].toFixed(2)})\ncaught ${r.tp} of ${D.per_item[it].key_fail} faults · missed ${r.fn}\nfalse alarms ${r.fp} · correct passes ${r.tn}`);
      s.append(b);
      const cx=bx+bw/2;
      s.append(n("line",{x1:cx,x2:cx,y1:y(r.ba_ci[0]),y2:y(r.ba_ci[1]),stroke:"var(--ink)","stroke-width":1.5}));
    });
  });
  $("c-items").append(s); legend("lg1",ENG_LEG);
  $("r-items").innerHTML="Ownership and Rapport are where fine-tuning paid off most. Active listening is a coin flip for every engine. Ollama is better on Empathy, Probing and Resolved. With 13 to 19 faults per item, the whiskers show that most single-item differences are not individually conclusive; the pooled test above is the stronger evidence.";
})();

// ---- 4 error direction table
(function(){
  const items=["Empathy","Paraphrasing","Active listening","Ownership","Rapport","Probing","Resolved"];
  let h="<tr><th rowspan=2>Item</th><th rowspan=2>Faults in key</th>"+ORDER.map(e=>`<th colspan=2 style="text-align:center;border-left:1px solid var(--line)">${NICE[e]}</th>`).join("")+"</tr><tr>"+ORDER.map(()=>"<th style='border-left:1px solid var(--line)'>Missed fault</th><th>False alarm</th>").join("")+"</tr>";
  for(const it of items){
    const r=D.per_item[it];
    h+=`<tr><td>${it}</td><td>${r.key_fail}</td>`+ORDER.map(e=>{
      const c=r[e]; return `<td style="border-left:1px solid var(--line)">${c.fn}<span class="bar" style="width:${c.fn*3}px;background:var(--miss)"></span></td><td>${c.fp}<span class="bar" style="width:${c.fp*3}px;background:var(--fa)"></span></td>`}).join("")+"</tr>";
  }
  const tot=e=>items.reduce((a,it)=>[a[0]+D.per_item[it][e].fn,a[1]+D.per_item[it][e].fp],[0,0]);
  h+="<tr><td><b>Total</b></td><td></td>"+ORDER.map(e=>{const t=tot(e);return `<td style="border-left:1px solid var(--line)"><b>${t[0]}</b></td><td><b>${t[1]}</b></td>`}).join("")+"</tr>";
  $("t-err").innerHTML=h;
  const a=tot("laya-ft"),o=tot("ollama");
  $("r-err").innerHTML=`Ollama almost never raises a false alarm (${o[1]}) but misses ${o[0]} faults: it is lenient, which is why its final scores average ${H.ollama.bias>0?"+":""}${H.ollama.bias.toFixed(1)} points above the key. Fine-tuned Laya is more balanced (${a[0]} missed, ${a[1]} false alarms) and its scores are nearly unbiased (${H["laya-ft"].bias>0?"+":""}${H["laya-ft"].bias.toFixed(1)}). Stock Laya: ${tot("laya-stock")[0]} missed, ${tot("laya-stock")[1]} false alarms.`;
})();

// ---- 5 funnel
(function(){
  const items=["Empathy","Paraphrasing","Active listening","Ownership","Rapport","Probing","Resolved"];
  const W=900,rh=44,top=8,left=130,right=20,Hh=top+items.length*rh+30,pw=W-left-right;
  const mx=Math.max(...items.map(i=>D.funnel[i].key_fail)), x=v=>left+v/mx*pw;
  const s=svg(W,Hh);
  items.forEach((it,i)=>{
    const f=D.funnel[it], c=f["laya-ft"], y=top+i*rh+6;
    s.append(n("text",{x:left-10,y:y+17,"text-anchor":"end"},it));
    const segs=[["never",f.never_shown,"var(--never)","Never shown to the model (the app's snippet rules found nothing to ask)"],
                ["miss",c.missed_when_shown,"var(--miss)","Shown to the model, which said PASS"],
                ["got",c.caught_when_shown,"var(--ft)","Shown to the model, which said FAIL (caught)"]];
    let cx=left;
    for(const [k,v,col,desc] of segs){
      if(!v) continue;
      const r=n("rect",{x:cx+1,y:y,width:Math.max(2,x(v)-x(0)-2),height:24,rx:3,fill:col});
      hover(r,`${it}: ${v} of ${f.key_fail} keyed faults\n${desc}`);
      s.append(r);
      if(x(v)-x(0)>20) s.append(n("text",{x:cx+(x(v)-x(0))/2,y:y+16,"text-anchor":"middle",style:"fill:#fff;font-weight:600"},v));
      cx+=x(v)-x(0);
    }
    s.append(n("text",{x:cx+8,y:y+16,class:"v"},`${f.key_fail} faults`));
  });
  $("c-funnel").append(s);
  legend("lg2",[["var(--never)","Never reached the model"],["var(--miss)","Reached the model, missed"],["var(--ft)","Reached the model, caught"]]);
  const a=D.funnel["Active listening"],o=D.funnel["Ownership"],w=D.window;
  $("r-funnel").innerHTML=`${a.never_shown} of ${a.key_fail} Active-listening faults and ${o.never_shown} of ${o.key_fail} Ownership faults never reached the model, so no amount of model training could catch them. Ownership is the clearest case: when the snippet reached it, fine-tuned Laya caught ${o["laya-ft"].caught_when_shown} of ${o.shown}. Paraphrasing sees only about ${Math.round(w.paraphrase_words_seen_mean)} words and Resolved about ${Math.round(w.resolved_words_seen_mean)} words of a ${Math.round(w.call_words_mean)}-word call.`;
})();

// ---- 6 scatter
(function(){
  const W=900,Hh=330,gap=18,pw=(W-2*gap)/3,m={l:34,b:30,t:20,r:8};
  const s=svg(W,Hh);
  ORDER.forEach((e,i)=>{
    const ox=i*(pw+gap), w=pw-m.l-m.r, h=Hh-m.t-m.b;
    const X=v=>ox+m.l+v/100*w, Y=v=>m.t+h-v/100*h;
    s.append(n("text",{x:ox+m.l,y:12,class:"v"},`${NICE[e]} · avg error ${f1(H[e].mae)}`));
    for(const t of [0,50,100]){
      s.append(n("line",{x1:X(0),x2:X(100),y1:Y(t),y2:Y(t),stroke:"var(--grid)"}));
      s.append(n("text",{x:X(0)-5,y:Y(t)+4,"text-anchor":"end"},t));
      s.append(n("text",{x:X(t),y:Hh-12,"text-anchor":"middle"},t));
    }
    s.append(n("line",{x1:X(0),y1:Y(0),x2:X(100),y2:Y(100),stroke:"var(--muted)","stroke-dasharray":"4 4"}));
    D.scores.forEach(r=>{
      const c=n("circle",{cx:X(r.key),cy:Y(r[e]),r:5,fill:COL[e],"fill-opacity":.8,stroke:"var(--surface)","stroke-width":2});
      hover(c,`${r.call} (${Math.floor(r.dur/60)} min)\nkey ${r.key} · ${NICE[e]} ${r[e]}`);
      s.append(c);
    });
    if(i===1) s.append(n("text",{x:ox+pw/2,y:Hh-0,"text-anchor":"middle"},"score in the key"));
  });
  $("c-scatter").append(s); legend("lg3",ENG_LEG);
  $("r-scatter").innerHTML=`Rank agreement with the key (Spearman): Ollama ${H.ollama.spearman.toFixed(2)}, fine-tuned Laya ${H["laya-ft"].spearman.toFixed(2)}, stock Laya ${H["laya-stock"].spearman.toFixed(2)}. Ollama ranks calls best but scores them ${H.ollama.bias.toFixed(1)} points too high on average; fine-tuned Laya is nearly unbiased (${H["laya-ft"].bias>0?"+":""}${H["laya-ft"].bias.toFixed(1)}) but noisier. That is why their average errors tie.`;
})();

// ---- 7 length
(function(){
  const rows=D.by_length, W=900,Hh=290,top=14,left=40,bot=48,pw=W-left-8,ph=Hh-top-bot,gw=pw/rows.length;
  const s=svg(W,Hh), y=v=>top+ph-v*ph;
  for(const t of [0,.25,.5,.75,1]){
    s.append(n("line",{x1:left,x2:W-8,y1:y(t),y2:y(t),stroke:"var(--grid)"}));
    s.append(n("text",{x:left-6,y:y(t)+4,"text-anchor":"end"},pct(t)));
  }
  rows.forEach((r,i)=>{
    const g=left+i*gw,bw=Math.min(44,(gw-30)/3);
    s.append(n("text",{x:g+gw/2,y:Hh-bot+20,"text-anchor":"middle"},r.bucket));
    s.append(n("text",{x:g+gw/2,y:Hh-bot+36,"text-anchor":"middle",style:"fill:var(--muted)"},`${r.n} calls`));
    ORDER.forEach((e,j)=>{
      const bx=g+(gw-3*bw-8)/2+j*(bw+4);
      const b=n("rect",{x:bx,y:y(r[e]),width:bw,height:y(0)-y(r[e]),rx:3,fill:COL[e]});
      hover(b,`${NICE[e]} · ${r.bucket}\n${pct(r[e],1)} of judged items match (${r.n} calls)`);
      s.append(b);
      s.append(n("text",{x:bx+bw/2,y:y(r[e])-5,"text-anchor":"middle",class:"v"},pct(r[e])));
    });
  });
  $("c-len").append(s); legend("lg4",ENG_LEG);
  $("r-len").innerHTML="Each bucket holds only 10 to 15 calls, so differences between buckets are noisy. Read it as: no engine collapses on the longest calls, and no clean trend with length.";
})();

// ---- probe section
(function(){
  const P=D.probe && D.probe["laya-ft"]; if(!P) return;
  const items=["Empathy","Paraphrasing","Active listening","Ownership","Rapport","Probing","Resolved"];
  const S=D.probe["laya-stock"]||{};
  const ci=c=>c?`${c[0].toFixed(2)} to ${c[1].toFixed(2)}`:"";
  let h=`<h2>8. Did training make the model better at telling good from bad? And would a better cutoff help?</h2>
  <p class="sub"><b>AUC</b> measures how well the model <i>ranks</i> faulty calls above good ones, ignoring any cutoff (0.50 = no skill, 1.00 = perfect). It is the cleanest test of what training changed. "Re-tuned" picks the best cutoff on one half of the calls and scores it on the other half (200 random splits). It is still an upper bound, because the key is the same data. For Active listening and Ownership the AUC also reflects the snippet rule that decides whether the model is asked at all.</p>
  <div class="card tbl"><table><tr><th>Item</th><th>Calls the model was asked</th><th>AUC fine-tuned (95%)</th><th>AUC stock</th><th>Training effect on AUC</th><th>Balanced acc. now</th><th>Re-tuned (cross-val.)</th></tr>`;
  for(const it of items){const r=P[it]; if(!r) continue; const st=S[it]||{};
    const d=r.auc_minus_stock, dc=r.auc_minus_stock_ci; const sig=dc&&(dc[0]>0||dc[1]<0);
    h+=`<tr><td>${it}</td><td>${r.n_called} of 50</td><td>${r.auc.toFixed(2)} <span style="color:var(--muted)">(${ci(r.auc_ci)})</span></td><td>${st.auc!==undefined?st.auc.toFixed(2):"-"}</td>
    <td>${d>=0?"+":""}${d.toFixed(2)} <span style="color:var(--muted)">(${ci(dc)})</span> ${sig?'<span class="sig">'+(d>0?"clear gain":"clear loss")+'</span>':'<span class="pill">no clear change</span>'}</td>
    <td>${r.deployed_ba.toFixed(2)}</td><td>${r.cv_ba.toFixed(2)} ${r.cv_ba-r.deployed_ba>0.05?'<span class="sig">+'+(r.cv_ba-r.deployed_ba).toFixed(2)+'</span>':''}</td></tr>`}
  h+=`</table><div class="read" id="r-probe"></div></div>`;
  $("probe-section").innerHTML=h;
  $("r-probe").innerHTML=`Training clearly improved the model's ranking on only one item, Rapport. For Empathy, Paraphrasing and Resolved the change is not distinguishable from zero (Resolved even trends down), and Paraphrasing ranking is weak for both models. Probing ranks well but its cutoff is set badly, so re-tuning it is the biggest cheap win in this table. Where AUC is already high and balanced accuracy is low, the lever is the cutoff or the snippet rule, not more training.`;
})();

// ---- speed table
(function(){
  $("t-speed").innerHTML="<tr><th>Engine</th><th>Seconds per call</th><th>Relative to fine-tuned Laya</th><th>Runs on</th></tr>"+
  ["laya-ft","laya-stock","ollama"].map(e=>`<tr><td>${NICE[e]}</td><td>${f1(H[e].sec_per_call)}</td><td>${(H[e].sec_per_call/H["laya-ft"].sec_per_call).toFixed(1)}x</td><td>${e==="ollama"?"local LLM (llama3.1)":"CPU, 421M-parameter model"}</td></tr>`).join("");
})();
</script>
</body>
</html>
"""

html = PAGE.replace("/*DATA*/null", json.dumps(DATA))
out = os.path.join(ROOT, "laya-finetuning", "docs", "AG50_DASHBOARD.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", out, f"({len(html) // 1024} KB)")

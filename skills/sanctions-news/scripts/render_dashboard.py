#!/usr/bin/env python3
"""Generate one offline comparison dashboard from researcher JSON reports only."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


STYLE = r'''
:root { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size:16px;
  line-height:1.5; color:#18353d; background:#eef3f4; color-scheme:light; }
* { box-sizing:border-box; } body { margin:0; } button,select,textarea { font:inherit; }
button { cursor:pointer; color:inherit; } button:focus-visible,select:focus-visible,textarea:focus-visible {
  outline:3px solid #166e88; outline-offset:3px; }
header { background:#163e49; color:white; padding:22px 26px; } h1 { font-size:1.6rem; margin:0 0 8px; }
p { margin:8px 0; } .small { font-size:.83rem; } .muted { color:#4d6268; }
.layout { display:grid; grid-template-columns:220px minmax(0,1fr); min-height:75vh; }
nav { padding:24px 16px; background:#e1ebed; border-right:1px solid #bdcfd3; }
nav button { display:block; width:100%; background:transparent; text-align:left; padding:14px 12px;
  border:1px solid transparent; border-radius:8px; margin-bottom:8px; }
nav button[aria-current=true] { background:white; border-color:#17677b; box-shadow:inset 4px 0 #17677b; }
nav small { display:block; color:#50676f; } #picker-label { display:none; }
main { padding:24px; min-width:0; } h2 { font-size:1.4rem; margin:0; } .toolbar { display:flex;
  flex-wrap:wrap; gap:12px; align-items:center; justify-content:space-between; margin-bottom:18px; }
.action { background:white; border:1px solid #9cb6bd; border-radius:7px; padding:10px 14px; }
.summary { border-left:4px solid #477985; padding:6px 14px; margin:12px 0 20px; }
.scroll { overflow:auto; border:1px solid #b3c7cc; border-radius:10px; background:white; }
table { border-collapse:separate; border-spacing:0; width:var(--table-width,100%); table-layout:fixed; }
caption { text-align:left; padding:10px 18px; }
th,td { text-align:left; vertical-align:top; padding:18px; width:250px; border-bottom:1px solid #c8d6da;
  border-right:1px solid #c8d6da; overflow-wrap:anywhere; font-weight:400; }
thead th { background:#f2f7f8; } th.ours,td.ours { position:sticky; left:0; z-index:1;
  background:#f0f6f8; border-right:2px solid #6e929c; width:230px; }
thead .ours { z-index:2; } .field-label { display:block; text-transform:uppercase; letter-spacing:.06em;
  font-size:.72rem; font-weight:750; color:#526d75; margin-bottom:10px; }
.cell-open,.article-open { padding:0; border:0; background:transparent; text-align:left; width:100%; }
.article-open { font-weight:650; color:#135f75; text-decoration:underline; text-underline-offset:3px; }
.chip { display:inline-block; border-radius:5px; padding:3px 8px; font-size:.76rem; font-weight:750;
  margin:10px 0 2px; background:#e4f1ea; color:#23523a; }
.chip.different { background:#a32d24; color:white; } .chip.not-stated { background:#e9edf0; color:#465b63; }
td.different { background:#fff0ed; box-shadow:inset 4px 0 #b74738; }
.value { display:block; font-size:1rem; } .stated { font-size:.76rem; color:#526970; }
.verdict { border-top:1px solid #c8d6da; padding-top:10px; font-size:.84rem; }
.judge { margin-top:16px; padding-top:12px; border-top:1px dashed #a9bdc3; }
.judge label { display:block; font-size:.78rem; margin:5px 0; }
select,textarea { max-width:100%; width:100%; border:1px solid #8faab3; border-radius:5px;
  background:white; padding:8px; color:#18353d; } textarea { min-height:64px; resize:vertical; }
.save-state { font-size:.72rem; min-height:1.5em; color:#345d4d; } #notice { min-height:1.5em; }
#export { margin-top:18px; min-height:130px; font-family:monospace; }
dialog { position:fixed; inset:0 0 0 auto; margin:0; height:100dvh; max-height:100dvh; width:min(680px,65vw);
  max-width:100vw; border:0; border-left:1px solid #789ba4; padding:0; color:#18353d; }
dialog::backdrop { background:#102d3680; } .panel-head { padding:20px 24px; background:#edf4f5;
  border-bottom:1px solid #b5cbd0; } .panel-head h2 { margin-top:12px; font-size:1.2rem; }
#article-text { overflow:auto; height:calc(100% - 245px); padding:18px 26px 60px; white-space:pre-wrap; }
#article-text p { margin:0 0 18px; } mark { background:#ffe071; color:#172d34; outline:2px solid #b77e00; }
#source-line { font-weight:600; } [hidden] { display:none!important; }
footer { margin-top:24px; font-size:.8rem; color:#4d6268; }
.decision-box { border:0; padding:0; margin:0; min-width:0; }
.decision-box legend { font-weight:700; margin-bottom:8px; }
.decision-choices { display:grid; gap:8px; margin:12px 0; }
.article-choice { text-align:left; font-size:.85rem; }
.article-choice[aria-pressed=true] { background:#163e49; color:white; border-color:#163e49; }
button:disabled { cursor:not-allowed; opacity:.55; }
.reason-label { display:block; font-size:.83rem; font-weight:650; margin-top:12px; }
.support-list { border:0; padding:0; margin:12px 0; font-size:.8rem; }
.support-list legend { font-size:.8rem; font-weight:500; }
.support-list label { display:flex; gap:6px; align-items:center; margin:6px 0; }
.support-list .chip { margin:0; } .decision-rule { font-size:.78rem; border-left:3px solid #9b6928; padding-left:8px; }
.event-headers th { background:#dcebed; font-weight:700; border-top:3px solid #56828d; padding:10px 18px; }
#timeline { margin:20px 0 26px; } #timeline h3 { margin:0 0 6px; }
.event-lane { margin:12px 0; padding:10px 14px; background:white; border:1px solid #b7ccd0; border-radius:8px; }
.lane-title { font-size:.8rem; color:#4d6268; margin:0 0 8px; }
.timeline-marks { display:flex; flex-wrap:wrap; gap:10px; border-left:3px solid #56828d; padding-left:12px; }
.timeline-mark { background:#f2f7f8; border:1px solid #a6bfc5; border-radius:7px; padding:9px 12px;
  text-align:left; flex:1 1 230px; max-width:100%; }
.timeline-mark time { display:block; font-size:.8rem; font-weight:700; color:#185b6e; }
.timeline-line { display:block; font-size:.86rem; } .lane-ending { font-size:.83rem; margin:8px 0 0; font-weight:650; }
.article-controls { display:none; } .article-controls label { display:block; width:100%; }
.timeline-node { flex:1 1 230px; min-width:0; }
.timeline-node .timeline-mark { width:100%; }
.timeline-edge { display:block; width:100%; border:0; border-top:3px dashed #9b6928;
  background:#fff8e9; padding:8px; text-align:left; font-size:.78rem; overflow-wrap:anywhere; }
.timeline-edge.edge-confirmed,.timeline-edge.edge-analyst-confirmed { border-top-style:solid; }
.timeline-edge.edge-confirmed { border-color:#17677b; background:#edf6f7; }
.timeline-edge.edge-analyst-confirmed { border-color:#68539b; background:#f5f1fc; }
.link-review { margin:16px 0; }
.link-card { margin:12px 0; padding:12px; border:1px solid #bdcfd3; border-left:4px dashed #9b6928;
  border-radius:6px; background:#fffdf7; min-width:0; overflow-wrap:anywhere; }
.link-card.edge-confirmed,.link-card.edge-analyst-confirmed { border-left-style:solid; }
.link-card.edge-confirmed { border-left-color:#17677b; }
.link-card.edge-analyst-confirmed { border-left-color:#68539b; }
.link-card.edge-rejected { background:#f0f2f3; border-left-color:#68777c; }
.link-card h5 { margin:0; font-size:.88rem; }
.link-reasons { font-size:.83rem; margin:8px 0; }
.link-reasons summary { cursor:pointer; text-decoration:underline; }
.link-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.link-actions [aria-pressed=true] { background:#163e49; color:white; }
.link-card textarea { min-height:60px; }
.timeline-marks { border-left:0; padding-left:0; }
@media(max-width:700px) { header { padding:18px 16px; } h1 { font-size:1.35rem; }
  .layout { display:block; } nav { padding:12px 16px; border-right:0; } #subject-list { display:none; }
  #picker-label { display:block; } main { padding:18px 12px; } th,td { width:240px; padding:14px; }
  th.ours,td.ours { width:210px; } dialog { width:100%; border:0; }
  .panel-head { padding:16px; } #article-text { padding:18px 18px 60px; } }
@media(max-width:700px) {
  .article-controls { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0; }
  .article-controls select { display:block; min-width:0; width:100%; }
  table { width:100%; } th,td { width:62%; padding:12px; }
  th.ours,td.ours { width:38%; } .media-col:not(.selected),.event-headers [data-event]:not(.selected) { display:none; }
  .event-headers th { padding:10px 12px; } .timeline-marks { display:grid; }
  .timeline-mark { width:100%; } .value { font-size:.93rem; }
}
'''

DECISION_LOGIC = r'''
const articleChoices = ['Not our person','Our person, not relevant','Need more info','Investigate'];
function recordArticleDecision(existing, candidate, reports) {
  const report = reports.find(r => r.subject.id === candidate.subject);
  const article = report?.comparisons.find(a => a.article_id === candidate.article);
  if (!article || !articleChoices.includes(candidate.choice)) throw new Error('Choose a decision.');
  if (typeof candidate.reason !== 'string' || !candidate.reason.trim()) throw new Error('Write a reason before saving.');
  if (candidate.reason.length > 600) throw new Error('Keep the reason within 600 characters.');
  if (!Array.isArray(candidate.support) || new Set(candidate.support).size !== candidate.support.length
      || candidate.support.some(f => !Object.hasOwn(article.fields, f))) throw new Error('Invalid supporting cells.');
  if (typeof candidate.time !== 'string' || !candidate.time) throw new Error('Missing decision time.');
  const record = {subject:candidate.subject,article:candidate.article,choice:candidate.choice,
    reason:candidate.reason.trim(),support:[...candidate.support],time:candidate.time,
    supporting_cells:candidate.support.map(field => ({field,...article.fields[field]}))};
  return [...existing.filter(d => d.subject !== record.subject || d.article !== record.article), record];
}
const linkKey = link => link.article_id + '--' + link.to_article_id;
function recordLinkDecision(existing, candidate, reports) {
  const report = reports.find(r => r.subject.id === candidate.subject);
  const link = report?.links.find(l => l.article_id === candidate.article_id
    && l.to_article_id === candidate.to_article_id && l.tier === 'SUGGESTED');
  if (!link || !['Confirm','Reject'].includes(candidate.choice)) throw new Error('Choose a suggested link and Confirm or Reject.');
  if (typeof candidate.reason !== 'string' || !candidate.reason.trim()) throw new Error('Write a reason before saving.');
  if (candidate.reason.length > 600) throw new Error('Keep the reason within 600 characters.');
  if (typeof candidate.time !== 'string' || !candidate.time) throw new Error('Missing decision time.');
  const record = {subject:candidate.subject,article_id:link.article_id,to_article_id:link.to_article_id,
    choice:candidate.choice,reason:candidate.reason.trim(),time:candidate.time,
    suggested_tier:link.tier,suggested_reasons:[...link.reasons]};
  return [...existing.filter(d => d.subject !== record.subject || linkKey(d) !== linkKey(record)),record];
}
function timelineGroups(report, decisions) {
  // Rebuild from immutable algorithm groups: rejection can always undo a visual join.
  const roots = new Map(report.events.map((e,i)=>[i,i]));
  const root = i => { while (roots.get(i)!==i) i=roots.get(i); return i; };
  const owner = new Map(report.events.flatMap((e,i)=>e.article_ids.map(id=>[id,i])));
  for (const link of report.links) {
    const decision = decisions.find(d=>d.subject===report.subject.id && linkKey(d)===linkKey(link));
    if (link.tier==='SUGGESTED' && decision?.choice==='Reject') continue;
    const a=root(owner.get(link.article_id)), b=root(owner.get(link.to_article_id));
    roots.set(a,b);
  }
  const groups = new Map();
  report.events.forEach((event,i)=> {
    const key=root(i);
    if (!groups.has(key)) groups.set(key,{event_id:event.event_id,article_ids:[],marks:[],endings:[]});
    const group=groups.get(key); group.article_ids.push(...event.article_ids); group.marks.push(...event.marks);
    if (event.ending) group.endings.push(event.ending);
  });
  return [...groups.values()].map(group=>({...group,
    marks:group.marks.toSorted((a,b)=>a.date.localeCompare(b.date)||a.article_id.localeCompare(b.article_id))}));
}
'''


SCRIPT = r'''
'use strict';
''' + DECISION_LOGIC + r'''
const data = JSON.parse(document.getElementById('data').textContent);
const storageKey = 'sanctions-news-decisions-v1-' + data.fingerprint;
let decisions = [];
const notice = document.getElementById('notice');
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
  if (!Array.isArray(saved)) throw new Error('Invalid saved choices');
  decisions = saved.filter(d => d && ['Same','Different',"Can't tell"].includes(d.choice)
    && typeof d.note === 'string' && typeof d.time === 'string'
    && data.reports.some(r => r.subject.id === d.subject && r.comparisons.some(a =>
      a.article_id === d.article && Object.hasOwn(a.fields, d.field))));
} catch (_) { notice.textContent = 'Saved choices could not be read. Copy decisions before closing.'; }
const articleStorageKey = storageKey + '-articles';
let articleDecisions = [];
try {
  const saved = JSON.parse(localStorage.getItem(articleStorageKey) || '[]');
  if (!Array.isArray(saved)) throw new Error('Invalid saved decisions');
  for (const d of saved) {
    try { articleDecisions = recordArticleDecision(articleDecisions, d, data.reports); }
    catch (_) { notice.textContent = 'An invalid saved article decision was ignored.'; }
  }
} catch (_) { notice.textContent = 'Saved article decisions could not be read. Keep a JSON copy.'; }
const linkStorageKey = storageKey + '-links';
let linkDecisions = [];
let linkStorageFailed = false;
try {
  const saved = JSON.parse(localStorage.getItem(linkStorageKey) || '[]');
  if (!Array.isArray(saved)) throw new Error('Invalid saved link decisions');
  for (const d of saved) {
    try { linkDecisions = recordLinkDecision(linkDecisions, d, data.reports); }
    catch (_) { notice.textContent = 'An invalid saved link decision was ignored.'; }
  }
} catch (_) { notice.textContent = 'Saved link decisions could not be read. Keep a JSON copy.'; }
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls; return n; };
const labels = {name:'Name',profile:'Profile',age:'Age',position:'Position held',key_people:'Key people',
  part_in_story:'Their part in the story',stage:'Stage'};
const storyFields = ['part_in_story','stage'];
let current, opener, selectedArticle;
const phone = window.matchMedia('(max-width:700px)');
const sameKey = (d, article, field) => d.subject === current.subject.id && d.article === article && d.field === field;
function judge(article, field) {
  const box = el('details', undefined, 'judge'); box.append(el('summary','Record your judgment'));
  const key = current.subject.id + '-' + article.article_id + '-' + field;
  const saved = decisions.find(d => sameKey(d,article.article_id,field));
  const label = el('label','Your judgment'); label.htmlFor = key;
  const select = el('select'); select.id = key; select.dataset.article = article.article_id; select.dataset.field = field;
  for (const choice of ['', 'Same','Different',"Can't tell"]) {
    const option = el('option', choice || 'Choose, if reviewed'); option.value = choice; select.append(option);
  }
  select.value = saved?.choice || '';
  const noteLabel = el('label','Short note'); noteLabel.htmlFor = key + '-note';
  const note = el('textarea'); note.id = key + '-note'; note.maxLength = 600; note.value = saved?.note || '';
  const state = el('div',saved ? 'Saved on this browser' : '', 'save-state'); state.setAttribute('aria-live','polite');
  const save = () => {
    decisions = decisions.filter(d => !sameKey(d,article.article_id,field));
    if (select.value) decisions.push({subject:current.subject.id,article:article.article_id,field,
      choice:select.value,note:note.value,time:new Date().toISOString()});
    try { localStorage.setItem(storageKey,JSON.stringify(decisions));
      state.textContent = select.value ? 'Saved on this browser' : 'Choice removed';
    } catch (_) { state.textContent = 'Not saved. Use Copy my decisions before closing.'; }
  };
  select.addEventListener('change',save); note.addEventListener('input',() => {
    if (select.value) save(); else state.textContent = 'Choose a judgment to save this note.';
  });
  box.append(label,select,noteLabel,note,state); return box;
}
function decisionBox(article) {
  const box = el('fieldset', undefined, 'decision-box'); box.dataset.article = article.article_id;
  box.append(el('legend', 'Your article decision'));
  const saved = articleDecisions.find(d => d.subject === current.subject.id && d.article === article.article_id);
  let choice = saved?.choice || '';
  const choices = el('div',undefined,'decision-choices');
  const state = el('p', saved ? 'Saved on this browser' : 'No article decision saved.', 'save-state');
  state.setAttribute('aria-live','polite');
  const note = el('textarea'); note.required=true; note.maxLength=600;
  note.id = current.subject.id + '-' + article.article_id + '-reason'; note.value = saved?.reason || '';
  const reasonLabel = el('label','Reason (required)','reason-label'); reasonLabel.htmlFor=note.id;
  const supports = el('fieldset',undefined,'support-list');
  supports.append(el('legend','Tick the row chips that support your reason (optional)'));
  for (const [field, cell] of Object.entries(article.fields)) {
    const label = el('label'), tick = el('input'); tick.type='checkbox'; tick.value=field;
    tick.checked = saved?.support.includes(field) || false;
    tick.addEventListener('change',()=>state.textContent='Unsaved changes. Save your decision.');
    label.append(tick,el('span',labels[field] + ': '),el('span',cell.status,'chip ' + cell.status.toLowerCase().replaceAll(' ','-')));
    supports.append(label);
  }
  const save = el('button','Save decision','action'); save.type='button'; save.dataset.requiresReason='true';
  const refresh = () => { save.disabled = !choice || !note.value.trim();
    for (const b of choices.children) b.setAttribute('aria-pressed',String(b.textContent===choice)); };
  for (const value of articleChoices) {
    const b = el('button',value,'article-choice action'); b.type='button'; b.dataset.decisionChoice=value;
    b.addEventListener('click',()=> { choice=value; refresh();
      state.textContent=note.value.trim() ? 'Unsaved changes. Save your decision.' : 'Write a reason before saving.'; });
    choices.append(b);
  }
  note.addEventListener('input',()=> { refresh(); state.textContent='Unsaved changes. Save your decision.'; });
  save.addEventListener('click',()=> {
    try {
      articleDecisions = recordArticleDecision(articleDecisions, {subject:current.subject.id,
        article:article.article_id,choice,reason:note.value,
        support:[...supports.querySelectorAll('input:checked')].map(n=>n.value),time:new Date().toISOString()}, data.reports);
    } catch (e) { state.textContent=e.message; return; }
    try { localStorage.setItem(articleStorageKey,JSON.stringify(articleDecisions)); state.textContent='Saved on this browser'; }
    catch (_) { state.textContent='Not saved. Use Copy my decisions before closing.'; }
  });
  box.append(choices,el('p','A Different on role or employer alone is weak evidence. A Different on age or a hard identifier is strong.','decision-rule'),
    reasonLabel,note,supports,save,state); refresh(); return box;
}
function openArticle(article, field, trigger, timelineSentence=null) {
  opener = trigger;
  $('article-title').textContent = article.headline;
  $('article-meta').textContent = article.outlet + ' · ' + article.date + ' · ' + sourceStatus(article);
  const sentence = timelineSentence || (storyFields.includes(field) ? article.story_evidence[field]
    : field ? article.fields[field].source_sentence : null);
  $('source-line').textContent = sentence ? (field ? labels[field] : 'Timeline') + ': source sentence highlighted below.'
    : field ? labels[field] + ': Not stated. No supporting sentence. Read the full article and use your judgment.'
    : 'Full supplied article. Pick a comparison cell to highlight its source sentence.';
  const container = $('article-text'); container.replaceChildren();
  const at = sentence ? article.body.indexOf(sentence) : -1;
  if (at >= 0) {
    container.append(document.createTextNode(article.body.slice(0,at)));
    const mark = el('mark',sentence); mark.id = 'source-sentence'; container.append(mark);
    container.append(document.createTextNode(article.body.slice(at + sentence.length)));
  } else container.textContent = article.body;
  $('article-panel').showModal();
  const headHeight = document.querySelector('.panel-head').getBoundingClientRect().height;
  container.style.height = `calc(100% - ${headHeight}px)`;
  container.scrollTop = 0;
  if (at >= 0) $('source-sentence').scrollIntoView({block:'center'});
  $('close-panel').focus();
}
function sourceStatus(article) { const s = article.source_status;
  return s.execution + ' · ' + s.result + ' · ' + s.freshness + ' (snapshot ' + s.as_of + ')'; }
function linkDecision(link) {
  return linkDecisions.find(d=>d.subject===current.subject.id && linkKey(d)===linkKey(link));
}
function linkStyle(link) {
  if (link.tier==='CONFIRMED') return {cls:'edge-confirmed',label:'CONFIRMED · algorithm link'};
  const choice=linkDecision(link)?.choice;
  if (choice==='Confirm') return {cls:'edge-analyst-confirmed',label:'Analyst confirmed visual link · report unchanged'};
  if (choice==='Reject') return {cls:'edge-rejected',label:'Rejected by analyst · not joined by this link'};
  return {cls:'edge-suggested',label:'suggested, analyst to confirm'};
}
function showLinkReasons(link) {
  const details=$('link-' + linkKey(link)).querySelector('details');
  details.open=true; details.scrollIntoView({block:'center'}); details.querySelector('summary').focus();
}
function linkCard(link) {
  const style=linkStyle(link), saved=linkDecision(link);
  const box=el('section',undefined,'link-card ' + style.cls); box.id='link-' + linkKey(link);
  box.dataset.link=linkKey(link); box.dataset.tier=link.tier;
  box.append(el('h5',link.to_article_id + ' → ' + link.article_id),el('p',style.label,'link-status small'));
  const details=el('details',undefined,'link-reasons');
  details.append(el('summary','Why these articles may be related · reasons'));
  const list=el('ul'); for (const reason of link.reasons) list.append(el('li',reason)); details.append(list); box.append(details);
  if (link.tier==='CONFIRMED') {
    box.append(el('p','Algorithm-confirmed relationship. Analyst suggestion controls do not change it.','small muted'));
    return box;
  }
  const label=el('label','Reason for Confirm or Reject (required)','reason-label');
  const note=el('textarea'); note.id=box.id + '-reason'; label.htmlFor=note.id;
  note.required=true; note.maxLength=600; note.value=saved?.reason || '';
  const state=el('p',saved ? (linkStorageFailed ? 'In memory only. Copy my decisions before closing. '
    : 'Saved on this browser. ') + saved.choice + ': ' + saved.reason : 'No analyst link decision saved.','save-state');
  state.setAttribute('aria-live','polite');
  const actions=el('div',undefined,'link-actions');
  for (const choice of ['Confirm','Reject']) {
    const b=el('button',choice,'action'); b.type='button'; b.dataset.linkChoice=choice;
    b.setAttribute('aria-pressed',String(saved?.choice===choice)); b.disabled=!note.value.trim();
    b.addEventListener('click',()=> {
      try { linkDecisions=recordLinkDecision(linkDecisions,{subject:current.subject.id,
        article_id:link.article_id,to_article_id:link.to_article_id,choice,reason:note.value,
        time:new Date().toISOString()},data.reports); }
      catch (e) { state.textContent=e.message; return; }
      try { localStorage.setItem(linkStorageKey,JSON.stringify(linkDecisions)); linkStorageFailed=false; }
      catch (_) { linkStorageFailed=true;
        notice.textContent='Link decision is in memory only, not saved. Use Copy my decisions before closing.'; }
      drawTimeline();
      const replacement=$('link-' + linkKey(link));
      replacement.querySelector('details').open=true;
      replacement.querySelector('[data-link-choice="' + choice + '"]').focus({preventScroll:true});
    });
    actions.append(b);
  }
  note.addEventListener('input',()=> {
    for (const b of actions.children) b.disabled=!note.value.trim();
    state.textContent='Unsaved reason. Confirm or Reject to save.';
  });
  box.append(label,note,actions,state,el('p','Visual grouping only. Neither choice changes findings, states, summary or report verdict. Only an algorithm CONFIRMED link can supply a case-closed lane ending.','small muted'));
  return box;
}
function drawTimeline() {
  const timeline=$('timeline'); timeline.replaceChildren(el('h3','News timeline'),
    el('p','Publication dates, earliest first in each lane. Dashed edges are suggested, analyst to confirm. Solid edges identify algorithm or analyst-confirmed visual links; these are labelled separately. Tap an edge for its reasons.','small muted'),
    el('p',current.finding_count + ' report findings · analyst link decisions never change this count or the report.','small report-finding-count'));
  for (const event of timelineGroups(current,linkDecisions)) {
    const lane=el('section',undefined,'event-lane'); lane.dataset.event=event.event_id;
    lane.dataset.articles=event.marks.map(m=>m.article_id).join(',');
    lane.append(el('h4',event.marks.map(m=>m.article_id).join(' → ') + ' · ' + event.marks.length + (event.marks.length===1 ? ' article' : ' articles'),'lane-title'));
    const marks=el('div',undefined,'timeline-marks');
    for (const mark of event.marks) {
      const node=el('div',undefined,'timeline-node');
      for (const link of current.links.filter(l=>l.article_id===mark.article_id)) {
        const style=linkStyle(link); if (style.cls==='edge-rejected') continue;
        const edge=el('button',link.to_article_id + ' → ' + link.article_id + ' · ' + style.label,'timeline-edge ' + style.cls);
        edge.type='button'; edge.dataset.link=linkKey(link);
        edge.addEventListener('click',()=>showLinkReasons(link)); node.append(edge);
      }
      const article=current.comparisons.find(a=>a.article_id===mark.article_id);
      const b=el('button',undefined,'timeline-mark'); b.dataset.article=mark.article_id;
      const date=el('time',mark.date); date.dateTime=mark.date;
      b.append(date,el('span',mark.line,'timeline-line'));
      b.addEventListener('click',()=> { selectArticle(mark.article_id); openArticle(article,null,b,mark.source_sentence); }); node.append(b); marks.append(node);
    }
    lane.append(marks);
    for (const ending of [...new Set(event.endings)]) {
      const closures=current.links.filter(l=>l.tier==='CONFIRMED' && event.article_ids.includes(l.article_id)
        && current.comparisons.find(a=>a.article_id===l.article_id).stage==='case closed');
      // Even when a suggested edge visually touches a closed algorithm group,
      // identify the exact confirmed pair: the closure does not spread to it.
      if (ending==='case closed' && !closures.length) continue;
      const text=ending==='case closed' ? ending + ' · CONFIRMED: '
        + closures.map(l=>l.to_article_id + ' → ' + l.article_id).join('; ') : ending;
      const endingNode=el('p',text,'lane-ending'); endingNode.dataset.ending=ending; lane.append(endingNode);
    }
    timeline.append(lane);
  }
  const review=el('section',undefined,'link-review');
  review.setAttribute('aria-label','Article relationship review');
  review.append(el('h4','Article relationships · analyst review'));
  if (!current.links.length) review.append(el('p','No article links supplied for this subject.','small muted'));
  for (const link of current.links) review.append(linkCard(link));
  timeline.append(review);
}
function selectArticle(id) {
  selectedArticle=id;
  const picker=$('article-picker'); picker.value=id;
  document.querySelectorAll('.media-col').forEach(n=>n.classList.toggle('selected',n.dataset.article===id));
  const event=current.events.find(e=>e.article_ids.includes(id));
  document.querySelectorAll('.event-headers [data-event]').forEach(n=> {
    n.classList.toggle('selected',n.dataset.event===event.event_id);
    n.colSpan=phone.matches ? 1 : current.events.find(e=>e.event_id===n.dataset.event).article_ids.length;
  });
  const index=[...picker.options].findIndex(o=>o.value===id);
  $('previous-article').disabled=index<=0; $('next-article').disabled=index>=picker.options.length-1;
  $('article-position').textContent='Article ' + (index+1) + ' of ' + picker.options.length;
  const columns=document.querySelector('table colgroup'); columns.replaceChildren();
  const ours=el('col'); ours.style.width=phone.matches ? '38%' : '230px'; columns.append(ours);
  for (let i=0;i<(phone.matches ? 1 : picker.options.length);i++) {
    const col=el('col'); col.style.width=phone.matches ? '62%' : '250px'; columns.append(col);
  }
}
function choose(sid) {
  current = data.reports.find(r => r.subject.id === sid) || data.reports[0];
  location.hash = current.subject.id; $('picker').value = current.subject.id;
  document.querySelectorAll('#subject-list button').forEach(b => b.setAttribute('aria-current',String(b.dataset.sid===current.subject.id)));
  $('subject-name').textContent = current.subject.name;
  $('subject-kind').textContent = current.subject.type === 'person' ? 'Person' : 'Company';
  $('summary').textContent = current.summary;
  drawTimeline();
  const events=[...current.events].sort((a,b)=>
    current.comparisons.findIndex(x=>a.article_ids.includes(x.article_id)) - current.comparisons.findIndex(x=>b.article_ids.includes(x.article_id)));
  const articles = events.flatMap(e=>e.article_ids.map(id=>current.comparisons.find(a=>a.article_id===id)));
  const fields = [...(current.subject.type === 'person'
    ? ['name','profile','age','position'] : ['name','profile','key_people']), ...storyFields];
  $('article-count').textContent = articles.length + ' media articles. On a wide screen, scroll sideways. On a phone, pick one article at a time. Our subject stays in view.';
  const picker=$('article-picker'); picker.replaceChildren();
  for (const article of articles) { const option=el('option',article.date + ' · ' + article.headline); option.value=article.article_id; picker.append(option); }
  const table = el('table'); table.style.setProperty('--table-width',(230 + 250 * articles.length) + 'px');
  const caption = el('caption','Subject and media comparison'); caption.className = 'small'; table.append(caption);
  table.append(el('colgroup'));
  const head = el('thead'), groups = el('tr',undefined,'event-headers');
  groups.append(el('th','Event groups','ours'));
  for (const event of events) {
    const group=el('th',event.event_id + ' · ' + event.article_ids.length + (event.article_ids.length===1 ? ' article' : ' articles'));
    group.colSpan=event.article_ids.length; group.scope='colgroup'; group.dataset.event=event.event_id;
    groups.append(group);
  }
  head.append(groups);
  const headrow = el('tr'), ours = el('th','Our subject','ours'); ours.scope='col';
  headrow.append(ours);
  for (const article of articles) {
    const th = el('th'); th.scope='col';
    const button = el('button',article.headline,'article-open'); button.dataset.article = article.article_id;
    button.addEventListener('click',()=>openArticle(article,null,button));
    th.append(button,el('p',article.outlet + ' · ' + article.date,'small'),
      el('p',sourceStatus(article),'small muted'),el('p',article.verdict,'verdict')); headrow.append(th);
  }
  head.append(headrow); table.append(head); const body = el('tbody');
  for (const field of fields) {
    const row = el('tr'); row.dataset.field = field;
    const our = el('th',undefined,'ours'); our.scope='row'; our.append(el('span',labels[field],'field-label'));
    const story = storyFields.includes(field);
    const values = story ? [] : [...new Set(articles.map(a => a.fields[field].subject_value).filter(v => v!==null))];
    if (field === 'age' && values.length > 1) {
      for (const value of values) our.append(el('p',value + ' at ' + articles.filter(a=>a.fields.age.subject_value===value).map(a=>a.date).join(', ')));
    } else our.append(el('span',story ? 'Article context, not an identity comparison' : values[0] || 'Not stated','value'));
    row.append(our);
    for (const article of articles) {
      const cell = story ? {value:article[field] === 'not stated' ? null : article[field],
        source_sentence:article.story_evidence[field],status:article[field] === 'not stated' ? 'Not stated' : 'Stated'}
        : article.fields[field];
      const td = el('td',undefined,cell.status.toLowerCase().replaceAll(' ','-'));
      const button = el('button',undefined,'cell-open'); button.dataset.article=article.article_id; button.dataset.field=field;
      button.setAttribute('aria-label',labels[field] + ' from ' + article.headline + ': ' + (cell.value || 'Not stated') + '. Open article');
      button.append(el('span',cell.value || 'Not stated','value'),el('span',cell.status,'chip ' + td.className));
      if (cell.value) button.append(el('span',' · stated in article','stated'));
      if (field==='age') button.append(el('p','Our subject at this date: ' + cell.subject_value,'small muted'));
      if (cell.comparison_note) button.append(el('p',cell.comparison_note,'small muted'));
      button.addEventListener('click',()=>openArticle(article,field,button)); td.append(button);
      if (cell.reported_only) td.append(el('p','Media reports: ' + cell.reported_only.value,'small'));
      if (!story && cell.status==='Not stated') td.append(judge(article,field)); row.append(td);
    }
    body.append(row);
  }
  const decisionRow = el('tr'); decisionRow.dataset.field='article_decision';
  const decisionLabel = el('th',undefined,'ours'); decisionLabel.scope='row';
  decisionLabel.append(el('span','Your decision','field-label'),el('p','Decide identity before relevance. A missing field is not a mismatch.','small'));
  decisionRow.append(decisionLabel);
  for (const article of articles) { const td=el('td'); td.append(decisionBox(article)); decisionRow.append(td); }
  body.append(decisionRow); table.append(body);
  for (const row of table.querySelectorAll('tr:not(.event-headers)')) {
    [...row.children].slice(1).forEach((n,i)=> { n.classList.add('media-col'); n.dataset.article=articles[i].article_id; });
  }
  $('comparison').replaceChildren(table); $('comparison').scrollLeft=0; selectArticle(articles[0].article_id);
}
for (const report of data.reports) {
  const b = el('button',report.subject.name); b.dataset.sid=report.subject.id;
  b.append(el('small',report.subject.type === 'person' ? 'Person' : 'Company'));
  b.addEventListener('click',()=>choose(report.subject.id)); $('subject-list').append(b);
  const option=el('option',report.subject.name); option.value=report.subject.id; $('picker').append(option);
}
$('picker').addEventListener('change',e=>choose(e.target.value));
$('article-picker').addEventListener('change',e=>selectArticle(e.target.value));
for (const [id, step] of [['previous-article',-1],['next-article',1]]) {
  $(id).addEventListener('click',()=> { const picker=$('article-picker'); selectArticle(picker.options[picker.selectedIndex+step].value); });
}
phone.addEventListener('change',()=>selectArticle(selectedArticle));
$('close-panel').addEventListener('click',()=>$('article-panel').close());
$('article-panel').addEventListener('close',()=>opener?.focus());
window.addEventListener('hashchange',()=> { if (location.hash.slice(1)!==current?.subject.id) choose(location.hash.slice(1)); });
$('copy').addEventListener('click',async()=> {
  const json=JSON.stringify({cell_marks:decisions,article_decisions:articleDecisions,link_decisions:linkDecisions},null,2);
  $('export').hidden=false; $('export').value=json;
  try { await navigator.clipboard.writeText(json); notice.textContent='Decisions copied as JSON.'; }
  catch (_) { $('export').focus(); $('export').select();
    const copied=document.execCommand('copy'); notice.textContent=copied ? 'Decisions copied as JSON.'
      : 'Copy was blocked. Select and copy the JSON below.'; }
});
choose(location.hash.slice(1));
'''


STORY_CHOICES = {
    'part_in_story': {'accused', 'under investigation', 'sanctioned', 'sued someone',
                      'witness', 'mentioned only', 'not stated'},
    'stage': {'allegation', 'investigation', 'charge', 'settlement', 'designation or restriction',
              'case closed', 'not stated'},
}


def validate_story(article):
    if not isinstance(article.get('event_id'), str) or not re.fullmatch(r'EVT-[0-9]{3}', article['event_id']):
        raise ValueError('Missing or invalid event metadata; rerun research')
    for field, choices in STORY_CHOICES.items():
        if article.get(field) not in choices:
            raise ValueError('Missing or invalid story category; rerun research')
        sentence = article.get('story_evidence', {}).get(field)
        if article[field] == 'not stated':
            if sentence is not None:
                raise ValueError('Not stated story category must have no sentence')
        elif not sentence or sentence not in article['body'].splitlines():
            raise ValueError('Story category needs an original article line')


def report_links(report):
    """Validate supplied edges, never derive a round-3 edge from raw event ids."""
    articles = {a['article_id']: a for a in report['comparisons']}
    if len(articles) != len(report['comparisons']):
        raise ValueError('Repeated article id')
    # Historical reports predate links. Their explicit resolution is a confirmed
    # algorithm link; raw event ids alone do not manufacture an edge.
    links = report.get('links', [
        {'article_id': f['resolution']['article_id'], 'to_article_id': f['article_id'],
         'tier': 'CONFIRMED', 'reasons': ['Explicit linked resolution in the report.']}
        for f in report['findings'] if f.get('resolution')])
    if not isinstance(links, list):
        raise ValueError('Report links must be a list')
    seen, result = set(), []
    for link in links:
        if not isinstance(link, dict):
            raise ValueError('Invalid report link')
        later, earlier = link.get('article_id'), link.get('to_article_id')
        if not isinstance(later, str) or not isinstance(earlier, str) or later not in articles or earlier not in articles:
            raise ValueError('Link endpoints must belong to this subject report')
        if articles[later]['date'] <= articles[earlier]['date']:
            raise ValueError('Link must point from a strictly later article to an earlier article')
        if link.get('tier') not in ('CONFIRMED', 'SUGGESTED'):
            raise ValueError('Invalid link tier')
        reasons = link.get('reasons')
        if not isinstance(reasons, list) or not reasons or any(not isinstance(r, str) or not r.strip() for r in reasons):
            raise ValueError('Link reasons must be nonempty plain strings')
        if (later, earlier) in seen:
            raise ValueError('Repeated report link')
        seen.add((later, earlier))
        result.append({'article_id': later, 'to_article_id': earlier,
                       'tier': link['tier'], 'reasons': list(reasons)})
    return sorted(result, key=lambda l: (articles[l['article_id']]['date'], l['article_id'], l['to_article_id']))


def event_groups(report):
    """Immutable algorithm groups. Suggested joins exist only in the browser view."""
    links = report_links(report)
    articles = sorted(report['comparisons'], key=lambda a: (a['date'], a['article_id']))
    roots = {a['article_id']: a['article_id'] for a in articles}

    def root(aid):
        while roots[aid] != aid:
            aid = roots[aid]
        return aid

    for link in links:
        if link['tier'] == 'CONFIRMED':
            roots[root(link['article_id'])] = root(link['to_article_id'])
    # Preserve old report table membership for historical replay only. Current
    # reports always supply links (including []), so event_id cannot join them.
    if 'links' not in report:
        legacy = {}
        for article in articles:
            previous = legacy.setdefault(article['event_id'], article['article_id'])
            roots[root(article['article_id'])] = root(previous)
    findings, endings = {}, {}
    confirmed = {(l['article_id'], l['to_article_id']) for l in links if l['tier'] == 'CONFIRMED'}
    for record in report['findings']:
        aid = record['article_id']
        findings[aid] = record
        resolution = record.get('resolution')
        if resolution:
            findings[resolution['article_id']] = resolution
            if (resolution['article_id'], aid) in confirmed:
                endings[root(aid)] = resolution['stage']
        elif record['state'] == 'cleared' and any(later == aid for later, _ in confirmed):
            endings[root(aid)] = record['stage']
        elif record['state'] == 'historical status unknown':
            endings.setdefault(root(aid), record['assessment'])
    groups = {}
    for article in articles:
        aid, eid = article['article_id'], article['event_id']
        finding = findings.get(aid)
        line = article['headline']
        sentence = article['fields']['name']['source_sentence']
        if finding:
            sentence = finding['quote']
            line = ('reported delisting' if finding.get('state') == 'reported delisting'
                    else finding['event'])
            for pattern in (r'^(The .+?) (?:designated|imposed|fined|announced)\b',
                            r', (the .+?) (?:is investigating|said|delisted|imposed)\b'):
                authority = re.search(pattern, sentence)
                if authority:
                    line += ' · ' + authority[1]
                    break
        if not sentence or sentence not in article['body']:
            raise ValueError('Timeline mark needs a verbatim article sentence')
        group = groups.setdefault(root(aid), {'event_id': eid, 'article_ids': [], 'marks': [],
                                              'ending': endings.get(root(aid))})
        group['article_ids'].append(aid)
        group['marks'].append({'article_id': aid, 'date': article['date'],
                               'line': line, 'source_sentence': sentence})
    labels = [g['event_id'] for g in groups.values()]
    for group in groups.values():
        if labels.count(group['event_id']) > 1:
            group['event_id'] += ' / ' + group['article_ids'][0]
    return list(groups.values())


def render_dashboard(reports):
    if not reports:
        raise ValueError('No report JSON files found')
    ids = set()
    payload = []
    for report in reports:
        sid = report['subject']['id']
        if sid in ids:
            raise ValueError('Repeated subject id')
        ids.add(sid)
        if 'comparisons' not in report:
            raise ValueError('Report has no comparison evidence; rerun research')
        for article in report['comparisons']:
            validate_story(article)
            for cell in article['fields'].values():
                if cell['status'] not in ('Same', 'Different', 'Not stated'):
                    raise ValueError('Invalid comparison status')
                if cell['status'] == 'Not stated':
                    if cell['value'] is not None or cell['source_sentence'] is not None:
                        raise ValueError('Not stated cell must have no value or sentence')
                elif not cell['source_sentence'] or cell['source_sentence'] not in article['body'] or cell['value'] not in cell['source_sentence']:
                    raise ValueError('Ungrounded media value')
        payload.append({**{k: report[k] for k in ('subject', 'summary', 'comparisons')},
                        'events': event_groups(report), 'links': report_links(report),
                        'finding_count': len(report['findings']), 'findings': report['findings']})
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]
    data = json.dumps({'reports': payload, 'fingerprint': fingerprint}, ensure_ascii=False).replace('<', '\\u003c')
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; connect-src \'none\'; '
            'base-uri \'none\'; form-action \'none\'">'
            '<title>Subject and media comparison</title><style>' + STYLE + '</style></head><body>'
            '<header><h1>Subject and media comparison</h1>'
            '<p>The page never fills a Not stated cell itself. Read the article and record your own judgment.</p>'
            '<p class="small">Invented sample only. All names are placeholders. Local in style only; no real place names. '
            'No live news search. A matching field is not an identity decision.</p></header>'
            '<div class="layout"><nav aria-label="Subjects"><div id="subject-list"></div>'
            '<label id="picker-label">Pick a subject<select id="picker"></select></label></nav><main>'
            '<div class="toolbar"><div><span id="subject-kind" class="small muted"></span>'
            '<h2 id="subject-name"></h2></div><button id="copy" class="action">Copy my decisions</button></div>'
            '<p id="summary" class="summary"></p><section id="timeline" aria-label="News timeline"></section>'
            '<p id="article-count" class="small muted"></p>'
            '<div class="article-controls"><label>Compare one article<select id="article-picker"></select></label>'
            '<button id="previous-article" class="action">Previous</button><button id="next-article" class="action">Next</button>'
            '<span id="article-position" class="small" role="status"></span></div>'
            '<div id="comparison" class="scroll" tabindex="0" aria-label="Scrollable comparison table"></div>'
            '<p id="notice" class="small" role="status"></p>'
            '<label class="small" for="export">Decision JSON (shown after copying)</label>'
            '<textarea id="export" hidden readonly></textarea>'
            '<footer>Rule-based extraction for this sample text only. Same and Different compare stated values, not people. '
            'Choices are yours, saved on this browser for this sample version only. They never change the report verdict. '
            'Private or restricted browser storage may not persist. Keep a JSON copy.</footer></main></div>'
            '<dialog id="article-panel" aria-labelledby="article-title"><div class="panel-head">'
            '<button id="close-panel" class="action">Close article</button><h2 id="article-title"></h2>'
            '<p id="article-meta" class="small"></p><p id="source-line" class="small"></p></div>'
            '<div id="article-text" tabindex="0"></div></dialog>'
            '<script id="data" type="application/json">' + data + '</script><script>' + SCRIPT + '</script>'
            '<noscript>Enable JavaScript to use this offline comparison. No network is used.</noscript></body></html>\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        paths = sorted(args.reports.glob('SUB-*.json'))
        if args.out.suffix.lower() != '.html' or args.out.resolve() in [p.resolve() for p in paths]:
            raise ValueError('Output must be a separate HTML file')
        rendered = render_dashboard([json.loads(p.read_text(encoding='utf-8')) for p in paths])
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Dashboard render failed: ' + str(exc), file=sys.stderr)
        return 1
    print(str(args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())

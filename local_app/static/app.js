'use strict';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
const supplied = fragment.get('session');
if (supplied) sessionStorage.setItem('local-session', supplied);
history.replaceState(null, '', location.pathname);
const token = sessionStorage.getItem('local-session') || '';
let current = null, job = null, inputLimit = 200000;
const bytes = text => new TextEncoder().encode(text).length;
function updateInputMeters() {
  const used = current ? current.inputs.reduce((n,x)=>n+bytes(x.text),0) : 0;
  for (const [input,meter,existing] of [['description','description-size',0],['followup','followup-size',used]]) {
    const total=bytes($(input).value)+existing;
    $(meter).textContent=`${total.toLocaleString()} / ${inputLimit.toLocaleString()} UTF-8 bytes${total>inputLimit?' · Too large; shorten the text before saving.':total>6000?' · Long-text local processing will take additional time.':''}`;
    $(meter).classList.toggle('over-limit',total>inputLimit);
  }
}
function checkInput(text,existing=0) {
  if(bytes(text)+existing>inputLimit)throw new Error(`Text exceeds the ${inputLimit.toLocaleString()}-byte project limit. Nothing was saved or truncated; your pasted text is still in the form.`);
}
$('description').addEventListener('input',updateInputMeters);
$('followup').addEventListener('input',updateInputMeters);
updateInputMeters();
function message(text, error=false) { $('message').textContent=text; $('message').className=error?'error':''; }
async function api(path, body) {
  const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'X-Local-Token':token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let data;try{data=await response.json();}catch{}throw new Error(data?.error||'Local request failed');}
  return response.json();
}
function item(text, tag='p') {const el=document.createElement(tag);el.textContent=text;return el;}
async function status() {
  const s=await api('/api/status');
  inputLimit=s.input_limit_bytes;updateInputMeters();$('app-version').textContent='LOCAL PROTOTYPE '+s.app_version;
  $('runtime-status').textContent=!s.installed?'Install Ollama first, then start local AI.':!s.running?'Ready to start. No client data leaves this computer.':`Local-only AI running · ${s.models.length?'Downloaded: '+s.models.join(', '):'download a model to begin.'}`;
  const topic=$('research-topic').value;
  $('research-topic').replaceChildren(...s.topics.map(x=>{const option=item(x,'option');option.value=x;return option;}));
  if(topic)$('research-topic').value=topic;
  queryPreview();
  if(s.active_job&&!job) watch(s.active_job);
}
async function projects() {
  const list=await api('/api/projects');
  $('project-list').replaceChildren(...list.map(p=>{const button=item(p.title+' · '+p.revisions+' report(s)','button');button.className='project-link';button.onclick=()=>run(()=>openProject(p.id));return button;}));
}
async function openProject(id) {
  current=await api('/api/projects/'+id);
  updateInputMeters();
  $('create-panel').hidden=true;$('project-panel').hidden=false;
  $('project-title').textContent=current.title;
  $('project-summary').textContent=`${current.inputs.length} input(s) · ${current.sources.length} public source(s) · ${current.revisions.length} saved revision(s)`;
  $('input-list').replaceChildren(...current.inputs.map(x=>item(x.text)));
  $('source-list').replaceChildren(...current.sources.map(x=>item(x.title+' · '+x.accessed)));
  $('revision').replaceChildren(...current.revisions.map(r=>{const option=item('Revision '+r.number+' · '+r.created,'option');option.value=r.number;return option;}));
  $('report-panel').hidden=!current.revisions.length;
  if(current.revisions.length){$('revision').value=current.revisions.at(-1).number;showReport();}
  else $('report').removeAttribute('src');
}
function showReport() {if(current&&$('revision').value)$('report').src='/reports/'+current.id+'/'+$('revision').value;}
async function run(fn) {try{message('');await fn();}catch(e){message(e.message,true);}}
function watch(id) {
  job=id;$('job-panel').hidden=false;
  const poll=async()=>{
    try {
      const j=await api('/api/jobs/'+id);$('job-message').textContent=j.message;
      if(j.status==='running'){setTimeout(poll,1000);return;}
      job=null;$('job-panel').hidden=true;message(j.message,j.status==='failed');
      await status();await projects();if(current)await openProject(current.id);
    }catch(e){job=null;message(e.message,true);}
  };poll();
}
$('start-runtime').onclick=()=>run(async()=>watch((await api('/api/runtime/start',{})).job_id));
$('pull-model').onclick=()=>run(async()=>watch((await api('/api/runtime/pull',{model:$('model').value})).job_id));
$('cancel-job').onclick=()=>run(()=>api('/api/jobs/cancel',{}));
$('shutdown').onclick=()=>run(async()=>{await api('/api/shutdown',{});message('Local app stopped. You can close this tab.');});
$('new-project').onclick=()=>{current=null;updateInputMeters();$('create-panel').hidden=false;$('project-panel').hidden=true;};
$('create-form').onsubmit=e=>{e.preventDefault();run(async()=>{checkInput($('description').value);const p=await api('/api/projects',{title:$('title').value,description:$('description').value});$('create-form').reset();await projects();await openProject(p.id);message('Saved on this computer. Start local AI, download a model, then generate the brief.');});};
$('followup-form').onsubmit=e=>{e.preventDefault();run(async()=>{checkInput($('followup').value,current.inputs.reduce((n,x)=>n+bytes(x.text),0));await api('/api/projects/'+current.id+'/inputs',{text:$('followup').value});$('followup').value='';await openProject(current.id);message('Follow-up saved. Generate a new brief to update the assessment; earlier reports remain available.');});};
$('generate').onclick=()=>run(async()=>watch((await api('/api/projects/'+current.id+'/generate',{model:$('model').value,expected_revision:current.revisions.length})).job_id));
$('revision').onchange=showReport;
function queryPreview() {$('query-preview').textContent='Exact outbound query: '+$('research-topic').value+' products research';}
$('research-topic').onchange=queryPreview;
$('public-search').onclick=()=>{
  const popup=window.open('about:blank','_blank');
  if(popup)popup.opener=null;
  run(async()=>{try{
    const result=await api('/api/projects/'+current.id+'/search',{topic:$('research-topic').value});
    if(popup)popup.location.replace(result.url);else message('Your browser blocked the search window. Allow popups for this local page and retry.');
  }catch(e){if(popup)popup.close();throw e;}});
};
$('source-form').onsubmit=e=>{e.preventDefault();run(async()=>{message('Retrieving the explicitly selected public page…');await api('/api/projects/'+current.id+'/sources',{url:$('source-url').value,approved:$('source-approved').checked});$('source-form').reset();await openProject(current.id);message('Public source saved locally. Generate a new brief to incorporate it.');});};
document.querySelectorAll('[data-format]').forEach(button=>button.onclick=()=>run(async()=>{
  const format=button.dataset.format;
  const response=await fetch('/api/reports/'+current.id+'/'+$('revision').value+'?format='+format,{headers:{'X-Local-Token':token}});
  if(!response.ok)throw new Error('Report download failed');
  const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='disclosure.'+format;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}));
run(async()=>{if(!token)throw new Error('Open the local app with its launcher to start a session.');await status();await projects();});

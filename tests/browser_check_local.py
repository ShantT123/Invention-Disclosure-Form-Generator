"""End-to-end application checks with explicitly synthetic model responses, not model-quality validation."""
from pathlib import Path
import json
import sys
import tempfile
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from local_app.server import App,make_server
from local_fixtures import FakeRuntime

out=Path(sys.argv[1]) if len(sys.argv)>1 else None
if out:out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
 app=App(directory,FakeRuntime());server=make_server(app)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 origin=f'http://127.0.0.1:{server.server_port}'
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=browser.new_page(viewport={'width':1440,'height':1100})
   external=[];errors=[]
   page.on('request',lambda req:external.append(req.url) if not req.url.startswith(origin) else None)
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   page.goto(origin+'/#session='+app.token)
   page.wait_for_function("() => document.getElementById('runtime-status').textContent.includes('running')")
   assert 'session' not in page.url
   page.locator('#title').fill('Fictional test client')
   description='A fictional home controller watches continuous water flow while away and closes a valve after a selected duration.'
   page.locator('#description').fill(description)
   page.locator('#create-form button').click()
   page.wait_for_selector('#project-panel:not([hidden])')
   page.locator('#generate').click()
   page.wait_for_selector('#report-panel:not([hidden])',timeout=20000)
   frame=page.frame_locator('#report')
   frame.locator('#brief-understanding').wait_for()
   assert 'water controller' in frame.locator('#brief-understanding').inner_text()
   assert not frame.locator('#full-analysis').evaluate('(el)=>el.open')
   for extension in ('html','md','json'):
    with page.expect_download() as got:page.locator('[data-format="'+extension+'"]').click()
    data=Path(got.value.path()).read_text()
    if extension=='json':
     first=json.loads(data);assert first['input_summary']==description
    else:assert 'Fictional test client' in data
   page.locator('#followup').fill('The timer reset behavior is still undecided.')
   page.locator('#followup-form button').click()
   page.wait_for_function("() => document.getElementById('project-summary').textContent.includes('2 input')")
   page.locator('#generate').click()
   page.wait_for_function("() => document.getElementById('revision').options.length===2",timeout=20000)
   frame.locator('#brief-strength').wait_for()
   expect(frame.locator('#brief-strength')).to_contain_text('Revision 2')
   page.locator('#revision').select_option('1')
   frame.locator('#brief-strength').wait_for()
   expect(frame.locator('#brief-strength')).to_contain_text('Revision 1')
   pid=app.store.list()[0]['id']
   assert app.store.revision(pid,1)==first
   assert len(app.store.get(pid)['inputs'])==2
   assert app.store.revision(pid,2)['patent_assessment']['previous_review_id']==first['review_id']
   # Project inputs, report and history survive reopening; runtime/model setup is not replayed.
   page.reload();page.wait_for_selector('.project-link');page.locator('.project-link').first.click()
   page.wait_for_function("() => document.getElementById('revision').options.length===2")
   if out:page.screenshot(path=str(out/'desktop.png'),full_page=False)
   page.set_viewport_size({'width':390,'height':844})
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
   if out:page.screenshot(path=str(out/'mobile.png'))
   assert not external,external
   assert not errors,errors
   browser.close()
  print('Passed synthetic-runtime browser flow: session, create, generate, iframe controls, three downloads, follow-up/revision history, earlier snapshot preservation, reload, mobile, no external requests, no console errors.')
 finally:
  server.shutdown();server.server_close();app.close()

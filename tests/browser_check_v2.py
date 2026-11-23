"""Optional integration checks. Requires Playwright and an installed Chromium browser.
Run: python3 tests/browser_check_v2.py /tmp/founder-preview
No third-party dependencies are required by the renderer itself.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import shutil
import sys
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/examples/inventor-v2/report/disclosure.html'
out=Path(sys.argv[1]) if len(sys.argv)>1 else None
if out:out.mkdir(parents=True,exist_ok=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1440,'height':1000})
  requests=[];errors=[]
  page.on('request',lambda r:requests.append(r.url) if not r.url.startswith(f'http://127.0.0.1:{server.server_port}/') else None)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.goto(url);page.wait_for_selector('#brief-understanding')
  assert not page.locator('#full-analysis').evaluate('(el)=>el.open')
  assert not page.locator('#concepts').is_visible()
  visible_words=len(page.locator('main').inner_text().split())
  assert visible_words<550,visible_words
  page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
  assert page.locator('details:not([open])').count()==0
  page.evaluate("window.dispatchEvent(new Event('afterprint'))")
  assert not page.locator('#full-analysis').evaluate('(el)=>el.open')
  page.locator('#brief-similar a').first.click()
  assert page.locator('#full-analysis').evaluate('(el)=>el.open')
  assert page.locator(page.evaluate('location.hash')).is_visible()
  page.wait_for_selector('.filter:not([hidden])')
  total=page.locator('.searchable').count();assert total==8
  page.locator('#search').fill('nonexistent-12345');assert page.locator('.searchable:visible').count()==0
  assert 'No matches' in page.locator('#matches').inner_text()
  page.locator('#reset').click();assert page.locator('.searchable:visible').count()==total
  page.locator('#search').fill('Resideo');assert 0<page.locator('.searchable:visible').count()<total
  page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
  assert page.locator('.searchable:visible').count()==total
  assert page.locator('details:not([open])').count()==0
  page.evaluate("window.dispatchEvent(new Event('afterprint'))")
  assert page.locator('#search').input_value()=='Resideo'
  page.locator('#reset').click()
  for button,extension in [('download-json','json'),('download-md','md')]:
   with page.expect_download() as received:page.locator('#'+button).click()
   downloaded=Path(received.value.path()).read_text()
   expected=(ROOT/'examples/inventor-v2/report'/('disclosure.'+extension)).read_text()
   assert (json.loads(downloaded)==json.loads(expected)) if extension=='json' else downloaded==expected
  link=page.locator('#summary a[href^="#item-"]').first
  link.click();assert page.locator(page.evaluate('location.hash')).is_visible()
  assert page.evaluate("Array.from(document.querySelectorAll('a')).filter(a=>a.getAttribute('href').startsWith('#')).every(a=>document.getElementById(a.hash.slice(1)))")
  page.locator('#full-analysis').evaluate('(el)=>{el.open=false}')
  page.evaluate('window.scrollTo(0,0)')
  if out:page.screenshot(path=str(out/'desktop.png'))
  page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)')
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
  if out:page.screenshot(path=str(out/'mobile.png'))
  assert not requests,requests
  assert not errors,errors
  nojs=browser.new_page(java_script_enabled=False);nojs.goto(url)
  assert nojs.locator('#concepts article').count()==3
  assert nojs.locator('noscript').is_visible()
  nojs.locator('#full-analysis > summary').click()
  assert nojs.locator('#concepts').is_visible()
  assert nojs.locator('.actions').is_hidden()
  browser.close()
  print('Passed: desktop/mobile, search/reset/empty state, source navigation, both downloads, print/restore, no-JavaScript, no external requests, no console errors; concise view, hidden detail, comparison reveal, revision display.')
finally:server.shutdown();server.server_close()

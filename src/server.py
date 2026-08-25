"""Minimal local web UI for the Aster & Row support agent."""
from __future__ import annotations

import json
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import SupportAgent

AGENT = SupportAgent()

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aster &amp; Row Support</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f7f6;color:#1d2a25;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.app{width:min(100%,1060px);min-height:100vh;margin:auto;display:grid;grid-template-columns:270px 1fr;background:#fff;box-shadow:0 0 0 1px #dfe6e1}@media(max-width:720px){.app{display:block}.sidebar{display:none}.main{min-height:100vh}}
.sidebar{background:#17483f;color:#f3faf6;padding:28px 20px;display:flex;flex-direction:column}.mark{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px}.mark span{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;background:#d3f1a7;color:#17483f;font-family:Georgia;font-size:21px}.tagline{font-size:13px;line-height:1.5;color:#c8ddd5;margin:19px 0 0}.nav-label{margin:40px 0 10px;font-size:11px;letter-spacing:.1em;color:#a9c4b9;font-weight:700}.nav-item{display:flex;align-items:center;gap:10px;border-radius:8px;padding:10px 11px;background:#286252;font-size:14px}.dot{width:8px;height:8px;border-radius:50%;background:#bde987}.sidebar-foot{margin-top:auto;border-top:1px solid #477367;padding-top:16px;font-size:12px;line-height:1.5;color:#c8ddd5}
.main{min-height:100vh;display:flex;flex-direction:column;background:#fbfcfb}.topbar{height:76px;padding:0 30px;border-bottom:1px solid #e4e9e6;display:flex;align-items:center;justify-content:space-between}.topbar h1{font-size:16px;margin:0;font-weight:650}.sub{font-size:12px;color:#69766f;margin-top:3px}.safe{font-size:12px;color:#37644d;background:#e7f3e6;border-radius:99px;padding:7px 10px;white-space:nowrap}.conversation{flex:1;padding:34px clamp(18px,4vw,48px);display:flex;flex-direction:column;gap:22px;overflow:auto}.welcome{max-width:590px;margin:auto 0}.kicker{color:#2c7864;text-transform:uppercase;font-weight:750;letter-spacing:.11em;font-size:11px}.welcome h2{font-family:Georgia,serif;font-size:35px;line-height:1.13;letter-spacing:-.02em;margin:12px 0}.welcome p{max-width:480px;color:#607067;line-height:1.6;margin:0 0 22px}.suggestions{display:flex;gap:9px;flex-wrap:wrap}.suggestions button{border:1px solid #dce5df;background:#fff;border-radius:99px;color:#355348;padding:9px 12px;font:inherit;font-size:13px;cursor:pointer}.suggestions button:hover{border-color:#73a492;background:#f3faf5}.message{max-width:min(640px,90%);display:flex;gap:10px;align-items:flex-start}.avatar{width:29px;height:29px;flex:0 0 29px;border-radius:9px;display:grid;place-items:center;font-size:13px;font-weight:700}.agent .avatar{background:#d8efc1;color:#225846}.user{align-self:flex-end;flex-direction:row-reverse}.user .avatar{background:#2c7864;color:#fff}.bubble{padding:13px 15px;border-radius:4px 15px 15px 15px;line-height:1.5;font-size:14px;background:#fff;border:1px solid #e0e8e3;box-shadow:0 2px 7px rgba(20,60,45,.04);white-space:pre-wrap}.user .bubble{background:#2c7864;color:#fff;border-color:#2c7864;border-radius:15px 4px 15px 15px}.sources{margin-top:10px;padding-top:9px;border-top:1px solid #e8eeea;font-size:12px;color:#527064;line-height:1.45}.sources strong{color:#294a3c}.handoff{margin-top:10px;border-radius:7px;background:#fff5e9;color:#87521a;padding:7px 9px;font-size:12px;font-weight:600}.composer-wrap{padding:18px clamp(18px,4vw,48px) 24px;border-top:1px solid #e4e9e6;background:#fff}.composer{display:flex;gap:10px;align-items:center;border:1px solid #cfdcd5;border-radius:13px;padding:6px 7px 6px 15px;box-shadow:0 2px 10px rgba(30,66,51,.05)}.composer:focus-within{border-color:#629d89;box-shadow:0 0 0 3px #e5f3eb}.composer input{width:100%;min-width:0;border:0;outline:0;font:inherit;color:#1d2a25;padding:8px 0}.composer button{border:0;border-radius:9px;background:#1e6856;color:#fff;font:inherit;font-weight:650;padding:10px 15px;cursor:pointer}.composer button:hover{background:#174f43}.composer button:disabled{opacity:.65;cursor:wait}.privacy{font-size:11px;color:#758179;margin:9px 2px 0}.typing{color:#728078;font-size:13px;font-style:italic}.typing .bubble{padding:11px 14px}.dots::after{content:'…';display:inline-block;animation:pulse 1.1s infinite}@keyframes pulse{50%{opacity:.25}}
</style></head><body><div class="app"><aside class="sidebar"><div class="mark"><span>A</span>Aster &amp; Row</div><p class="tagline">Thoughtful gear for wherever you’re headed.</p><p class="nav-label">SUPPORT</p><div class="nav-item"><i class="dot"></i>Ask a question</div></aside><main class="main"><header class="topbar"><div><h1>Customer support</h1><div class="sub">Answers from Aster &amp; Row’s current policies</div></div><div class="safe">● Secure conversation</div></header><section id="chat" class="conversation" aria-live="polite"><div class="welcome"><div class="kicker">Hello</div><h2>How can we help today?</h2><p>I can help with shipping, returns, product care, and a current order status. I’ll show the policy source whenever it applies.</p><div class="suggestions"><button type="button" data-prompt="How long can I return an unused backpack?">Return window</button><button type="button" data-prompt="Do you ship internationally?">International shipping</button><button type="button" data-prompt="Where is ORD-1007?">Track an order</button></div></div></section><div class="composer-wrap"><form id="form" class="composer"><label class="sr-only" for="input">Your message</label><input id="input" autocomplete="off" placeholder="Ask about an order or policy" autofocus><button>Send</button></form><div class="privacy">Order lookup is read-only. Do not share payment details or personal information.</div></div></main></div>
<script>
const session=crypto.randomUUID(),chat=document.querySelector('#chat'),form=document.querySelector('#form'),input=document.querySelector('#input'),button=form.querySelector('button');
function sourceText(value){return value.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function add(kind,text,sources=[],handoff=false){chat.querySelector('.welcome')?.remove();const item=document.createElement('article');item.className='message '+kind;const avatar=document.createElement('div');avatar.className='avatar';avatar.textContent=kind==='user'?'You':'AR';const area=document.createElement('div');area.className='bubble';area.textContent=text;if(sources.length){const s=document.createElement('div');s.className='sources';s.innerHTML='<strong>Source'+(sources.length>1?'s':'')+':</strong><br>'+sources.map(sourceText).join('<br>');area.append(s)}if(handoff){const h=document.createElement('div');h.className='handoff';h.textContent='Human assistance recommended';area.append(h)}item.append(avatar,area);chat.append(item);item.scrollIntoView({behavior:'smooth',block:'end'});return item}
async function send(message){if(!message)return;add('user',message);input.value='';button.disabled=true;const loading=add('agent','Looking that up');loading.classList.add('typing');loading.querySelector('.bubble').classList.add('dots');try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,session_id:session})});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');loading.remove();add('agent',data.answer,data.sources,data.handoff)}catch(e){loading.remove();add('agent','Sorry, the local agent could not process that request. Please try again.')}finally{button.disabled=false;input.focus()}}
form.addEventListener('submit',e=>{e.preventDefault();send(input.value.trim())});document.querySelectorAll('[data-prompt]').forEach(el=>el.addEventListener('click',()=>send(el.dataset.prompt)));
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None: print("[web] " + format % args)
    def do_GET(self) -> None:
        if self.path != "/": self.send_error(HTTPStatus.NOT_FOUND); return
        self._send(HTTPStatus.OK, PAGE.encode(), "text/html; charset=utf-8")
    def do_POST(self) -> None:
        if self.path != "/api/chat": self.send_error(HTTPStatus.NOT_FOUND); return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length <= 0 or length > 10_000: raise ValueError("invalid request size")
            payload=json.loads(self.rfile.read(length)); message,session_id=payload.get("message"),payload.get("session_id")
            if not isinstance(message,str) or not message.strip(): raise ValueError("message is required")
            if not isinstance(session_id,str) or len(session_id)>100: session_id=secrets.token_urlsafe(16)
            result=AGENT.respond(message.strip(),session_id)
            self._send(HTTPStatus.OK,json.dumps({"answer":result.answer,"sources":result.sources,"handoff":result.handoff}).encode(),"application/json")
        except (ValueError,json.JSONDecodeError) as exc: self._send(HTTPStatus.BAD_REQUEST,json.dumps({"error":str(exc)}).encode(),"application/json")
    def _send(self,status:HTTPStatus,body:bytes,content_type:str)->None:
        self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
def main()->None:
    server=ThreadingHTTPServer(("127.0.0.1",8000),Handler);print("Aster & Row chat: http://127.0.0.1:8000")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=="__main__": main()

"""Exercise production language selection through its real HTTP methods."""
import ast
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen
from jetson_worktime.localization import LANGUAGES, LocalizedError

ROOT = Path(__file__).resolve().parents[1]


class MediaLanguageTests(unittest.TestCase):
    def test_snapshot_language_selection_and_invalid_language_are_read_only(self):
        module=ast.parse((ROOT/'scripts/preview.py').read_text())
        handler=next(node for node in module.body if isinstance(node,ast.ClassDef) and node.name=='Handler')
        methods=[node for node in handler.body if isinstance(node,ast.FunctionDef) and node.name in
                 ('do_GET','send_bytes','json','error','media_headers','log_message','send_media')]
        media=dict(jpeg=b'protected',annotated_locales={'zh-CN':b'chinese','en':b'english'},
                   received=time.monotonic_ns(),meta=dict(session_id='stream',receive_sequence=12),
                   revision=9,privacy_applied=True)
        behavior=SimpleNamespace(lock=threading.RLock(),media=media,config={'max_observation_age':1.5,'revision':9},transport=SimpleNamespace(condition=threading.Condition(),output_sockets=set()))
        namespace=dict(ROOT=ROOT,urlsplit=urlsplit,parse_qs=parse_qs,LANGUAGES=LANGUAGES,
                       LocalizedError=LocalizedError,json=json,time=time,behavior=behavior)
        namespace['studio_http']=SimpleNamespace(handle=lambda *args:False)
        exec(compile(ast.Module(body=methods,type_ignores=[]),'production_http_methods','exec'),namespace)
        attributes={node.name:namespace[node.name] for node in methods}
        namespace['json']=json
        cls=type('Handler',(BaseHTTPRequestHandler,),attributes)
        server=ThreadingHTTPServer(('127.0.0.1',0),cls)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            for query,locale,expected in [('', 'zh-CN',b'chinese'),('?lang=en','en',b'english'),('?lang=zh-CN','zh-CN',b'chinese')]:
                with urlopen(base+'/api/frame.jpg'+query,timeout=3) as response:
                    self.assertEqual(response.read(),expected)
                    self.assertEqual(response.headers['Content-Language'],locale)
                    self.assertEqual(response.headers['X-Config-Revision'],'9')
                    self.assertEqual(response.headers['X-Frame-Sequence'],'12')
                    self.assertEqual(response.headers['X-Privacy-Applied'],'true')
            for query in ('?lang=fr','?lang=','?lang=en&lang=zh-CN'):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base+'/api/frame.jpg'+query,timeout=3)
                self.assertEqual(caught.exception.code,400)
                self.assertEqual(json.loads(caught.exception.read())['error']['message_key'],'error.language')
            current_received = media['received']
            media['received'] = time.monotonic_ns()-2_000_000_000
            with self.assertRaises(HTTPError) as expired:
                urlopen(base+'/api/frame.jpg',timeout=3)
            self.assertEqual(expired.exception.code,503)
            media['received'] = current_received
            self.assertEqual(behavior.media,media)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

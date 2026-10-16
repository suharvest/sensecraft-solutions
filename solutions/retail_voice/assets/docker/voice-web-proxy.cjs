// voice-web 同源代理：/app/dist 静态文件 + /api/* 转发到 voice-service:8081。
// 背景：镜像默认 CMD 是 `serve -s dist`——纯静态、无 /api 代理，SPA 的相对路径
// API 调用会拿到 index.html，登录必败。此脚本只用 node 标准库，不动镜像。
const http = require('http');
const fs = require('fs');
const path = require('path');

const DIST = '/app/dist';
const UPSTREAM_HOST = process.env.UPSTREAM_HOST || 'voice-service';
const UPSTREAM_PORT = parseInt(process.env.UPSTREAM_PORT || '8081', 10);
const PORT = parseInt(process.env.PORT || '3000', 10);

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.ttf': 'font/ttf', '.map': 'application/json', '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp', '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
};

function proxy(req, res) {
  const opts = {
    host: UPSTREAM_HOST, port: UPSTREAM_PORT, method: req.method, path: req.url,
    headers: { ...req.headers, host: `${UPSTREAM_HOST}:${UPSTREAM_PORT}` },
  };
  const up = http.request(opts, (ur) => { res.writeHead(ur.statusCode, ur.headers); ur.pipe(res); });
  up.on('error', (e) => {
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ code: 502, message: `upstream voice-service unreachable: ${e.code || e.message}` }));
  });
  req.pipe(up);
}

function sendFile(res, f) {
  const ext = path.extname(f).toLowerCase();
  const stream = fs.createReadStream(f);
  stream.on('open', () => {
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=3600',
    });
    stream.pipe(res);
  });
  stream.on('error', () => { res.writeHead(404); res.end('not found'); });
}

http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) return proxy(req, res);
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  const f = path.join(DIST, p);
  if (!f.startsWith(DIST)) { res.writeHead(403); return res.end('forbidden'); }
  fs.stat(f, (e, st) => {
    if (!e && st.isFile()) return sendFile(res, f);
    sendFile(res, path.join(DIST, 'index.html')); // SPA 回退
  });
}).listen(PORT, () =>
  console.log(`voice-web proxy :${PORT}  static=${DIST}  /api/* -> ${UPSTREAM_HOST}:${UPSTREAM_PORT}`));

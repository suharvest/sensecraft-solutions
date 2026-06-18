const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 80;
const STATIC_DIR = __dirname;
const CONFIG_FILE = process.env.CONFIG_PATH || path.join(__dirname, 'data', 'config.json');

const MIME = {
    '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.json': 'application/json', '.svg': 'image/svg+xml',
};

function jsonResponse(res, status, body) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(typeof body === 'string' ? body : JSON.stringify(body));
}

http.createServer((req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    // --- API: calibration config ---
    if (req.url === '/api/config') {
        if (req.method === 'GET') {
            let data;
            try { data = fs.readFileSync(CONFIG_FILE, 'utf8'); } catch { data = 'null'; }
            jsonResponse(res, 200, data);
            return;
        }
        if (req.method === 'PUT') {
            let body = '';
            req.on('data', chunk => { body += chunk; if (body.length > 5e6) req.destroy(); });
            req.on('end', () => {
                try {
                    JSON.parse(body);
                    fs.mkdirSync(path.dirname(CONFIG_FILE), { recursive: true });
                    fs.writeFileSync(CONFIG_FILE, body);
                    jsonResponse(res, 200, '{"ok":true}');
                } catch {
                    jsonResponse(res, 400, '{"error":"invalid json"}');
                }
            });
            return;
        }
        if (req.method === 'DELETE') {
            try { fs.unlinkSync(CONFIG_FILE); } catch {}
            jsonResponse(res, 200, '{"ok":true}');
            return;
        }
    }

    // --- Static files ---
    const urlPath = req.url.split('?')[0];
    const filePath = path.join(STATIC_DIR, urlPath === '/' ? 'index.html' : urlPath);

    if (!filePath.startsWith(STATIC_DIR)) { res.writeHead(403); res.end(); return; }

    let fileData;
    try { fileData = fs.readFileSync(filePath); } catch { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
    res.end(fileData);
}).listen(PORT, () => console.log(`Heatmap server on :${PORT}`));

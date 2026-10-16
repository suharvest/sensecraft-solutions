// Heatmap UI backend.
//
// The browser talks only to this server: it proxies the InfluxDB queries and
// keeps the calibration store. The token stays here, and port 8086 no longer
// has to be reachable from the operator's laptop.
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 80;
const STATIC_DIR = __dirname;
const CONFIG_FILE = process.env.CONFIG_PATH || path.join(__dirname, 'data', 'config.json');

const INFLUX_URL = process.env.INFLUX_URL || 'http://influxdb:8086';
const INFLUX_ORG = process.env.INFLUX_ORG || 'seeed';
const INFLUX_BUCKET = process.env.INFLUX_BUCKET || 'recamera';
const INFLUX_TOKEN = process.env.INFLUX_TOKEN || 'recamera-heatmap-token';

const MIME = {
    '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.json': 'application/json', '.svg': 'image/svg+xml',
};

function jsonResponse(res, status, body) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(typeof body === 'string' ? body : JSON.stringify(body));
}

// --- Calibration store ------------------------------------------------------
// Shape: { floorPlan: <data-url|null>, streams: { "<device>/<stream>": {srcPoints, dstPoints} } }
// The floor plan is shared: several cameras in one store map onto one plan.
// Key "*" is the fallback used by any stream without its own calibration.
const EMPTY_CONFIG = { floorPlan: null, streams: {} };

function normalizeConfig(raw) {
    if (!raw || typeof raw !== 'object') return { ...EMPTY_CONFIG };
    // Pre-multi-camera layout: one unnamed calibration plus its floor plan.
    if (Array.isArray(raw.srcPoints)) {
        return {
            floorPlan: raw.floorPlanImage || null,
            streams: { '*': { srcPoints: raw.srcPoints, dstPoints: raw.dstPoints } },
        };
    }
    return {
        floorPlan: raw.floorPlan || null,
        streams: (raw.streams && typeof raw.streams === 'object') ? raw.streams : {},
    };
}

function readConfig() {
    try { return normalizeConfig(JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))); }
    catch { return { ...EMPTY_CONFIG }; }
}

// --- InfluxDB ---------------------------------------------------------------
const RANGE_RE = /^-\d{1,4}(m|h|d)$/;
const TAG_RE = /^[A-Za-z0-9._:-]{1,64}$/;

async function influxQuery(flux) {
    const resp = await fetch(`${INFLUX_URL}/api/v2/query?org=${encodeURIComponent(INFLUX_ORG)}`, {
        method: 'POST',
        headers: {
            'Authorization': `Token ${INFLUX_TOKEN}`,
            'Content-Type': 'application/vnd.flux',
            'Accept': 'application/csv',
        },
        body: flux,
    });
    if (!resp.ok) throw new Error(`InfluxDB HTTP ${resp.status}`);
    return await resp.text();
}

// Annotated-CSV reader: returns rows as objects keyed by the header row.
function parseCsv(csv) {
    const rows = [];
    let header = null;
    for (const line of csv.split('\n')) {
        const t = line.trim();
        if (!t || t.startsWith('#')) { header = null; continue; }
        const cols = t.split(',');
        if (!header) { header = cols.map(c => c.trim()); continue; }
        const row = {};
        header.forEach((h, i) => { row[h] = cols[i]; });
        rows.push(row);
    }
    return rows;
}

// Detectors publish under a tag pair; the UI needs the list to offer a
// per-camera calibration target and to group points by their own transform.
async function listStreams() {
    const flux = `
from(bucket: "${INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "persons" and r._field == "cx_pct")
  |> group(columns: ["device", "stream"])
  |> count()
  |> group()
  |> keep(columns: ["device", "stream", "_value"])`;
    return parseCsv(await influxQuery(flux))
        .filter(r => r.device)
        .map(r => ({ device: r.device, stream: r.stream || 'cam-01', points: Number(r._value) || 0 }))
        .sort((a, b) => (a.device + a.stream).localeCompare(b.device + b.stream));
}

// Points come back grouped by camera: each camera has its own perspective
// calibration onto the shared floor plan, so they cannot be merged before
// the transform is applied.
async function queryPoints(range, device, stream) {
    const filters = [];
    if (device) filters.push(`  |> filter(fn: (r) => r.device == "${device}")`);
    if (stream) filters.push(`  |> filter(fn: (r) => r.stream == "${stream}")`);
    const flux = `
from(bucket: "${INFLUX_BUCKET}")
  |> range(start: ${range})
  |> filter(fn: (r) => r._measurement == "persons")
  |> filter(fn: (r) => r._field == "cx_pct" or r._field == "cy_pct")
${filters.join('\n')}
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["device", "stream", "cx_pct", "cy_pct"])`;

    const groups = new Map();
    for (const row of parseCsv(await influxQuery(flux))) {
        const x = parseFloat(row.cx_pct), y = parseFloat(row.cy_pct);
        if (isNaN(x) || isNaN(y)) continue;
        const dev = row.device || 'unknown';
        const str = row.stream || 'cam-01';
        const key = `${dev}/${str}`;
        if (!groups.has(key)) groups.set(key, { device: dev, stream: str, points: [] });
        groups.get(key).points.push([x, y]);
    }
    return [...groups.values()];
}

// --- HTTP -------------------------------------------------------------------
function readBody(req, limit = 8e6) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => {
            body += chunk;
            if (body.length > limit) { req.destroy(); reject(new Error('body too large')); }
        });
        req.on('end', () => resolve(body));
        req.on('error', reject);
    });
}

http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    const url = new URL(req.url, 'http://localhost');

    // --- API: calibration config ---
    if (url.pathname === '/api/config') {
        if (req.method === 'GET') { jsonResponse(res, 200, readConfig()); return; }
        if (req.method === 'PUT') {
            try {
                const cfg = normalizeConfig(JSON.parse(await readBody(req)));
                fs.mkdirSync(path.dirname(CONFIG_FILE), { recursive: true });
                fs.writeFileSync(CONFIG_FILE, JSON.stringify(cfg));
                jsonResponse(res, 200, { ok: true });
            } catch {
                jsonResponse(res, 400, { error: 'invalid json' });
            }
            return;
        }
        if (req.method === 'DELETE') {
            try { fs.unlinkSync(CONFIG_FILE); } catch {}
            jsonResponse(res, 200, { ok: true });
            return;
        }
    }

    // --- API: which cameras are reporting ---
    if (url.pathname === '/api/streams' && req.method === 'GET') {
        try { jsonResponse(res, 200, await listStreams()); }
        catch (err) { jsonResponse(res, 502, { error: String(err.message) }); }
        return;
    }

    // --- API: heatmap points, grouped by camera ---
    if (url.pathname === '/api/points' && req.method === 'GET') {
        const range = url.searchParams.get('range') || '-1h';
        const device = url.searchParams.get('device') || '';
        const stream = url.searchParams.get('stream') || '';
        if (!RANGE_RE.test(range)) { jsonResponse(res, 400, { error: 'bad range' }); return; }
        if (device && !TAG_RE.test(device)) { jsonResponse(res, 400, { error: 'bad device' }); return; }
        if (stream && !TAG_RE.test(stream)) { jsonResponse(res, 400, { error: 'bad stream' }); return; }
        try { jsonResponse(res, 200, { groups: await queryPoints(range, device, stream) }); }
        catch (err) { jsonResponse(res, 502, { error: String(err.message) }); }
        return;
    }

    // --- Static files ---
    const filePath = path.join(STATIC_DIR, url.pathname === '/' ? 'index.html' : url.pathname);
    if (!filePath.startsWith(STATIC_DIR)) { res.writeHead(403); res.end(); return; }

    let fileData;
    try { fileData = fs.readFileSync(filePath); } catch { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
    res.end(fileData);
}).listen(PORT, () => console.log(`Heatmap server on :${PORT}`));

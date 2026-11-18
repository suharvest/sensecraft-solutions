import {overlayStyle, visualizationDefaults, stationFill} from './overlay.js';
import {LocalizedError} from './i18n.js';
import {containRect} from './api.js';

export function sourcePoint(clientX, clientY, bounds, size) {
  const map = containRect(size[0], size[1], bounds.width, bounds.height);
  const x = (clientX - bounds.left - map.x) / map.scale;
  const y = (clientY - bounds.top - map.y) / map.scale;
  if (x < 0 || y < 0 || x > size[0] || y > size[1]) return null;
  return [Math.min(size[0] - 1, Math.round(x)), Math.min(size[1] - 1, Math.round(y))];
}

function cross(a, b, c) {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}
function onSegment(p, a, b) {
  return Math.abs(cross(a, b, p)) < 1e-7 && [0, 1].every(i => p[i] >= Math.min(a[i], b[i]) - 1e-7 && p[i] <= Math.max(a[i], b[i]) + 1e-7);
}
function edges(points) {
  return points.map((point, i) => [point, points[(i + 1) % points.length]]);
}
function inside(point, polygon) {
  if (edges(polygon).some(([a, b]) => onSegment(point, a, b))) return true;
  let result = false;
  for (const [a, b] of edges(polygon)) {
    if ((a[1] > point[1]) !== (b[1] > point[1]) && point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) result = !result;
  }
  return result;
}
function intersects(a, b, c, d) {
  return (cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0)
    || onSegment(c, a, b) || onSegment(d, a, b) || onSegment(a, c, d) || onSegment(b, c, d);
}

export function validateRegions(regions, size) {
  for (const name of ['station', 'seat']) {
    const polygon = regions[name];
    if (!Array.isArray(polygon) || polygon.length < 3 || polygon.length > 32) throw new LocalizedError('roi.vertexCount', {region:name});
    if (polygon.some(p => !Array.isArray(p) || p.length !== 2 || p.some((v, i) => !Number.isFinite(v) || v < 0 || v > size[i] - 1))) throw new LocalizedError('roi.bounds', {region:name});
    if (new Set(polygon.map(p => p.join(','))).size !== polygon.length) throw new LocalizedError('roi.duplicate', {region:name});
    const segments = edges(polygon);
    const area = Math.abs(segments.reduce((sum, [a, b]) => sum + a[0] * b[1] - b[0] * a[1], 0)) / 2;
    if (area < 1) throw new LocalizedError('roi.area', {region:name});
    for (let i = 0; i < segments.length; i++) {
      for (let j = i + 1; j < segments.length; j++) {
        if (j === i + 1 || (i === 0 && j === segments.length - 1)) continue;
        if (intersects(...segments[i], ...segments[j])) throw new LocalizedError('roi.crossing', {region:name});
      }
    }
  }
  if (regions.seat.some(point => !inside(point, regions.station))) throw new LocalizedError('roi.containment');
  for (const [a, b] of edges(regions.seat)) {
    const fractions = [0, 1];
    for (const [c, d] of edges(regions.station)) {
      const denominator = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0]);
      if (Math.abs(denominator) < 1e-9) continue;
      const t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / denominator;
      if (t > 0 && t < 1 && onSegment([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])], c, d)) fractions.push(t);
    }
    fractions.sort((left, right) => left - right);
    for (let i = 1; i < fractions.length; i++) {
      const t = (fractions[i - 1] + fractions[i]) / 2;
      if (!inside([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])], regions.station)) throw new LocalizedError('roi.edgeContainment');
    }
  }
}

export class RoiEditor {
  constructor(canvas, onChange, names = ['station','seat']) {
    this.canvas = canvas;
    this.onChange = onChange;
    this.names=names;
    this.regions=Object.fromEntries(names.map(n=>[n,[]]));
    this.size = [1280, 720];
    this.region = names[0];
    this.tool = 'rectangle';
    this.image = null;
    this.history = [];
    this.draft = [];
    this.drag = null;
    canvas.addEventListener('pointerdown', event => this.pointerDown(event));
    canvas.addEventListener('pointermove', event => this.pointerMove(event));
    canvas.addEventListener('pointerup', event => this.pointerUp(event));
    canvas.addEventListener('pointercancel', event => this.pointerUp(event));
    canvas.addEventListener('dblclick', event => {
      event.preventDefault();
      if (this.tool === 'polygon') this.finishPolygon();
    });
  }

  load(regions, size) {
    this.regions = structuredClone(regions);
    this.size = size.slice();
    this.history = [];
    this.draft = [];
    this.draw();
  }

  setImage(image, size) {
    this.image = image;
    this.size = size.slice();
    this.canvas.width = image.naturalWidth;
    this.canvas.height = image.naturalHeight;
    this.canvas.style.aspectRatio = size[0] + ' / ' + size[1];
    this.draw();
  }

  clearImage() {
    this.image = null;
    this.draw();
  }

  setRegion(name) {
    this.region = name;
    this.draft = [];
    this.draw();
  }

  setTool(tool) {
    this.tool = tool;
    this.draft = [];
    this.draw();
  }

  remember() {
    this.history.push(structuredClone({regions: this.regions, draft: this.draft}));
    if (this.history.length > 40) this.history.shift();
  }

  undo() {
    const previous = this.history.pop();
    if (!previous) return;
    this.regions = previous.regions;
    this.draft = previous.draft;
    this.changed();
  }

  clearRegion() {
    this.remember();
    this.regions[this.region] = [];
    this.draft = [];
    this.changed();
  }

  point(event) {
    return sourcePoint(event.clientX, event.clientY, this.canvas.getBoundingClientRect(), this.size);
  }

  pointerDown(event) {
    if (!this.image || (event.button !== undefined && event.button !== 0)) return;
    const point = this.point(event);
    if (!point) return;
    event.preventDefault();
    const bounds = this.canvas.getBoundingClientRect();
    const tolerance = 14 / containRect(...this.size, bounds.width, bounds.height).scale;
    if (this.tool === 'polygon') {
      if (this.draft.length >= 3 && Math.hypot(point[0] - this.draft[0][0], point[1] - this.draft[0][1]) < tolerance) {
        this.finishPolygon();
        return;
      }
      if (this.draft.length && Math.hypot(point[0] - this.draft.at(-1)[0], point[1] - this.draft.at(-1)[1]) < tolerance) return;
      if (this.draft.length >= 32) return;
      this.remember();
      this.draft.push(point);
      this.draw();
      return;
    }
    if (this.tool === 'edit') {
      const index = this.regions[this.region].findIndex(p => Math.hypot(p[0] - point[0], p[1] - point[1]) < tolerance);
      if (index < 0) return;
      this.remember();
      this.drag = {index};
    } else {
      this.remember();
      this.drag = {start: point};
    }
    this.canvas.setPointerCapture(event.pointerId);
  }

  pointerMove(event) {
    if (!this.drag) return;
    const point = this.point(event);
    if (!point) return;
    if (this.drag.start) {
      const [a, b] = [this.drag.start, point];
      this.regions[this.region] = [[Math.min(a[0], b[0]), Math.min(a[1], b[1])], [Math.max(a[0], b[0]), Math.min(a[1], b[1])], [Math.max(a[0], b[0]), Math.max(a[1], b[1])], [Math.min(a[0], b[0]), Math.max(a[1], b[1])]];
    } else {
      this.regions[this.region][this.drag.index] = point;
    }
    this.draw();
  }

  pointerUp(event) {
    if (!this.drag) return;
    this.pointerMove(event);
    this.drag = null;
    if (this.canvas.hasPointerCapture(event.pointerId)) this.canvas.releasePointerCapture(event.pointerId);
    this.changed();
  }

  finishPolygon() {
    if (this.draft.length < 3) return;
    this.remember();
    this.regions[this.region] = this.draft.map(point => point.slice());
    this.draft = [];
    this.changed();
  }

  changed() {
    this.draw();
    this.onChange();
  }

  draw() {
    const context = this.canvas.getContext('2d');
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (!this.image) return;
    context.drawImage(this.image, 0, 0, this.canvas.width, this.canvas.height);
    const scaleX = this.canvas.width / this.size[0];
    const scaleY = this.canvas.height / this.size[1];
    const displayScale = this.canvas.width / Math.max(1, this.canvas.getBoundingClientRect().width);
    for (const name of this.names) {
      const points = name === this.region && this.draft.length ? this.draft : this.regions[name];
      if (!points.length) continue;
      const visualization = this.visualization ?? visualizationDefaults();
      const color = this.regionColors?.[name] ?? visualization.colors[name];
      context.strokeStyle = color;
      context.fillStyle = color;
      context.globalAlpha = this.regionMasks?.[name]===false?0:(this.regionOpacity?.[name] ?? visualization[name+'_fill_alpha']);
      context.lineWidth = (name === this.region ? 2.5 : 1.5) * displayScale;
      context.setLineDash(name === this.region ? [] : [6 * displayScale, 4 * displayScale]);
      context.beginPath();
      points.forEach(([x, y], index) => index ? context.lineTo(x * scaleX, y * scaleY) : context.moveTo(x * scaleX, y * scaleY));
      if (!(name === this.region && this.draft.length)) context.closePath();
      if(name==='station'){
        const opacity=context.globalAlpha;context.globalAlpha=1;context.fillStyle=stationFill(context,points.map(([x,y])=>[x*scaleX,y*scaleY]),color,opacity);
      }
      context.fill();
      context.globalAlpha = 1;
      context.stroke();
      context.setLineDash([]);
      for (const [x, y] of points) {
        context.beginPath();
        context.arc(x * scaleX, y * scaleY, 4.5 * displayScale, 0, 2 * Math.PI);
        context.fillStyle = color;
        context.fill();
        context.strokeStyle = '#15362a';
        context.lineWidth = displayScale;
        context.stroke();
      }
    }
  }
}

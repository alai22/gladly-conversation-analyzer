/**
 * Image-to-vector contour extraction using Canvas API.
 */

import { polygonPerimeter, resampleClosedPolyline, smoothPolygon } from './geometry';

/** @typedef {{ x: number, y: number }} Point */
/** @typedef {{ id: string, name: string, points: Point[], perimeter: number, source: 'sample' | 'image' }} NeckProfile */

/**
 * Load image file to HTMLImageElement.
 * @param {File} file
 * @returns {Promise<HTMLImageElement>}
 */
function loadImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };
    img.src = url;
  });
}

/**
 * Trace outer boundary of foreground pixels (4-connected boundary walk).
 * @param {Uint8ClampedArray} data
 * @param {number} width
 * @param {number} height
 * @param {number} threshold
 * @returns {Point[]}
 */
function extractLargestContour(data, width, height, threshold) {
  const mask = new Uint8Array(width * height);
  for (let i = 0; i < width * height; i++) {
    const idx = i * 4;
    const gray = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
    mask[i] = gray < threshold ? 1 : 0;
  }

  // Find largest connected component via flood fill
  const visited = new Uint8Array(width * height);
  let bestComponent = [];

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const start = y * width + x;
      if (!mask[start] || visited[start]) continue;
      const component = [];
      const stack = [[x, y]];
      visited[start] = 1;
      while (stack.length) {
        const [cx, cy] = stack.pop();
        component.push({ x: cx, y: cy });
        const neighbors = [
          [cx + 1, cy],
          [cx - 1, cy],
          [cx, cy + 1],
          [cx, cy - 1],
        ];
        for (const [nx, ny] of neighbors) {
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
          const ni = ny * width + nx;
          if (mask[ni] && !visited[ni]) {
            visited[ni] = 1;
            stack.push([nx, ny]);
          }
        }
      }
      if (component.length > bestComponent.length) {
        bestComponent = component;
      }
    }
  }

  if (bestComponent.length < 10) return [];

  // Boundary pixels: foreground with at least one background neighbor
  const inSet = new Set(bestComponent.map((p) => `${p.x},${p.y}`));
  const boundary = bestComponent.filter(({ x, y }) => {
    const neighbors = [
      [x + 1, y],
      [x - 1, y],
      [x, y + 1],
      [x, y - 1],
    ];
    return neighbors.some(([nx, ny]) => !inSet.has(`${nx},${ny}`));
  });

  if (boundary.length < 10) return [];

  // Sort boundary by angle from centroid for a closed loop
  const cx = boundary.reduce((s, p) => s + p.x, 0) / boundary.length;
  const cy = boundary.reduce((s, p) => s + p.y, 0) / boundary.length;
  boundary.sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));

  // Downsample and convert to centered coordinates
  const step = Math.max(1, Math.floor(boundary.length / 150));
  const sampled = [];
  for (let i = 0; i < boundary.length; i += step) {
    sampled.push({
      x: boundary[i].x - cx,
      y: boundary[i].y - cy,
    });
  }
  return sampled;
}

/**
 * Douglas-Peucker simplification.
 * @param {Point[]} points
 * @param {number} epsilon
 * @returns {Point[]}
 */
function simplifyPolygon(points, epsilon) {
  if (points.length <= 2) return points;

  function perpDist(p, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy) || 1;
    return Math.abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / len;
  }

  function rdp(pts) {
    if (pts.length <= 2) return pts;
    let maxDist = 0;
    let idx = 0;
    const end = pts.length - 1;
    for (let i = 1; i < end; i++) {
      const d = perpDist(pts[i], pts[0], pts[end]);
      if (d > maxDist) {
        maxDist = d;
        idx = i;
      }
    }
    if (maxDist > epsilon) {
      const left = rdp(pts.slice(0, idx + 1));
      const right = rdp(pts.slice(idx));
      return left.slice(0, -1).concat(right);
    }
    return [pts[0], pts[end]];
  }

  return rdp(points);
}

/**
 * Extract neck profile contour from uploaded image.
 * @param {File} file
 * @param {{ smoothing?: number, threshold?: number }} [options]
 * @returns {Promise<NeckProfile>}
 */
export async function extractContourFromImage(file, options = {}) {
  const { smoothing = 0.3, threshold = 128 } = options;
  const img = await loadImage(file);

  const maxDim = 400;
  const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
  const w = Math.round(img.width * scale);
  const h = Math.round(img.height * scale);

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas not supported');

  ctx.drawImage(img, 0, 0, w, h);
  const imageData = ctx.getImageData(0, 0, w, h);

  let contour = extractLargestContour(imageData.data, w, h, threshold);
  if (contour.length < 8) {
    throw new Error('Could not detect a clear neck contour. Try a higher-contrast image.');
  }

  contour = simplifyPolygon(contour, 2);
  contour = smoothPolygon(contour, smoothing);
  contour = resampleClosedPolyline(contour, 120);

  return {
    id: `image-${Date.now()}`,
    name: file.name.replace(/\.[^.]+$/, '') || 'Uploaded Neck',
    points: contour,
    perimeter: polygonPerimeter(contour),
    source: 'image',
  };
}

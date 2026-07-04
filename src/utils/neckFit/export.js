/**
 * Export utilities for neck-fit visualization.
 */

import { pointsToSvgPath, normalizeForView } from './geometry';

const SEGMENT_COLORS = {
  electronics: '#374151',
  gpsAntenna: '#6366f1',
  strap: '#059669',
};

const SEGMENT_LABELS = {
  electronics: 'Electronics',
  gpsAntenna: 'GPS / Antenna',
  strap: 'Strap',
};

/**
 * Build standalone SVG string for export.
 * @param {Object} params
 * @param {import('./geometry').Point[]} params.neckPoints
 * @param {import('./geometry').Point[]} params.collarOffsetPoints
 * @param {import('./mechanicalModel').CollarSegment[]} params.segments
 * @param {import('./geometry').Point[]} [params.gapIndicators]
 * @param {import('./geometry').Point[]} [params.pressurePoints]
 * @param {boolean} [params.showGaps]
 * @param {boolean} [params.showPressure]
 * @returns {string}
 */
export function buildExportSvg({
  neckPoints,
  collarOffsetPoints,
  segments,
  gapIndicators = [],
  pressurePoints = [],
  showGaps = true,
  showPressure = false,
}) {
  const allPts = [...neckPoints, ...collarOffsetPoints];
  segments.forEach((s) => allPts.push(...s.pathPoints));
  const { viewBox } = normalizeForView(allPts, 50);

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="800" height="800">`;
  svg += `<style>
    .neck { fill: #fef3c7; stroke: #d97706; stroke-width: 1.5; }
    .collar-offset { fill: none; stroke: #94a3b8; stroke-width: 1; stroke-dasharray: 4 3; }
    .segment { fill: none; stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
    .label { font-family: system-ui, sans-serif; font-size: 10px; fill: #374151; }
  </style>`;

  svg += `<path class="neck" d="${pointsToSvgPath(neckPoints, true)}" />`;
  svg += `<path class="collar-offset" d="${pointsToSvgPath(collarOffsetPoints, true)}" />`;

  segments.forEach((seg) => {
    if (!seg.pathPoints.length) return;
    const color = SEGMENT_COLORS[seg.type];
    svg += `<path class="segment" stroke="${color}" d="${pointsToSvgPath(seg.pathPoints, false)}" />`;
    const mid = seg.pathPoints[Math.floor(seg.pathPoints.length / 2)];
    svg += `<text class="label" x="${mid.x}" y="${mid.y - 8}">${SEGMENT_LABELS[seg.type]}</text>`;
  });

  if (showGaps) {
    gapIndicators.forEach((p) => {
      svg += `<circle cx="${p.x}" cy="${p.y}" r="3" fill="#ef4444" opacity="0.7" />`;
    });
  }

  if (showPressure) {
    pressurePoints.forEach((p) => {
      svg += `<circle cx="${p.x}" cy="${p.y}" r="3" fill="#f59e0b" opacity="0.7" />`;
    });
  }

  svg += '</svg>';
  return svg;
}

/**
 * Trigger browser download of content.
 * @param {string} content
 * @param {string} filename
 * @param {string} mimeType
 */
export function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export { SEGMENT_COLORS, SEGMENT_LABELS };

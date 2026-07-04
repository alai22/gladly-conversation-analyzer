/**
 * Built-in non-circular dog neck cross-section profiles.
 */

import { polygonPerimeter, resampleClosedPolyline } from './geometry';

/** @typedef {{ x: number, y: number }} Point */
/** @typedef {{ id: string, name: string, points: Point[], perimeter: number, source: 'sample' | 'image' }} NeckProfile */

/**
 * Generate points on an ellipse.
 * @param {number} rx
 * @param {number} ry
 * @param {number} count
 * @param {number} [rotation=0]
 * @returns {Point[]}
 */
function ellipsePoints(rx, ry, count, rotation = 0) {
  const pts = [];
  for (let i = 0; i < count; i++) {
    const theta = (2 * Math.PI * i) / count;
    let x = rx * Math.cos(theta);
    let y = ry * Math.sin(theta);
    const cos = Math.cos(rotation);
    const sin = Math.sin(rotation);
    pts.push({
      x: x * cos - y * sin,
      y: x * sin + y * cos,
    });
  }
  return pts;
}

/**
 * Flatten front of ellipse (y > 0 region pulled inward).
 * @param {Point[]} points
 * @param {number} flatAmount
 * @returns {Point[]}
 */
function flattenFront(points, flatAmount) {
  return points.map((p) => {
    if (p.y > 0) {
      const factor = 1 - flatAmount * (p.y / (Math.max(...points.map((q) => q.y)) + 1e-6));
      return { x: p.x * factor, y: p.y };
    }
    return { ...p };
  });
}

/**
 * @param {Point[]} points
 * @param {string} id
 * @param {string} name
 * @returns {NeckProfile}
 */
function makeProfile(points, id, name) {
  const resampled = resampleClosedPolyline(points, 120);
  return {
    id,
    name,
    points: resampled,
    perimeter: polygonPerimeter(resampled),
    source: 'sample',
  };
}

/** Oval with flattened front (trachea / throat side). */
function ovalFlattenedFront() {
  const base = ellipsePoints(55, 42, 120);
  const flat = flattenFront(base, 0.35);
  return makeProfile(flat, 'oval-flat-front', 'Oval — Flattened Front');
}

/** Asymmetric oval — wider on one side. */
function asymmetricOval() {
  const pts = [];
  for (let i = 0; i < 120; i++) {
    const theta = (2 * Math.PI * i) / 120;
    const rx = 50 + 12 * Math.cos(theta);
    const ry = 38 + 8 * Math.sin(theta + 0.4);
    pts.push({ x: rx * Math.cos(theta), y: ry * Math.sin(theta) });
  }
  return makeProfile(pts, 'asymmetric-oval', 'Asymmetric Oval');
}

/** Pear-shaped — wider at base (lower neck). */
function pearShaped() {
  const pts = [];
  for (let i = 0; i < 120; i++) {
    const theta = (2 * Math.PI * i) / 120;
    const t = (Math.sin(theta) + 1) / 2; // 0 top, 1 bottom
    const rx = 38 + 22 * t;
    const ry = 35 + 10 * t;
    pts.push({ x: rx * Math.cos(theta), y: ry * Math.sin(theta) });
  }
  return makeProfile(pts, 'pear-shaped', 'Pear-Shaped Neck');
}

/** Wider lower neck — bulldog / thick neck profile. */
function widerLowerNeck() {
  const pts = [];
  for (let i = 0; i < 120; i++) {
    const theta = (2 * Math.PI * i) / 120;
    const t = (Math.sin(theta) + 1) / 2;
    const rx = 42 + 18 * Math.pow(t, 1.5);
    const ry = 40 + 6 * t;
    // Slight front flatten
    let x = rx * Math.cos(theta);
    let y = ry * Math.sin(theta);
    if (y > 0) x *= 1 - 0.2 * (y / (ry + 1e-6));
    pts.push({ x, y });
  }
  return makeProfile(pts, 'wider-lower', 'Wider Lower Neck');
}

export const SAMPLE_PROFILES = [
  ovalFlattenedFront(),
  asymmetricOval(),
  pearShaped(),
  widerLowerNeck(),
];

/**
 * @param {string} id
 * @returns {NeckProfile | undefined}
 */
export function getSampleProfileById(id) {
  return SAMPLE_PROFILES.find((p) => p.id === id);
}

export const DEFAULT_SAMPLE_PROFILE_ID = 'oval-flat-front';

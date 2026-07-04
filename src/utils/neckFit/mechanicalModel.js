/**
 * Simplified mechanical fit model for Halo Collar 6 neck-fit exploration.
 */

import {
  buildArcLengthTable,
  computeCurvature,
  extractPathSegment,
  getPointAtS,
  getTangentAtS,
  lerpPoint,
  maxGapToLine,
  maxLinePolygonPenetration,
  offsetPolygon,
  pointToSegmentDistance,
  polylineLength,
  scaleProfileToPerimeter,
  smoothPolygon,
} from './geometry';

/** @typedef {{ x: number, y: number }} Point */

/** @typedef {Object} FitInputs
 * @property {number} neckCircumference mm
 * @property {number} clearanceOffset mm
 * @property {number} electronicsLength mm
 * @property {number} electronicsThickness mm
 * @property {number} electronicsPlacementS mm along collar path
 * @property {number} gpsAntennaLength mm
 * @property {number} gpsAntennaThickness mm
 * @property {number} gpsAntennaStiffness 0-1 (1 = stiffest)
 * @property {number} [gpsAntennaYoungsModulus]
 * @property {number} gpsMinBendRadius mm
 * @property {number} strapThickness mm
 * @property {number} slack mm
 */

/** @typedef {'electronics' | 'gpsAntenna' | 'strap'} CollarSegmentType */

/** @typedef {Object} CollarSegment
 * @property {CollarSegmentType} type
 * @property {number} length
 * @property {number} thickness
 * @property {number | 'rigid' | 'fully-flexible'} stiffness
 * @property {number} startS
 * @property {number} endS
 * @property {Point[]} pathPoints
 */

/** @typedef {Object} FitResult
 * @property {number} collarPathLength
 * @property {number} strapLength
 * @property {number} maxGpsCurvature
 * @property {number} minGpsBendRadius
 * @property {number} maxElectronicsGap
 * @property {number} maxInterferenceDepth
 * @property {boolean} isValid
 * @property {string[]} warnings
 * @property {CollarSegment[]} segments
 * @property {Point[]} neckPoints
 * @property {Point[]} collarOffsetPoints
 * @property {Point[]} gapIndicators
 * @property {Point[]} pressurePoints
 * @property {number} bendingEnergy
 */

export const MIN_STRAP_LENGTH = 30; // mm manufacturability minimum

export const DEFAULT_FIT_INPUTS = {
  neckCircumference: 350,
  clearanceOffset: 8,
  electronicsLength: 85,
  electronicsThickness: 12,
  electronicsPlacementS: 0,
  gpsAntennaLength: 55,
  gpsAntennaThickness: 8,
  gpsAntennaStiffness: 0.5,
  gpsAntennaYoungsModulus: 2.5,
  gpsMinBendRadius: 15,
  strapThickness: 4,
  slack: 0,
};

/**
 * Stiffness factor for GPS section: 0 = fully flexible (follows path), 1 = rigid straight.
 * @param {number} stiffness slider 0-1
 * @returns {number}
 */
function gpsStiffnessFactor(stiffness) {
  return Math.max(0, Math.min(1, stiffness));
}

/**
 * Build GPS/antenna path blending straight chord vs. ideal offset path.
 * @param {ReturnType<typeof buildArcLengthTable>} table
 * @param {number} sStart
 * @param {number} length
 * @param {number} stiffness 0-1
 * @returns {Point[]}
 */
function buildGpsPath(table, sStart, length, stiffness) {
  const factor = gpsStiffnessFactor(stiffness);
  const startPt = getPointAtS(table, sStart);
  const endPt = getPointAtS(table, sStart + length);

  if (factor >= 0.99) {
    return [startPt, endPt];
  }

  const samples = Math.max(20, Math.ceil(length / 2));
  const result = [];
  for (let i = 0; i <= samples; i++) {
    const t = i / samples;
    const s = sStart + t * length;
    const pathPt = getPointAtS(table, s);
    const straightPt = lerpPoint(startPt, endPt, t);
    result.push(lerpPoint(straightPt, pathPt, 1 - factor));
  }
  return result;
}

/**
 * Estimate bending energy E = 0.5 * EI * integral(kappa^2 ds).
 * @param {Point[]} path
 * @param {number} youngsModulus MPa scale
 * @param {number} thickness mm
 * @returns {number}
 */
function estimateBendingEnergy(path, youngsModulus, thickness) {
  const { curvatures } = computeCurvature(path);
  const I = (thickness ** 3) / 12; // simplified rectangular section
  const E = youngsModulus * 1e6; // scale to Pa-like units for display
  let energy = 0;
  const ds = polylineLength(path) / Math.max(curvatures.length, 1);
  for (const k of curvatures) {
    energy += 0.5 * E * I * k * k * ds;
  }
  return energy;
}

/**
 * Compute pressure/contact zones — points where GPS path deviates from ideal (tension).
 * @param {Point[]} gpsPath
 * @param {Point[]} idealPath
 * @returns {Point[]}
 */
function computePressurePoints(gpsPath, idealPath) {
  const pts = [];
  const n = Math.min(gpsPath.length, idealPath.length);
  for (let i = 0; i < n; i++) {
    const d = Math.hypot(gpsPath[i].x - idealPath[i].x, gpsPath[i].y - idealPath[i].y);
    if (d > 1.5) {
      pts.push({ ...gpsPath[i], _pressure: d });
    }
  }
  return pts;
}

/**
 * Main fit computation.
 * @param {Point[]} rawNeckPoints
 * @param {FitInputs} inputs
 * @param {{ smoothing?: number }} [options]
 * @returns {FitResult}
 */
export function computeFit(rawNeckPoints, inputs, options = {}) {
  const warnings = [];
  const smoothing = options.smoothing ?? 0;

  let neckPoints = rawNeckPoints.map((p) => ({ ...p }));
  if (smoothing > 0) {
    neckPoints = smoothPolygon(neckPoints, smoothing);
  }
  neckPoints = scaleProfileToPerimeter(neckPoints, inputs.neckCircumference);

  const collarOffsetPoints = offsetPolygon(neckPoints, inputs.clearanceOffset);
  const table = buildArcLengthTable(collarOffsetPoints);
  const collarPathLength = table.total;

  const sElecStart = ((inputs.electronicsPlacementS % collarPathLength) + collarPathLength) % collarPathLength;
  const elecLen = Math.max(0, inputs.electronicsLength);
  const gpsLen = Math.max(0, inputs.gpsAntennaLength);

  const sElecEnd = (sElecStart + elecLen) % collarPathLength;
  const sGpsStart = sElecEnd;
  const sGpsEnd = (sGpsStart + gpsLen) % collarPathLength;
  const sStrapStart = sGpsEnd;
  const sStrapEnd = sElecStart;

  // Rigid electronics — straight segment from start tangent
  const elecStart = getPointAtS(table, sElecStart);
  const elecTangent = getTangentAtS(table, sElecStart);
  const elecEnd = {
    x: elecStart.x + elecTangent.x * elecLen,
    y: elecStart.y + elecTangent.y * elecLen,
  };
  const electronicsPath = elecLen > 0 ? [elecStart, elecEnd] : [elecStart];

  const idealElecPath = extractPathSegment(table, sElecStart, sElecStart + elecLen, 25);
  const maxElectronicsGap = elecLen > 0 ? maxGapToLine(elecStart, elecEnd, idealElecPath) : 0;
  const maxInterferenceDepth = elecLen > 0
    ? maxLinePolygonPenetration(elecStart, elecEnd, neckPoints)
    : 0;

  // GPS / antenna semi-flexible
  const gpsPath = gpsLen > 0
    ? buildGpsPath(table, sGpsStart, gpsLen, inputs.gpsAntennaStiffness)
    : [];
  const idealGpsPath = gpsLen > 0
    ? extractPathSegment(table, sGpsStart, sGpsStart + gpsLen, 25)
    : [];

  const { maxCurvature: maxGpsCurvature, minBendRadius: minGpsBendRadius } = computeCurvature(gpsPath);

  // Strap — follows remaining offset path
  const strapPath = extractPathSegment(table, sStrapStart, sStrapEnd, 40);

  const strapLength =
    collarPathLength + inputs.slack - elecLen - gpsLen;

  const segments = [
    {
      type: 'electronics',
      length: elecLen,
      thickness: inputs.electronicsThickness,
      stiffness: 'rigid',
      startS: sElecStart,
      endS: sElecEnd,
      pathPoints: electronicsPath,
    },
    {
      type: 'gpsAntenna',
      length: gpsLen,
      thickness: inputs.gpsAntennaThickness,
      stiffness: inputs.gpsAntennaStiffness,
      startS: sGpsStart,
      endS: sGpsEnd,
      pathPoints: gpsPath,
    },
    {
      type: 'strap',
      length: Math.max(0, strapLength),
      thickness: inputs.strapThickness,
      stiffness: 'fully-flexible',
      startS: sStrapStart,
      endS: sStrapEnd,
      pathPoints: strapPath,
    },
  ];

  // Warnings
  if (strapLength < 0) {
    warnings.push(
      `Strap length is negative (${strapLength.toFixed(1)} mm). Electronics + GPS lengths exceed the collar loop.`
    );
  } else if (strapLength < MIN_STRAP_LENGTH) {
    warnings.push(
      `Strap length (${strapLength.toFixed(1)} mm) is below minimum manufacturable length (${MIN_STRAP_LENGTH} mm).`
    );
  }

  if (maxElectronicsGap > inputs.clearanceOffset * 0.5) {
    warnings.push(
      `Electronics bridges with up to ${maxElectronicsGap.toFixed(1)} mm gap from ideal collar path.`
    );
  }

  if (maxInterferenceDepth > 0.5) {
    warnings.push(
      `Electronics segment penetrates neck contour by up to ${maxInterferenceDepth.toFixed(1)} mm.`
    );
  }

  if (gpsLen > 0 && minGpsBendRadius < inputs.gpsMinBendRadius) {
    warnings.push(
      `GPS/antenna bend radius (${minGpsBendRadius.toFixed(1)} mm) is below minimum (${inputs.gpsMinBendRadius} mm).`
    );
  }

  if (elecLen + gpsLen > collarPathLength * 0.95) {
    warnings.push('Electronics and GPS sections consume nearly the entire collar loop — very little strap remains.');
  }

  const bendingEnergy = estimateBendingEnergy(
    gpsPath,
    inputs.gpsAntennaYoungsModulus ?? 2.5,
    inputs.gpsAntennaThickness
  );

  const gapIndicators = [];
  if (maxElectronicsGap > 1) {
    for (let i = 0; i < idealElecPath.length; i += 3) {
      const p = idealElecPath[i];
      const d = pointToSegmentDistance(p, elecStart, elecEnd);
      if (d > 1) gapIndicators.push({ ...p, _gap: d });
    }
  }

  const pressurePoints = computePressurePoints(gpsPath, idealGpsPath);

  const isValid =
    strapLength >= 0 &&
    strapLength >= MIN_STRAP_LENGTH &&
    maxInterferenceDepth < 1 &&
    (gpsLen === 0 || minGpsBendRadius >= inputs.gpsMinBendRadius);

  return {
    collarPathLength,
    strapLength,
    maxGpsCurvature,
    minGpsBendRadius: gpsLen > 0 ? minGpsBendRadius : Infinity,
    maxElectronicsGap,
    maxInterferenceDepth,
    isValid,
    warnings,
    segments,
    neckPoints,
    collarOffsetPoints,
    gapIndicators,
    pressurePoints,
    bendingEnergy,
  };
}

/**
 * Generate fit report as plain text.
 * @param {FitResult} result
 * @param {FitInputs} inputs
 * @param {string} profileName
 * @returns {string}
 */
export function generateFitReport(result, inputs, profileName) {
  const lines = [
    'Halo Collar 6 — Neck Fit Report',
    '================================',
    `Profile: ${profileName}`,
    `Date: ${new Date().toISOString()}`,
    '',
    '--- Neck ---',
    `Circumference: ${inputs.neckCircumference.toFixed(1)} mm`,
    `Clearance offset: ${inputs.clearanceOffset.toFixed(1)} mm`,
    `Collar path length: ${result.collarPathLength.toFixed(1)} mm`,
    '',
    '--- Components ---',
    `Electronics length: ${inputs.electronicsLength.toFixed(1)} mm (rigid)`,
    `GPS/Antenna length: ${inputs.gpsAntennaLength.toFixed(1)} mm (stiffness ${(inputs.gpsAntennaStiffness * 100).toFixed(0)}%)`,
    `Strap length (calculated): ${result.strapLength.toFixed(1)} mm`,
    `Slack: ${inputs.slack.toFixed(1)} mm`,
    '',
    '--- Fit Metrics ---',
    `Max GPS curvature: ${result.maxGpsCurvature.toFixed(4)} 1/mm`,
    `Min GPS bend radius: ${result.minGpsBendRadius === Infinity ? 'N/A' : result.minGpsBendRadius.toFixed(1) + ' mm'}`,
    `Max electronics gap: ${result.maxElectronicsGap.toFixed(1)} mm`,
    `Max interference depth: ${result.maxInterferenceDepth.toFixed(1)} mm`,
    `Est. GPS bending energy: ${result.bendingEnergy.toFixed(2)} (relative)`,
    '',
    '--- Status ---',
    `Valid fit: ${result.isValid ? 'YES' : 'NO'}`,
  ];
  if (result.warnings.length) {
    lines.push('', 'Warnings:');
    result.warnings.forEach((w) => lines.push(`  • ${w}`));
  }
  return lines.join('\n');
}

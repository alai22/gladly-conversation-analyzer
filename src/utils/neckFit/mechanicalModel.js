/**
 * Simplified mechanical fit model for Halo Collar 6 neck-fit exploration.
 *
 * Assembly model: Electronics and GPS/antenna are serially attached (parallel at
 * the junction). The strap closes the loop. Rigidity lifts hardware off the
 * neck — neck gaps are the primary output, not inter-component separation.
 */

import {
  angleBetweenDeg,
  buildArcLengthTable,
  buildRigidArcPath,
  closestPointOnClosedPath,
  computeCurvature,
  ensureTracheaDown,
  extractPathSegment,
  findArcLengthAtExtremeY,
  getPointAtS,
  getTangentAtS,
  lerpPoint,
  maxPolylinePolygonPenetration,
  offsetPolygon,
  polylineLength,
  rigidArcExitTangent,
  RIGID_STRAIGHT_BEND_RADIUS,
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
 * @property {number} electronicsBendRadius mm fixed rigid bend radius (large = straight)
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
 * @property {number} maxElectronicsNeckGap
 * @property {number} maxGpsNeckGap
 * @property {number} maxNeckGap
 * @property {number} maxElectronicsGap @deprecated alias for maxElectronicsNeckGap
 * @property {number} junctionAngleDeg angle at electronics→GPS joint
 * @property {number} maxInterferenceDepth
 * @property {boolean} isValid
 * @property {string[]} warnings
 * @property {CollarSegment[]} segments
 * @property {Point[]} neckPoints
 * @property {Point[]} collarOffsetPoints
 * @property {Point[]} gapIndicators air gaps between hardware and neck seating path
 * @property {Point[]} pressurePoints contact / compression zones at neck
 * @property {Point | null} junctionPoint electronics–GPS attachment
 * @property {Point} tracheaPoint throat / ground side of neck
 * @property {Point} skyPoint back of neck / sky side
 * @property {number} bendingEnergy
 */

export const MIN_STRAP_LENGTH = 30; // mm manufacturability minimum

export const DEFAULT_FIT_INPUTS = {
  neckCircumference: 350,
  clearanceOffset: 8,
  electronicsLength: 60,
  electronicsThickness: 12,
  electronicsPlacementS: 0,
  electronicsBendRadius: 1200,
  gpsAntennaLength: 55,
  gpsAntennaThickness: 8,
  gpsAntennaStiffness: 0.5,
  gpsAntennaYoungsModulus: 2.5,
  gpsMinBendRadius: 15,
  strapThickness: 4,
  slack: 0,
};

function gpsStiffnessFactor(stiffness) {
  return Math.max(0, Math.min(1, stiffness));
}

/**
 * GPS path attached to electronics end, parallel at junction.
 * Stiffness controls how much the rubber section conforms to the neck vs. staying straight.
 * @param {Point} attachPoint electronics exit (GPS entry)
 * @param {Point} attachTangent unit tangent — shared with electronics at junction
 * @param {ReturnType<typeof buildArcLengthTable>} table
 * @param {number} sIdealStart arc position on neck path where GPS would ideally begin
 * @param {number} length
 * @param {number} stiffness 0-1
 * @returns {Point[]}
 */
function buildGpsPathAttached(attachPoint, attachTangent, table, sIdealStart, length, stiffness) {
  const factor = gpsStiffnessFactor(stiffness);
  if (length <= 0) return [attachPoint];

  const samples = Math.max(20, Math.ceil(length / 2));
  const result = [attachPoint];

  for (let i = 1; i <= samples; i++) {
    const t = i / samples;
    const straightPt = {
      x: attachPoint.x + attachTangent.x * length * t,
      y: attachPoint.y + attachTangent.y * length * t,
    };
    const idealPt = getPointAtS(table, sIdealStart + t * length);
    // Conformity ramps along length; junction stays parallel to electronics
    const blend = (1 - factor) * Math.pow(t, 0.85);
    result.push(lerpPoint(straightPt, idealPt, blend));
  }
  return result;
}

function estimateBendingEnergy(path, youngsModulus, thickness) {
  const { curvatures } = computeCurvature(path);
  const I = (thickness ** 3) / 12;
  const E = youngsModulus * 1e6;
  let energy = 0;
  const ds = polylineLength(path) / Math.max(curvatures.length, 1);
  for (const k of curvatures) {
    energy += 0.5 * E * I * k * k * ds;
  }
  return energy;
}

/**
 * Measure air gaps between a hardware centerline and the desired neck seating path.
 * @param {Point[]} centerline
 * @param {ReturnType<typeof buildArcLengthTable>} table
 * @param {number} [sampleEvery=2]
 * @returns {{ maxGap: number, indicators: Point[] }}
 */
function analyzeNeckGaps(centerline, table, sampleEvery = 2) {
  let maxGap = 0;
  const indicators = [];
  for (let i = 0; i < centerline.length; i += sampleEvery) {
    const p = centerline[i];
    const closest = closestPointOnClosedPath(p, table);
    maxGap = Math.max(maxGap, closest.distance);
    if (closest.distance > 1.2) {
      indicators.push({
        x: (p.x + closest.point.x) / 2,
        y: (p.y + closest.point.y) / 2,
        _gap: closest.distance,
      });
    }
  }
  return { maxGap, indicators };
}

/**
 * Points where hardware presses into or sits tight against the neck seating path.
 * @param {Point[]} centerline
 * @param {ReturnType<typeof buildArcLengthTable>} table
 * @param {number} clearanceOffset
 * @returns {Point[]}
 */
function computeNeckContactPoints(centerline, table, clearanceOffset) {
  const pts = [];
  for (let i = 0; i < centerline.length; i += 2) {
    const p = centerline[i];
    const closest = closestPointOnClosedPath(p, table);
    if (closest.distance < clearanceOffset * 0.35) {
      pts.push({ ...p, _pressure: clearanceOffset - closest.distance });
    }
  }
  return pts;
}

/**
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
  neckPoints = ensureTracheaDown(neckPoints);
  neckPoints = scaleProfileToPerimeter(neckPoints, inputs.neckCircumference);

  const collarOffsetPoints = offsetPolygon(neckPoints, inputs.clearanceOffset);
  const table = buildArcLengthTable(collarOffsetPoints);
  const collarPathLength = table.total;

  // Trachea (+y / ground) is the strap-side anchor; placement is offset from there.
  const trachea = findArcLengthAtExtremeY(neckPoints, 'max');
  const sky = findArcLengthAtExtremeY(neckPoints, 'min');
  const sElecStart =
    ((trachea.s + inputs.electronicsPlacementS) % collarPathLength + collarPathLength) %
    collarPathLength;
  const elecLen = Math.max(0, inputs.electronicsLength);
  const gpsLen = Math.max(0, inputs.gpsAntennaLength);

  const sIdealGpsStart = (sElecStart + elecLen) % collarPathLength;
  const sIdealGpsEnd = (sIdealGpsStart + gpsLen) % collarPathLength;
  const sStrapStart = sIdealGpsEnd;
  const sStrapEnd = sElecStart;

  // Rigid electronics — fixed-curvature arc (or straight when bend radius is large)
  const elecStart = getPointAtS(table, sElecStart);
  const elecStartTangent = getTangentAtS(table, sElecStart);
  const bendRadius = inputs.electronicsBendRadius ?? 1200;
  const electronicsPath =
    elecLen > 0
      ? buildRigidArcPath(elecStart, elecStartTangent, elecLen, bendRadius, 16)
      : [elecStart];
  const elecEnd = electronicsPath[electronicsPath.length - 1];
  const elecExitTangent = rigidArcExitTangent(elecStart, elecStartTangent, elecLen, bendRadius);

  // GPS attached at elecEnd, parallel at junction; rubber may bend toward neck
  const gpsPath =
    gpsLen > 0
      ? buildGpsPathAttached(elecEnd, elecExitTangent, table, sIdealGpsStart, gpsLen, inputs.gpsAntennaStiffness)
      : [elecEnd];
  const gpsEnd = gpsPath[gpsPath.length - 1];

  // Junction parallelism at electronics→GPS (parallel by construction when GPS is stiff)
  let junctionAngleDeg = 0;
  if (gpsPath.length >= 2) {
    const gpsEntry = {
      x: gpsPath[1].x - gpsPath[0].x,
      y: gpsPath[1].y - gpsPath[0].y,
    };
    const elen = Math.hypot(gpsEntry.x, gpsEntry.y) || 1;
    junctionAngleDeg = angleBetweenDeg(elecExitTangent, { x: gpsEntry.x / elen, y: gpsEntry.y / elen });
  }

  const { maxCurvature: maxGpsCurvature, minBendRadius: minGpsBendRadius } = computeCurvature(gpsPath);

  // Strap closes loop: GPS exit → neck contour → electronics entry
  const offsetStrap = extractPathSegment(table, sStrapStart, sStrapEnd, 40);
  const strapPath =
    offsetStrap.length > 0
      ? [gpsEnd, ...offsetStrap.slice(1, -1), elecStart]
      : [gpsEnd, elecStart];

  const strapLength = collarPathLength + inputs.slack - elecLen - gpsLen;

  // Neck gaps — primary fit unknown
  const elecGaps = analyzeNeckGaps(electronicsPath, table);
  const gpsGaps = analyzeNeckGaps(gpsPath, table);
  const maxElectronicsNeckGap = elecGaps.maxGap;
  const maxGpsNeckGap = gpsGaps.maxGap;
  const maxNeckGap = Math.max(maxElectronicsNeckGap, maxGpsNeckGap);
  const gapIndicators = [...elecGaps.indicators, ...gpsGaps.indicators];

  const maxInterferenceDepth =
    elecLen > 0 ? maxPolylinePolygonPenetration(electronicsPath, neckPoints) : 0;

  const pressurePoints = [
    ...computeNeckContactPoints(electronicsPath, table, inputs.clearanceOffset),
    ...computeNeckContactPoints(gpsPath, table, inputs.clearanceOffset),
  ];

  const segments = [
    {
      type: 'electronics',
      length: elecLen,
      thickness: inputs.electronicsThickness,
      stiffness: 'rigid',
      startS: sElecStart,
      endS: sIdealGpsStart,
      pathPoints: electronicsPath,
    },
    {
      type: 'gpsAntenna',
      length: gpsLen,
      thickness: inputs.gpsAntennaThickness,
      stiffness: inputs.gpsAntennaStiffness,
      startS: sIdealGpsStart,
      endS: sIdealGpsEnd,
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

  if (strapLength < 0) {
    warnings.push(
      `Strap length is negative (${strapLength.toFixed(1)} mm). Electronics + GPS lengths exceed the collar loop.`
    );
  } else if (strapLength < MIN_STRAP_LENGTH) {
    warnings.push(
      `Strap length (${strapLength.toFixed(1)} mm) is below minimum manufacturable length (${MIN_STRAP_LENGTH} mm).`
    );
  }

  if (maxElectronicsNeckGap > inputs.clearanceOffset * 0.4) {
    warnings.push(
      `Rigid electronics lifts up to ${maxElectronicsNeckGap.toFixed(1)} mm off the neck at clearance.`
    );
  }

  if (maxGpsNeckGap > inputs.clearanceOffset * 0.5) {
    warnings.push(
      `GPS/antenna section lifts up to ${maxGpsNeckGap.toFixed(1)} mm off the neck — reduce stiffness or adjust placement.`
    );
  }

  if (maxInterferenceDepth > 0.5) {
    warnings.push(
      `Electronics penetrates neck contour by up to ${maxInterferenceDepth.toFixed(1)} mm.`
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
    maxElectronicsNeckGap,
    maxGpsNeckGap,
    maxNeckGap,
    maxElectronicsGap: maxElectronicsNeckGap,
    junctionAngleDeg,
    maxInterferenceDepth,
    isValid,
    warnings,
    segments,
    neckPoints,
    collarOffsetPoints,
    gapIndicators,
    pressurePoints,
    junctionPoint: elecLen > 0 && gpsLen > 0 ? elecEnd : null,
    tracheaPoint: trachea.point,
    skyPoint: sky.point,
    bendingEnergy,
  };
}

/**
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
    '--- Orientation ---',
    'Sky / back of neck: top of diagram (−y)',
    'Trachea / throat: bottom of diagram (+y)',
    'Electronics strap end anchored at trachea + placement offset',
    `Electronics length: ${inputs.electronicsLength.toFixed(1)} mm (rigid arc)`,
    `Electronics bend radius: ${inputs.electronicsBendRadius >= RIGID_STRAIGHT_BEND_RADIUS ? 'straight' : inputs.electronicsBendRadius.toFixed(0) + ' mm'}`,
    `GPS/Antenna length: ${inputs.gpsAntennaLength.toFixed(1)} mm (stiffness ${(inputs.gpsAntennaStiffness * 100).toFixed(0)}%)`,
    `Strap length (calculated): ${result.strapLength.toFixed(1)} mm`,
    `Slack: ${inputs.slack.toFixed(1)} mm`,
    '',
    '--- Fit Metrics ---',
    `Max electronics–neck gap: ${result.maxElectronicsNeckGap.toFixed(1)} mm`,
    `Max GPS–neck gap: ${result.maxGpsNeckGap.toFixed(1)} mm`,
    `Max overall neck gap: ${result.maxNeckGap.toFixed(1)} mm`,
    `Electronics→GPS junction angle: ${result.junctionAngleDeg.toFixed(1)}°`,
    `Max GPS curvature: ${result.maxGpsCurvature.toFixed(4)} 1/mm`,
    `Min GPS bend radius: ${result.minGpsBendRadius === Infinity ? 'N/A' : result.minGpsBendRadius.toFixed(1) + ' mm'}`,
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

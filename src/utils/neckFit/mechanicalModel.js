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
  buildPerpendicularSegment,
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
  pointInPolygon,
  pointToPolygonBoundary,
  polylineEntryTangent,
  polylineExitTangent,
  polygonCentroid,
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
 * @property {number} strapEndpointGap GPS exit distance from ideal neck path (extra strap span)
 * @property {number} strapPathLength modeled strap centerline length including endpoint chords
 * @property {number} maxInterferenceDepth
 * @property {boolean} isValid
 * @property {string[]} warnings
 * @property {CollarSegment[]} segments
 * @property {Point[]} neckPoints
 * @property {Point[]} collarOffsetPoints
 * @property {Point[]} gapIndicators air gaps between hardware and neck seating path
 * @property {Point[]} pressurePoints contact / compression zones at neck
 * @property {Point | null} junctionPoint electronics–GPS attachment
 * @property {Point[]} staticContactPath static feedback tip (strap-side end of electronics)
 * @property {Point | null} staticContactTipPoint tip endpoint toward neck
 * @property {Point} tracheaPoint throat / ground side of neck
 * @property {Point} skyPoint back of neck / sky side
 * @property {number} bendingEnergy
 */

export const MIN_STRAP_LENGTH = 30; // mm manufacturability minimum
export const STATIC_CONTACT_TIP_LENGTH = 15; // mm perpendicular probe for static feedback
export const STATIC_CONTACT_TIP_THICKNESS = 4; // mm visual stroke width

export const DEFAULT_FIT_INPUTS = {
  neckCircumference: 350,
  clearanceOffset: 8,
  electronicsLength: 60,
  electronicsThickness: 12,
  electronicsPlacementS: 0,
  electronicsBendRadius: 40,
  gpsAntennaLength: 55,
  gpsAntennaThickness: 8,
  gpsAntennaStiffness: 0.7,
  gpsAntennaYoungsModulus: 2.5,
  gpsMinBendRadius: 15,
  strapThickness: 4,
  slack: 0,
};

function gpsStiffnessFactor(stiffness) {
  return Math.max(0, Math.min(1, stiffness));
}

/**
 * True when a centerline point intrudes into the neck or its physical half-thickness.
 * @param {Point} p
 * @param {Point[]} neckPoints
 * @param {number} minStandoff mm from neck skin to centerline
 * @returns {boolean}
 */
function intrudesNeck(p, neckPoints, minStandoff) {
  return (
    pointInPolygon(p, neckPoints) ||
    pointToPolygonBoundary(p, neckPoints) < minStandoff - 0.05
  );
}

/**
 * GPS path attached to electronics end, parallel at junction.
 * Stiffness controls how much the rubber section conforms to the neck vs. staying straight.
 * Points that would pass through the neck are redirected to the collar seating path.
 * @param {Point} attachPoint electronics exit (GPS entry)
 * @param {Point} attachTangent unit tangent — shared with electronics at junction
 * @param {ReturnType<typeof buildArcLengthTable>} table collar offset path
 * @param {Point[]} neckPoints neck skin contour
 * @param {number} sIdealStart arc position on neck path where GPS would ideally begin
 * @param {number} length
 * @param {number} stiffness 0-1
 * @param {number} clearanceOffset mm
 * @param {number} gpsThickness mm
 * @returns {Point[]}
 */
function buildGpsPathAttached(
  attachPoint,
  attachTangent,
  table,
  neckPoints,
  sIdealStart,
  length,
  stiffness,
  clearanceOffset,
  gpsThickness
) {
  const factor = gpsStiffnessFactor(stiffness);
  if (length <= 0) return [attachPoint];

  const minStandoff = Math.max(clearanceOffset, gpsThickness / 2);
  const samples = Math.max(20, Math.ceil(length / 2));
  const result = [attachPoint];

  // Hold exit tangent before bending toward neck — keeps junction parallel to electronics.
  const tangentRun = length * (0.06 + factor * 0.3);
  const bendLength = Math.max(length - tangentRun, length * 0.05);

  for (let i = 1; i <= samples; i++) {
    const t = i / samples;
    const s = length * t;
    const straightPt = {
      x: attachPoint.x + attachTangent.x * s,
      y: attachPoint.y + attachTangent.y * s,
    };
    const idealPt = getPointAtS(table, sIdealStart + s);

    let blend = 0;
    if (s > tangentRun && bendLength > 0) {
      const u = Math.min(1, (s - tangentRun) / bendLength);
      blend = (1 - factor) * u * u * (3 - 2 * u);
    }
    let pt = lerpPoint(straightPt, idealPt, blend);
    if (intrudesNeck(pt, neckPoints, minStandoff)) {
      pt = { ...idealPt };
    }
    result.push(pt);
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
        hardwarePoint: { x: p.x, y: p.y },
        seatingPoint: { x: closest.point.x, y: closest.point.y },
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
  const bendRadius = inputs.electronicsBendRadius ?? 40;
  const electronicsPath =
    elecLen > 0
      ? buildRigidArcPath(elecStart, elecStartTangent, elecLen, bendRadius, 16)
      : [elecStart];
  const elecEnd = electronicsPath[electronicsPath.length - 1];
  const elecEntryTangent = polylineEntryTangent(electronicsPath, elecStartTangent);
  const neckCenter = polygonCentroid(neckPoints);
  const staticContactPath =
    elecLen > 0
      ? buildPerpendicularSegment(
          elecStart,
          elecEntryTangent,
          STATIC_CONTACT_TIP_LENGTH,
          neckCenter
        )
      : [];
  const staticContactTipPoint =
    staticContactPath.length >= 2 ? staticContactPath[staticContactPath.length - 1] : null;

  const elecExitTangent = polylineExitTangent(
    electronicsPath,
    rigidArcExitTangent(elecStart, elecStartTangent, elecLen, bendRadius)
  );

  // GPS attached at elecEnd, parallel at junction; rubber may bend toward neck
  const gpsPath =
    gpsLen > 0
      ? buildGpsPathAttached(
          elecEnd,
          elecExitTangent,
          table,
          neckPoints,
          sIdealGpsStart,
          gpsLen,
          inputs.gpsAntennaStiffness,
          inputs.clearanceOffset,
          inputs.gpsAntennaThickness
        )
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

  const idealGpsEndPt = getPointAtS(table, sIdealGpsEnd);
  const strapEndpointGap = Math.hypot(gpsEnd.x - idealGpsEndPt.x, gpsEnd.y - idealGpsEndPt.y);
  const strapPathLength = polylineLength(strapPath);

  // Neck gaps — primary fit unknown
  const elecGaps = analyzeNeckGaps(electronicsPath, table);
  const gpsGaps = analyzeNeckGaps(gpsPath, table);
  const maxElectronicsNeckGap = elecGaps.maxGap;
  const maxGpsNeckGap = gpsGaps.maxGap;
  const maxNeckGap = Math.max(maxElectronicsNeckGap, maxGpsNeckGap);
  const gapIndicators = [...elecGaps.indicators, ...gpsGaps.indicators];

  const elecInterference =
    elecLen > 0 ? maxPolylinePolygonPenetration(electronicsPath, neckPoints) : 0;
  const gpsInterference =
    gpsLen > 0 ? maxPolylinePolygonPenetration(gpsPath, neckPoints) : 0;
  const maxInterferenceDepth = Math.max(elecInterference, gpsInterference);

  const pressurePoints = [
    ...computeNeckContactPoints(electronicsPath, table, inputs.clearanceOffset),
    ...computeNeckContactPoints(gpsPath, table, inputs.clearanceOffset),
    ...(staticContactPath.length >= 2
      ? computeNeckContactPoints(staticContactPath, table, inputs.clearanceOffset)
      : []),
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
    const parts = [];
    if (elecInterference > 0.5) parts.push(`electronics (${elecInterference.toFixed(1)} mm)`);
    if (gpsInterference > 0.5) parts.push(`GPS/antenna (${gpsInterference.toFixed(1)} mm)`);
    warnings.push(`Hardware penetrates neck contour: ${parts.join(', ')}.`);
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
    strapEndpointGap,
    strapPathLength,
    maxInterferenceDepth,
    isValid,
    warnings,
    segments,
    neckPoints,
    collarOffsetPoints,
    gapIndicators,
    pressurePoints,
    junctionPoint: elecLen > 0 && gpsLen > 0 ? elecEnd : null,
    staticContactPath,
    staticContactTipPoint,
    tracheaPoint: trachea.point,
    skyPoint: sky.point,
    bendingEnergy,
  };
}

/**
 * Score a fit for collar rotation optimization (lower is better).
 * @param {FitResult} result
 * @param {FitInputs} inputs
 * @returns {number}
 */
function scoreFitForPlacement(result, inputs) {
  let score = result.maxNeckGap + 0.5 * result.strapEndpointGap;
  if (result.minGpsBendRadius < inputs.gpsMinBendRadius) score += 200;
  if (result.strapLength < MIN_STRAP_LENGTH) score += 100;
  if (result.maxInterferenceDepth > 1) score += 150;
  return score;
}

/**
 * Normalize placement offset to roughly ±half the collar loop for UI display.
 * @param {number} offset
 * @param {number} loopLength
 * @returns {number}
 */
function normalizePlacementOffset(offset, loopLength) {
  let o = ((offset % loopLength) + loopLength) % loopLength;
  if (o > loopLength / 2) o -= loopLength;
  return o;
}

/**
 * How much a candidate placement improves gap and strap closure vs current.
 * @param {FitResult} fromResult
 * @param {FitResult} toResult
 * @returns {number}
 */
function placementImprovement(fromResult, toResult) {
  const gapGain = fromResult.maxNeckGap - toResult.maxNeckGap;
  const strapGain = fromResult.strapEndpointGap - toResult.strapEndpointGap;
  return gapGain + 0.5 * strapGain;
}

/**
 * Search collar rotation (placement offset from trachea) to minimize neck gaps
 * and strap closure span while respecting bend-radius constraints.
 *
 * Uses incremental bidirectional search: at each step tries clockwise (+) and
 * counter-clockwise (−) and follows whichever reduces gap / strap span more.
 *
 * @param {Point[]} rawNeckPoints
 * @param {FitInputs} inputs
 * @param {{ smoothing?: number, coarseStep?: number, fineStep?: number, maxIterations?: number }} [options]
 * @returns {{ optimalPlacementS: number, fitResult: FitResult, baselineMaxNeckGap: number, baselineStrapEndpointGap: number }}
 */
export function optimizeCollarPlacement(rawNeckPoints, inputs, options = {}) {
  const smoothing = options.smoothing ?? 0;
  const coarseStep = options.coarseStep ?? 5;
  const fineStep = options.fineStep ?? 1;
  const maxIterations = options.maxIterations ?? 200;

  const baseline = computeFit(rawNeckPoints, inputs, { smoothing });
  const loop = baseline.collarPathLength;

  const evaluate = (offsetS) => {
    const placementS = normalizePlacementOffset(offsetS, loop);
    const result = computeFit(
      rawNeckPoints,
      { ...inputs, electronicsPlacementS: placementS },
      { smoothing }
    );
    return { placementS, result, score: scoreFitForPlacement(result, inputs) };
  };

  let current = evaluate(inputs.electronicsPlacementS);

  const climb = (step) => {
    const minGain = 0.05;
    for (let i = 0; i < maxIterations; i++) {
      const cw = evaluate(current.placementS + step);
      const ccw = evaluate(current.placementS - step);
      const cwGain = placementImprovement(current.result, cw.result);
      const ccwGain = placementImprovement(current.result, ccw.result);

      let next = null;
      if (cwGain > minGain && cwGain >= ccwGain) {
        next = cw;
      } else if (ccwGain > minGain) {
        next = ccw;
      } else if (cwGain > minGain) {
        next = cw;
      }

      if (!next) break;

      const gain = placementImprovement(current.result, next.result);
      const scoreImproved = next.score < current.score - 0.01;
      const scoreNeutral = Math.abs(next.score - current.score) <= 0.01;
      if (!scoreImproved && !(scoreNeutral && gain > 0.5)) break;
      if (next.score > current.score + 5) break;

      current = next;
    }
  };

  climb(coarseStep);
  climb(fineStep);

  return {
    optimalPlacementS: Math.round(current.placementS * 10) / 10,
    fitResult: current.result,
    baselineMaxNeckGap: baseline.maxNeckGap,
    baselineStrapEndpointGap: baseline.strapEndpointGap,
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
    `Static contact tip: ${STATIC_CONTACT_TIP_LENGTH} mm (perpendicular, strap-side end)`,
    `Electronics bend radius: ${inputs.electronicsBendRadius >= RIGID_STRAIGHT_BEND_RADIUS ? 'straight' : inputs.electronicsBendRadius.toFixed(0) + ' mm'}`,
    `GPS/Antenna length: ${inputs.gpsAntennaLength.toFixed(1)} mm (stiffness ${(inputs.gpsAntennaStiffness * 100).toFixed(0)}%)`,
    `Strap length (calculated): ${result.strapLength.toFixed(1)} mm`,
    `Slack: ${inputs.slack.toFixed(1)} mm`,
    '',
    '--- Fit Metrics ---',
    `Max electronics–neck gap: ${result.maxElectronicsNeckGap.toFixed(1)} mm`,
    `Max GPS–neck gap: ${result.maxGpsNeckGap.toFixed(1)} mm`,
    `Max overall neck gap: ${result.maxNeckGap.toFixed(1)} mm`,
    `Strap endpoint gap (GPS exit): ${result.strapEndpointGap.toFixed(1)} mm`,
    `Modeled strap path length: ${result.strapPathLength.toFixed(1)} mm`,
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

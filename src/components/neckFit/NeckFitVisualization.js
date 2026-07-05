import React, { useMemo } from 'react';
import {
  normalizeForView,
  parseViewBox,
  pointsToSvgPath,
  polygonCentroid,
} from '../../utils/neckFit/geometry';
import { SEGMENT_COLORS, SEGMENT_LABELS } from '../../utils/neckFit/export';

const NeckFitVisualization = ({
  fitResult,
  showGaps,
  showCurvature,
  showPressure,
}) => {
  const viewData = useMemo(() => {
    if (!fitResult) return null;
    const all = [
      ...fitResult.neckPoints,
      ...fitResult.collarOffsetPoints,
      ...fitResult.segments.flatMap((s) => s.pathPoints),
    ];
    return normalizeForView(all, 60);
  }, [fitResult]);

  const vb = useMemo(() => {
    if (!viewData?.viewBox) return null;
    return parseViewBox(viewData.viewBox);
  }, [viewData]);

  if (!fitResult || !viewData || !vb) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px] bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500 text-sm">Adjust inputs to see the fit visualization</p>
      </div>
    );
  }

  const {
    neckPoints,
    collarOffsetPoints,
    segments,
    gapIndicators,
    pressurePoints,
    junctionPoint,
    tracheaPoint,
    skyPoint,
  } = fitResult;

  const labelX = vb.x + vb.w / 2;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden h-full flex flex-col">
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-800">Cross-Section View</h3>
        <p className="text-xs text-gray-500">
          Top = sky / back of neck · Bottom = trachea / throat (ground). Strap end at throat; GPS wraps upward.
        </p>
      </div>
      <div className="flex-1 p-2 min-h-[420px]">
        <svg
          viewBox={viewData.viewBox}
          className="w-full h-full"
          style={{ maxHeight: '560px' }}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Orientation labels */}
          <text
            x={labelX}
            y={vb.y + 16}
            textAnchor="middle"
            fontSize={10}
            fontWeight={600}
            fill="#64748b"
          >
            ↑ Sky · Back of neck
          </text>
          <text
            x={labelX}
            y={vb.y + vb.h - 8}
            textAnchor="middle"
            fontSize={10}
            fontWeight={600}
            fill="#64748b"
          >
            ↓ Trachea · Throat (ground)
          </text>

          {/* Neck fill */}
          <path
            d={pointsToSvgPath(neckPoints, true)}
            fill="#fef3c7"
            stroke="#d97706"
            strokeWidth={1.5}
            opacity={0.9}
          />

          {/* Trachea / sky landmarks on neck */}
          {tracheaPoint && (
            <g>
              <circle cx={tracheaPoint.x} cy={tracheaPoint.y} r={4} fill="#b45309" opacity={0.35} />
              <text
                x={tracheaPoint.x}
                y={tracheaPoint.y + 14}
                textAnchor="middle"
                fontSize={8}
                fill="#92400e"
              >
                Throat
              </text>
            </g>
          )}
          {skyPoint && (
            <g>
              <circle cx={skyPoint.x} cy={skyPoint.y} r={4} fill="#0284c7" opacity={0.35} />
              <text
                x={skyPoint.x}
                y={skyPoint.y - 8}
                textAnchor="middle"
                fontSize={8}
                fill="#0369a1"
              >
                Back
              </text>
            </g>
          )}

          {/* Ideal collar offset path (dashed) */}
          <path
            d={pointsToSvgPath(collarOffsetPoints, true)}
            fill="none"
            stroke="#94a3b8"
            strokeWidth={1}
            strokeDasharray="5 4"
          />

          {/* Neck air-gap indicators */}
          {showGaps &&
            gapIndicators.map((p, i) => (
              <circle
                key={`gap-${i}`}
                cx={p.x}
                cy={p.y}
                r={2.5}
                fill="#ef4444"
                opacity={0.8}
              />
            ))}

          {/* Electronics → GPS junction */}
          {junctionPoint && (
            <circle
              cx={junctionPoint.x}
              cy={junctionPoint.y}
              r={4}
              fill="none"
              stroke="#6366f1"
              strokeWidth={1.5}
            />
          )}

          {/* Collar segments */}
          {segments.map((seg) => {
            if (!seg.pathPoints.length) return null;
            const color = SEGMENT_COLORS[seg.type];
            return (
              <g key={seg.type}>
                <path
                  d={pointsToSvgPath(seg.pathPoints, false)}
                  fill="none"
                  stroke={color}
                  strokeWidth={seg.thickness}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={0.85}
                />
                <path
                  d={pointsToSvgPath(seg.pathPoints, false)}
                  fill="none"
                  stroke={color}
                  strokeWidth={1.5}
                  strokeLinecap="round"
                  opacity={0.5}
                />
              </g>
            );
          })}

          {showCurvature &&
            segments
              .filter((s) => s.type === 'gpsAntenna' || s.type === 'electronics')
              .flatMap((s) => s.pathPoints)
              .filter((_, i, arr) => i > 0 && i < arr.length - 1 && i % 3 === 0)
              .map((p, i) => (
                <circle key={`curv-${i}`} cx={p.x} cy={p.y} r={2} fill="#8b5cf6" opacity={0.6} />
              ))}

          {showPressure &&
            pressurePoints.map((p, i) => (
              <circle
                key={`press-${i}`}
                cx={p.x}
                cy={p.y}
                r={3}
                fill="#f59e0b"
                opacity={0.7}
              />
            ))}

          {segments.map((seg) => {
            if (!seg.pathPoints.length) return null;
            const mid = seg.pathPoints[Math.floor(seg.pathPoints.length / 2)];
            const c = polygonCentroid(fitResult.neckPoints);
            const dx = mid.x - c.x;
            const dy = mid.y - c.y;
            const len = Math.hypot(dx, dy) || 1;
            const lx = mid.x + (dx / len) * (seg.thickness + 6);
            const ly = mid.y + (dy / len) * (seg.thickness + 6);
            return (
              <text
                key={`label-${seg.type}`}
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={9}
                fontWeight={600}
                fill={SEGMENT_COLORS[seg.type]}
              >
                {SEGMENT_LABELS[seg.type]}
              </text>
            );
          })}

          <circle
            cx={polygonCentroid(neckPoints).x}
            cy={polygonCentroid(neckPoints).y}
            r={2}
            fill="#9ca3af"
            opacity={0.5}
          />
        </svg>
      </div>

      <div className="px-4 py-2 border-t border-gray-100 flex flex-wrap gap-3 text-xs">
        {Object.entries(SEGMENT_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: SEGMENT_COLORS[key] }}
            />
            <span className="text-gray-600">{label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-amber-700 opacity-50" />
          <span className="text-gray-600">Throat</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-sky-600 opacity-50" />
          <span className="text-gray-600">Back / sky</span>
        </div>
        {showGaps && (
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500 opacity-75" />
            <span className="text-gray-600">Neck air gap</span>
          </div>
        )}
        {fitResult.junctionPoint && (
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full border-2 border-indigo-500" />
            <span className="text-gray-600">Enclosure–GPS joint</span>
          </div>
        )}
        {showPressure && (
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-amber-500 opacity-75" />
            <span className="text-gray-600">Neck contact</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default NeckFitVisualization;

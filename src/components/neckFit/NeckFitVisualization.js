import React, { useMemo } from 'react';
import {
  normalizeForView,
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

  if (!fitResult || !viewData) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px] bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500 text-sm">Adjust inputs to see the fit visualization</p>
      </div>
    );
  }

  const { neckPoints, collarOffsetPoints, segments, gapIndicators, pressurePoints, junctionPoint } = fitResult;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden h-full flex flex-col">
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-800">Cross-Section View</h3>
        <p className="text-xs text-gray-500">Rigid/semi-rigid hardware attached in series; red markers = air gap to neck</p>
      </div>
      <div className="flex-1 p-2 min-h-[420px]">
        <svg
          viewBox={viewData.viewBox}
          className="w-full h-full"
          style={{ maxHeight: '560px' }}
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Neck fill */}
          <path
            d={pointsToSvgPath(neckPoints, true)}
            fill="#fef3c7"
            stroke="#d97706"
            strokeWidth={1.5}
            opacity={0.9}
          />

          {/* Ideal collar offset path (dashed) */}
          <path
            d={pointsToSvgPath(collarOffsetPoints, true)}
            fill="none"
            stroke="#94a3b8"
            strokeWidth={1}
            strokeDasharray="5 4"
          />

          {/* Neck air-gap indicators (hardware lifted off seating path) */}
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

          {/* Electronics → GPS junction (always attached, parallel) */}
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

          {/* Collar segments with thickness */}
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

          {/* Curvature markers on GPS segment */}
          {showCurvature &&
            segments
              .filter((s) => s.type === 'gpsAntenna' || s.type === 'electronics')
              .flatMap((s) => s.pathPoints)
              .filter((_, i, arr) => i > 0 && i < arr.length - 1 && i % 3 === 0)
              .map((p, i) => (
                <circle key={`curv-${i}`} cx={p.x} cy={p.y} r={2} fill="#8b5cf6" opacity={0.6} />
              ))}

          {/* Pressure / contact zones */}
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

          {/* Segment labels */}
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

          {/* Center marker */}
          <circle
            cx={polygonCentroid(neckPoints).x}
            cy={polygonCentroid(neckPoints).y}
            r={2}
            fill="#9ca3af"
            opacity={0.5}
          />
        </svg>
      </div>

      {/* Legend */}
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

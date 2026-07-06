import React, { useMemo, useState, useEffect } from 'react';
import {
  normalizeForView,
  parseViewBox,
  pointsToSvgPath,
  polygonCentroid,
} from '../../utils/neckFit/geometry';
import { SEGMENT_COLORS, SEGMENT_LABELS } from '../../utils/neckFit/export';

const GUIDE_STORAGE_KEY = 'neckFitDiagramGuideSeen';

const OverlayChip = ({ label, active, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className={`px-2 py-0.5 text-[10px] font-medium rounded-full border transition-colors ${
      active
        ? 'bg-indigo-100 border-indigo-300 text-indigo-800'
        : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
    }`}
  >
    {label}
  </button>
);

const NeckFitVisualization = ({
  fitResult,
  showGaps,
  showCurvature,
  showPressure,
  onShowGapsChange,
  onShowCurvatureChange,
  onShowPressureChange,
}) => {
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(GUIDE_STORAGE_KEY)) {
        setGuideOpen(true);
        localStorage.setItem(GUIDE_STORAGE_KEY, '1');
      }
    } catch {
      /* ignore */
    }
  }, []);

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

  const worstGap = useMemo(() => {
    if (!fitResult?.gapIndicators?.length) return null;
    return fitResult.gapIndicators.reduce((best, g) =>
      (g._gap ?? 0) > (best._gap ?? 0) ? g : best
    );
  }, [fitResult]);

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
      <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-gray-800">Cross-Section View</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Top = sky / back · Bottom = trachea. Red spokes = hardware lifted off target seating path.
            </p>
          </div>
          {onShowGapsChange && (
            <div className="flex flex-wrap gap-1.5 shrink-0">
              <OverlayChip
                label="Lift-off gaps"
                active={showGaps}
                onClick={() => onShowGapsChange(!showGaps)}
              />
              <OverlayChip
                label="Contact"
                active={showPressure}
                onClick={() => onShowPressureChange(!showPressure)}
              />
              <OverlayChip
                label="Curvature"
                active={showCurvature}
                onClick={() => onShowCurvatureChange(!showCurvature)}
              />
            </div>
          )}
        </div>

        <details
          open={guideOpen}
          onToggle={(e) => setGuideOpen(e.target.open)}
          className="text-xs text-gray-600"
        >
          <summary className="cursor-pointer select-none font-medium text-gray-700">
            Reading this diagram
          </summary>
          <ul className="mt-1.5 space-y-0.5 list-disc list-inside text-[11px] text-gray-500">
            <li>Orange fill = neck cross-section (skin)</li>
            <li>Grey dashed loop = target seating path (clearance offset from skin)</li>
            <li>Thick colored strokes = electronics, GPS, and strap</li>
            <li>Red dashed spokes = lift-off gap between hardware and seating path</li>
          </ul>
        </details>
      </div>

      <div className="flex-1 p-2 min-h-[420px]">
        <svg
          viewBox={viewData.viewBox}
          className="w-full h-full"
          style={{ maxHeight: '560px' }}
          preserveAspectRatio="xMidYMid meet"
        >
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

          <path
            d={pointsToSvgPath(neckPoints, true)}
            fill="#fef3c7"
            stroke="#d97706"
            strokeWidth={1.5}
            opacity={0.9}
          />

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

          <path
            d={pointsToSvgPath(collarOffsetPoints, true)}
            fill="none"
            stroke="#94a3b8"
            strokeWidth={1}
            strokeDasharray="5 4"
          />

          {showGaps &&
            gapIndicators.map((g, i) => {
              const hw = g.hardwarePoint ?? { x: g.x, y: g.y };
              const seat = g.seatingPoint ?? { x: g.x, y: g.y };
              const gapMm = g._gap?.toFixed(1) ?? '?';
              return (
                <g key={`gap-${i}`}>
                  <line
                    x1={hw.x}
                    y1={hw.y}
                    x2={seat.x}
                    y2={seat.y}
                    stroke="#ef4444"
                    strokeWidth={1}
                    strokeDasharray="3 2"
                    opacity={0.85}
                  >
                    <title>{`${gapMm} mm lift-off`}</title>
                  </line>
                  <circle cx={g.x} cy={g.y} r={2} fill="#ef4444" opacity={0.9}>
                    <title>{`${gapMm} mm lift-off`}</title>
                  </circle>
                </g>
              );
            })}

          {showGaps && worstGap && (
            <g>
              <rect
                x={worstGap.x + 6}
                y={worstGap.y - 10}
                width={52}
                height={14}
                rx={3}
                fill="white"
                fillOpacity={0.9}
                stroke="#ef4444"
                strokeWidth={0.5}
              />
              <text
                x={worstGap.x + 32}
                y={worstGap.y}
                textAnchor="middle"
                fontSize={8}
                fontWeight={600}
                fill="#b91c1c"
              >
                {worstGap._gap?.toFixed(0)} mm
              </text>
            </g>
          )}

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
          <span className="w-3 h-0.5 border-t border-dashed border-slate-400" style={{ width: 12 }} />
          <span className="text-gray-600">Target seating path</span>
        </div>
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
            <span className="w-3 h-0.5 bg-red-500 opacity-75" style={{ width: 12 }} />
            <span className="text-gray-600">Hardware lift-off gap</span>
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

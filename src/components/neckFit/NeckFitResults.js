import React from 'react';
import { CheckCircle, AlertTriangle, Download, FileText } from 'lucide-react';
import { MIN_STRAP_LENGTH } from '../../utils/neckFit/mechanicalModel';
import { RIGID_STRAIGHT_BEND_RADIUS } from '../../utils/neckFit/geometry';

const MetricRow = ({ label, value, highlight }) => (
  <div className="flex justify-between items-baseline py-1.5 border-b border-gray-100 last:border-0">
    <span className="text-xs text-gray-600">{label}</span>
    <span
      className={`text-sm font-medium tabular-nums ${
        highlight === 'good' ? 'text-green-700' : highlight === 'bad' ? 'text-red-700' : 'text-gray-900'
      }`}
    >
      {value}
    </span>
  </div>
);

const NeckFitResults = ({
  fitResult,
  inputs,
  profileName,
  showGaps,
  onShowGapsChange,
  showCurvature,
  onShowCurvatureChange,
  showPressure,
  onShowPressureChange,
  onExportSvg,
  onExportReport,
}) => {
  if (!fitResult) {
    return (
      <div className="text-sm text-gray-500 p-4">Results will appear here after inputs are set.</div>
    );
  }

  const strapHighlight =
    fitResult.strapLength < 0
      ? 'bad'
      : fitResult.strapLength < MIN_STRAP_LENGTH
        ? 'bad'
        : 'good';

  return (
    <div className="space-y-4 overflow-y-auto max-h-[calc(100vh-220px)] pr-1">
      {/* Fit status */}
      <div
        className={`rounded-lg p-3 flex items-start gap-2 ${
          fitResult.isValid ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'
        }`}
      >
        {fitResult.isValid ? (
          <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        )}
        <div>
          <p className={`text-sm font-semibold ${fitResult.isValid ? 'text-green-800' : 'text-amber-800'}`}>
            {fitResult.isValid ? 'Valid Fit' : 'Review Required'}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">
            Profile: {profileName}
          </p>
        </div>
      </div>

      {/* Key metrics */}
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Fit Calculations
        </h4>
        <MetricRow
          label="Collar path length"
          value={`${fitResult.collarPathLength.toFixed(1)} mm`}
        />
        <MetricRow
          label="Strap length (auto)"
          value={`${fitResult.strapLength.toFixed(1)} mm`}
          highlight={strapHighlight}
        />
        <MetricRow
          label="Electronics length"
          value={`${inputs.electronicsLength.toFixed(1)} mm`}
        />
        <MetricRow
          label="GPS / antenna length"
          value={`${inputs.gpsAntennaLength.toFixed(1)} mm`}
        />
        <MetricRow
          label="Neck circumference"
          value={`${inputs.neckCircumference.toFixed(1)} mm`}
        />
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Mechanical Metrics
        </h4>
        <MetricRow
          label="Electronics bend radius"
          value={
            inputs.electronicsBendRadius >= RIGID_STRAIGHT_BEND_RADIUS
              ? 'Straight'
              : `${inputs.electronicsBendRadius.toFixed(0)} mm`
          }
        />
        <MetricRow
          label="Max GPS curvature"
          value={fitResult.maxGpsCurvature.toFixed(4)}
        />
        <MetricRow
          label="Min GPS bend radius"
          value={
            fitResult.minGpsBendRadius === Infinity
              ? 'N/A'
              : `${fitResult.minGpsBendRadius.toFixed(1)} mm`
          }
          highlight={
            fitResult.minGpsBendRadius < inputs.gpsMinBendRadius ? 'bad' : undefined
          }
        />
        <MetricRow
          label="Strap path length (modeled)"
          value={`${fitResult.strapPathLength.toFixed(1)} mm`}
        />
        <MetricRow
          label="Strap endpoint gap"
          value={`${fitResult.strapEndpointGap.toFixed(1)} mm`}
          highlight={fitResult.strapEndpointGap > 8 ? 'bad' : undefined}
        />
        <MetricRow
          label="Max overall neck gap"
          value={`${fitResult.maxNeckGap.toFixed(1)} mm`}
          highlight={fitResult.maxNeckGap > 8 ? 'bad' : undefined}
        />
        <MetricRow
          label="Max electronics–neck gap"
          value={`${fitResult.maxElectronicsNeckGap.toFixed(1)} mm`}
          highlight={fitResult.maxElectronicsNeckGap > 5 ? 'bad' : undefined}
        />
        <MetricRow
          label="Max GPS–neck gap"
          value={`${fitResult.maxGpsNeckGap.toFixed(1)} mm`}
          highlight={fitResult.maxGpsNeckGap > 5 ? 'bad' : undefined}
        />
        <MetricRow
          label="Enclosure–GPS angle"
          value={`${fitResult.junctionAngleDeg.toFixed(1)}°`}
        />
        <MetricRow
          label="Max interference depth"
          value={`${fitResult.maxInterferenceDepth.toFixed(1)} mm`}
          highlight={fitResult.maxInterferenceDepth > 0.5 ? 'bad' : undefined}
        />
        <MetricRow
          label="GPS bending energy"
          value={fitResult.bendingEnergy.toFixed(1)}
        />
      </div>

      {/* Warnings */}
      {fitResult.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <h4 className="text-xs font-semibold text-amber-800 mb-2">Warnings</h4>
          <ul className="space-y-1">
            {fitResult.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-900 flex gap-1.5">
                <span className="text-amber-500 shrink-0">•</span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Display toggles */}
      <div className="bg-white rounded-lg border border-gray-200 p-3 space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
          Overlays
        </h4>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={showGaps}
            onChange={(e) => onShowGapsChange(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Show neck air gaps
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={showCurvature}
            onChange={(e) => onShowCurvatureChange(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Show curvature markers
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={showPressure}
            onChange={(e) => onShowPressureChange(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Show neck contact zones
        </label>
      </div>

      {/* Export */}
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={onExportSvg}
          className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors"
        >
          <Download className="h-4 w-4" />
          Export SVG
        </button>
        <button
          type="button"
          onClick={onExportReport}
          className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        >
          <FileText className="h-4 w-4" />
          Export Fit Report
        </button>
      </div>
    </div>
  );
};

export default NeckFitResults;

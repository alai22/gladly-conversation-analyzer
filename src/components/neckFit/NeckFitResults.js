import React from 'react';
import { CheckCircle, AlertTriangle, Download, FileText } from 'lucide-react';
import { MIN_STRAP_LENGTH } from '../../utils/neckFit/mechanicalModel';

const KpiCard = ({ label, value, sublabel, status }) => (
  <div
    className={`rounded-lg border p-3 ${
      status === 'bad'
        ? 'border-red-200 bg-red-50'
        : status === 'good'
          ? 'border-green-200 bg-green-50'
          : 'border-gray-200 bg-gray-50'
    }`}
  >
    <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide">{label}</p>
    <p
      className={`text-lg font-semibold tabular-nums mt-0.5 ${
        status === 'bad' ? 'text-red-800' : status === 'good' ? 'text-green-800' : 'text-gray-900'
      }`}
    >
      {value}
    </p>
    {sublabel && <p className="text-[10px] text-gray-500 mt-0.5">{sublabel}</p>}
  </div>
);

const DetailRow = ({ label, value, highlight }) => (
  <div className="flex justify-between items-baseline py-1.5 border-b border-gray-100 last:border-0">
    <span className="text-xs text-gray-600">{label}</span>
    <span
      className={`text-xs font-medium tabular-nums ${
        highlight === 'bad' ? 'text-red-700' : highlight === 'good' ? 'text-green-700' : 'text-gray-900'
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
  onExportSvg,
  onExportReport,
}) => {
  if (!fitResult) {
    return (
      <div className="text-sm text-gray-500 p-4">Results will appear here after inputs are set.</div>
    );
  }

  const strapStatus =
    fitResult.strapLength < 0 || fitResult.strapLength < MIN_STRAP_LENGTH ? 'bad' : 'good';
  const gapStatus = fitResult.maxNeckGap > 8 ? 'bad' : undefined;
  const strapEndpointStatus = fitResult.strapEndpointGap > 8 ? 'bad' : undefined;
  const bendStatus =
    fitResult.minGpsBendRadius !== Infinity &&
    fitResult.minGpsBendRadius < inputs.gpsMinBendRadius
      ? 'bad'
      : 'good';

  return (
    <div className="space-y-4">
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
          <p className="text-xs text-gray-600 mt-0.5">{profileName}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <KpiCard
          label="Contact pad violations"
          value={`${fitResult.contactPadViolations}`}
          sublabel={`${fitResult.contactPads.length} pads sampled`}
          status={fitResult.contactPadViolations > 0 ? 'bad' : 'good'}
        />
        <KpiCard
          label="Strap length"
          value={`${fitResult.strapLength.toFixed(0)} mm`}
          sublabel="Auto-calculated"
          status={strapStatus}
        />
        <KpiCard
          label="Max lift-off gap"
          value={`${fitResult.maxNeckGap.toFixed(1)} mm`}
          sublabel="Hardware vs seating path"
          status={gapStatus}
        />
        <KpiCard
          label="Strap endpoint gap"
          value={`${fitResult.strapEndpointGap.toFixed(1)} mm`}
          sublabel="GPS exit span"
          status={strapEndpointStatus}
        />
        <KpiCard
          label="Min GPS bend"
          value={
            fitResult.minGpsBendRadius === Infinity
              ? 'N/A'
              : `${fitResult.minGpsBendRadius.toFixed(1)} mm`
          }
          sublabel={`Limit ${inputs.gpsMinBendRadius} mm`}
          status={bendStatus}
        />
      </div>

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

      <details className="rounded-lg border border-gray-200 bg-white">
        <summary className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none">
          Engineering details
        </summary>
        <div className="px-3 pb-3">
          <DetailRow label="Collar path length" value={`${fitResult.collarPathLength.toFixed(1)} mm`} />
          <DetailRow label="Strap path length (modeled)" value={`${fitResult.strapPathLength.toFixed(1)} mm`} />
          <DetailRow
            label="Max electronics lift-off"
            value={`${fitResult.maxElectronicsNeckGap.toFixed(1)} mm`}
            highlight={fitResult.maxElectronicsNeckGap > 5 ? 'bad' : undefined}
          />
          <DetailRow
            label="Max GPS lift-off"
            value={`${fitResult.maxGpsNeckGap.toFixed(1)} mm`}
            highlight={fitResult.maxGpsNeckGap > 5 ? 'bad' : undefined}
          />
          <DetailRow
            label="Hardware settle inset"
            value={`${fitResult.hardwareSettleInsetMm.toFixed(1)} mm`}
            highlight={fitResult.hardwareSettleInsetMm <= 0 ? 'bad' : undefined}
          />
          <DetailRow
            label="Body rotation vs neck"
            value={`${(inputs.electronicsBodyRotationDeg ?? 0).toFixed(0)}°`}
          />
          <DetailRow label="Enclosure–GPS angle" value={`${fitResult.junctionAngleDeg.toFixed(1)}°`} />
          <DetailRow
            label="Max interference depth"
            value={`${fitResult.maxInterferenceDepth.toFixed(1)} mm`}
            highlight={fitResult.maxInterferenceDepth > 0.5 ? 'bad' : undefined}
          />
          <DetailRow label="Max GPS curvature" value={fitResult.maxGpsCurvature.toFixed(4)} />
          <DetailRow label="GPS bending energy" value={fitResult.bendingEnergy.toFixed(1)} />
        </div>
      </details>

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

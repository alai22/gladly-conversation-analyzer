import React, { useRef, useState } from 'react';
import { Upload, ImageIcon, RotateCw } from 'lucide-react';
import { SAMPLE_PROFILES } from '../../utils/neckFit/sampleProfiles';

const TABS = [
  { id: 'neck', label: 'Neck', hint: 'Profile shape and clearance from skin' },
  { id: 'hardware', label: 'Hardware', hint: 'Rigid enclosure + semi-flex GPS' },
  { id: 'strap', label: 'Strap', hint: 'Flexible strap that closes the loop' },
];

const HARDWARE_SECTIONS = [
  { id: 'electronics', label: 'Electronics' },
  { id: 'gps', label: 'GPS' },
];

const SliderInput = ({ label, value, onChange, min, max, step, unit, hint }) => (
  <div className="space-y-1">
    <div className="flex justify-between items-baseline">
      <label className="text-xs font-medium text-gray-700">{label}</label>
      <span className="text-xs text-gray-500 tabular-nums">
        {typeof value === 'number' ? value.toFixed(step < 1 ? 1 : 0) : value}
        {unit ? ` ${unit}` : ''}
      </span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
    />
    {hint && <p className="text-[10px] text-gray-400">{hint}</p>}
  </div>
);

const NumberInput = ({ label, value, onChange, min, max, step, unit }) => (
  <div className="space-y-1">
    <label className="text-xs font-medium text-gray-700">{label}</label>
    <div className="flex items-center gap-1">
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
      />
      {unit && <span className="text-xs text-gray-500 shrink-0">{unit}</span>}
    </div>
  </div>
);

const AutoFitPanel = ({ onOptimizePlacement, optimizeMessage }) => {
  if (!onOptimizePlacement) return null;
  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50/80 p-3 space-y-2">
      <button
        type="button"
        onClick={onOptimizePlacement}
        className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors shadow-sm"
      >
        <RotateCw className="h-4 w-4" />
        Re-run auto-fit
      </button>
      {optimizeMessage && (
        <p className="text-[10px] text-indigo-800 leading-snug">{optimizeMessage}</p>
      )}
      <p className="text-[10px] text-indigo-600/80 leading-snug">
        Optimizes placement and body rotation. Runs on load; re-run after changing dimensions or neck settings.
      </p>
    </div>
  );
};

const NeckFitControls = ({
  profileId,
  onProfileChange,
  customProfile,
  onImageUpload,
  imageLoading,
  imageError,
  inputs,
  onInputChange,
  smoothing,
  onSmoothingChange,
  onOptimizePlacement,
  optimizeMessage,
  activeTab,
  onActiveTabChange,
}) => {
  const fileRef = useRef(null);
  const [hardwareSection, setHardwareSection] = useState('electronics');
  const set = (key) => (val) => onInputChange({ ...inputs, [key]: val });
  const tabHint = TABS.find((t) => t.id === activeTab)?.hint ?? '';

  return (
    <div className="space-y-3">
      <div className="flex rounded-lg border border-gray-200 p-0.5 bg-gray-50">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onActiveTabChange(tab.id)}
            className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabHint && <p className="text-[10px] text-gray-500 leading-snug">{tabHint}</p>}

      <AutoFitPanel
        onOptimizePlacement={onOptimizePlacement}
        optimizeMessage={optimizeMessage}
      />

      <div className="space-y-4">
        {activeTab === 'neck' && (
          <>
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-700">Built-in profile</label>
              <select
                value={profileId}
                onChange={(e) => onProfileChange(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-indigo-500"
              >
                {SAMPLE_PROFILES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
                {customProfile && (
                  <option value={customProfile.id}>{customProfile.name} (uploaded)</option>
                )}
              </select>
            </div>

            <div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onImageUpload(file);
                  e.target.value = '';
                }}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={imageLoading}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm border border-dashed border-gray-300 rounded-md hover:border-indigo-400 hover:bg-indigo-50 transition-colors disabled:opacity-50"
              >
                {imageLoading ? (
                  <span className="text-gray-500">Processing image…</span>
                ) : (
                  <>
                    <Upload className="h-4 w-4 text-gray-500" />
                    <span>Upload neck cross-section</span>
                  </>
                )}
              </button>
              {imageError && <p className="text-xs text-red-600 mt-1">{imageError}</p>}
              {customProfile && profileId === customProfile.id && (
                <p className="text-[10px] text-gray-400 mt-1 flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" />
                  Image-derived contour active
                </p>
              )}
            </div>

            <SliderInput
              label="Neck circumference"
              value={inputs.neckCircumference}
              onChange={set('neckCircumference')}
              min={200}
              max={600}
              step={1}
              unit="mm"
            />
            <SliderInput
              label="Profile smoothing"
              value={smoothing}
              onChange={onSmoothingChange}
              min={0}
              max={1}
              step={0.05}
              hint="Higher = smoother outline"
            />
            <SliderInput
              label="Collar clearance offset"
              value={inputs.clearanceOffset}
              onChange={set('clearanceOffset')}
              min={2}
              max={25}
              step={0.5}
              unit="mm"
              hint="Distance from neck skin to target seating path"
            />
          </>
        )}

        {activeTab === 'hardware' && (
          <>
            <div className="flex rounded-md border border-gray-200 p-0.5 bg-gray-50">
              {HARDWARE_SECTIONS.map((section) => (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => setHardwareSection(section.id)}
                  className={`flex-1 px-2 py-1 text-[11px] font-medium rounded transition-colors ${
                    hardwareSection === section.id
                      ? 'bg-white text-indigo-700 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {section.label}
                </button>
              ))}
            </div>

            {hardwareSection === 'electronics' && (
              <>
                <p className="text-[10px] text-gray-500 leading-snug">
                  Rigid enclosure — length, bend, and placement on the neck.
                </p>
                <SliderInput
                  label="Length"
                  value={inputs.electronicsLength}
                  onChange={set('electronicsLength')}
                  min={30}
                  max={150}
                  step={1}
                  unit="mm"
                />
                <SliderInput
                  label="Fixed bend radius"
                  value={inputs.electronicsBendRadius}
                  onChange={set('electronicsBendRadius')}
                  min={20}
                  max={120}
                  step={10}
                  unit="mm"
                  hint="Higher = straighter arc, length stays fixed"
                />
                <SliderInput
                  label="Thickness"
                  value={inputs.electronicsThickness}
                  onChange={set('electronicsThickness')}
                  min={4}
                  max={25}
                  step={0.5}
                  unit="mm"
                />
                <SliderInput
                  label="Body rotation vs neck"
                  value={inputs.electronicsBodyRotationDeg}
                  onChange={set('electronicsBodyRotationDeg')}
                  min={-35}
                  max={35}
                  step={1}
                  unit="°"
                  hint="Rigid body angle relative to neck tangent at anchor"
                />
                <SliderInput
                  label="Rotation from trachea"
                  value={inputs.electronicsPlacementS}
                  onChange={set('electronicsPlacementS')}
                  min={-200}
                  max={200}
                  step={1}
                  unit="mm"
                  hint="Clockwise (+) or counter-clockwise (−); 0 = strap end at throat"
                />
              </>
            )}

            {hardwareSection === 'gps' && (
              <>
                <p className="text-[10px] text-gray-500 leading-snug">
                  Semi-flexible GPS/antenna segment attached to the electronics exit.
                </p>
                <SliderInput
                  label="Length"
                  value={inputs.gpsAntennaLength}
                  onChange={set('gpsAntennaLength')}
                  min={20}
                  max={120}
                  step={1}
                  unit="mm"
                />
                <SliderInput
                  label="Thickness"
                  value={inputs.gpsAntennaThickness}
                  onChange={set('gpsAntennaThickness')}
                  min={3}
                  max={20}
                  step={0.5}
                  unit="mm"
                />
                <SliderInput
                  label="Stiffness"
                  value={inputs.gpsAntennaStiffness}
                  onChange={set('gpsAntennaStiffness')}
                  min={0}
                  max={1}
                  step={0.05}
                  hint="0 = fully flexible, 1 = rigid"
                />

                <details className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
                  <summary className="text-xs font-medium text-gray-600 cursor-pointer select-none">
                    Advanced
                  </summary>
                  <div className="space-y-3 mt-3 pt-2 border-t border-gray-200">
                    <SliderInput
                      label="Young's modulus (relative)"
                      value={inputs.gpsAntennaYoungsModulus}
                      onChange={set('gpsAntennaYoungsModulus')}
                      min={0.5}
                      max={10}
                      step={0.1}
                    />
                    <NumberInput
                      label="Minimum bend radius"
                      value={inputs.gpsMinBendRadius}
                      onChange={set('gpsMinBendRadius')}
                      min={5}
                      max={50}
                      step={1}
                      unit="mm"
                    />
                  </div>
                </details>
              </>
            )}
          </>
        )}

        {activeTab === 'strap' && (
          <>
            <SliderInput
              label="Thickness"
              value={inputs.strapThickness}
              onChange={set('strapThickness')}
              min={2}
              max={12}
              step={0.5}
              unit="mm"
            />
            <SliderInput
              label="Slack"
              value={inputs.slack}
              onChange={set('slack')}
              min={0}
              max={30}
              step={0.5}
              unit="mm"
              hint="Extra loop length beyond tight fit"
            />
          </>
        )}
      </div>
    </div>
  );
};

export default NeckFitControls;

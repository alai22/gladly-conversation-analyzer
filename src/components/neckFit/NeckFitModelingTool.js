import React, { useState, useMemo, useCallback } from 'react';
import { CircleDot } from 'lucide-react';
import NeckFitControls from './NeckFitControls';
import NeckFitVisualization from './NeckFitVisualization';
import NeckFitResults from './NeckFitResults';
import {
  DEFAULT_FIT_INPUTS,
  computeFit,
  generateFitReport,
} from '../../utils/neckFit/mechanicalModel';
import {
  DEFAULT_SAMPLE_PROFILE_ID,
  getSampleProfileById,
} from '../../utils/neckFit/sampleProfiles';
import { extractContourFromImage } from '../../utils/neckFit/imageContour';
import { buildExportSvg, downloadFile } from '../../utils/neckFit/export';

const NeckFitModelingTool = () => {
  const [profileId, setProfileId] = useState(DEFAULT_SAMPLE_PROFILE_ID);
  const [customProfile, setCustomProfile] = useState(null);
  const [inputs, setInputs] = useState({ ...DEFAULT_FIT_INPUTS });
  const [smoothing, setSmoothing] = useState(0.15);
  const [showGaps, setShowGaps] = useState(true);
  const [showCurvature, setShowCurvature] = useState(false);
  const [showPressure, setShowPressure] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(null);

  const activeProfile = useMemo(() => {
    if (customProfile && profileId === customProfile.id) return customProfile;
    return getSampleProfileById(profileId) || getSampleProfileById(DEFAULT_SAMPLE_PROFILE_ID);
  }, [profileId, customProfile]);

  const fitResult = useMemo(() => {
    if (!activeProfile?.points?.length) return null;
    return computeFit(activeProfile.points, inputs, { smoothing });
  }, [activeProfile, inputs, smoothing]);

  const handleImageUpload = useCallback(async (file) => {
    setImageLoading(true);
    setImageError(null);
    try {
      const profile = await extractContourFromImage(file, { smoothing });
      setCustomProfile(profile);
      setProfileId(profile.id);
    } catch (err) {
      setImageError(err.message || 'Failed to process image');
    } finally {
      setImageLoading(false);
    }
  }, [smoothing]);

  const handleExportSvg = useCallback(() => {
    if (!fitResult) return;
    const svg = buildExportSvg({
      neckPoints: fitResult.neckPoints,
      collarOffsetPoints: fitResult.collarOffsetPoints,
      segments: fitResult.segments,
      gapIndicators: fitResult.gapIndicators,
      pressurePoints: fitResult.pressurePoints,
      showGaps,
      showPressure,
    });
    downloadFile(svg, `halo-collar-6-neck-fit-${Date.now()}.svg`, 'image/svg+xml');
  }, [fitResult, showGaps, showPressure]);

  const handleExportReport = useCallback(() => {
    if (!fitResult) return;
    const report = generateFitReport(fitResult, inputs, activeProfile?.name || 'Unknown');
    downloadFile(report, `halo-collar-6-fit-report-${Date.now()}.txt`, 'text/plain');
  }, [fitResult, inputs, activeProfile]);

  return (
    <div className="min-h-full bg-gray-50">
      <div className="border-b border-gray-200 bg-white px-4 sm:px-6 py-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg shrink-0">
            <CircleDot className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Halo Collar 6 — Neck Fit Modeler</h1>
            <p className="text-sm text-gray-600 mt-0.5">
              Interactive cross-section modeling for electronics, GPS/antenna, and strap fit around dog neck profiles.
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 max-w-[1600px] mx-auto">
          {/* Left: Inputs */}
          <div className="lg:col-span-3 bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-800 mb-4">Inputs</h2>
            <NeckFitControls
              profileId={profileId}
              onProfileChange={setProfileId}
              customProfile={customProfile}
              onImageUpload={handleImageUpload}
              imageLoading={imageLoading}
              imageError={imageError}
              inputs={inputs}
              onInputChange={setInputs}
              smoothing={smoothing}
              onSmoothingChange={setSmoothing}
            />
          </div>

          {/* Center: Visualization */}
          <div className="lg:col-span-6 min-h-[480px]">
            <NeckFitVisualization
              fitResult={fitResult}
              showGaps={showGaps}
              showCurvature={showCurvature}
              showPressure={showPressure}
            />
          </div>

          {/* Right: Results */}
          <div className="lg:col-span-3 bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-800 mb-4">Results</h2>
            <NeckFitResults
              fitResult={fitResult}
              inputs={inputs}
              profileName={activeProfile?.name || ''}
              showGaps={showGaps}
              onShowGapsChange={setShowGaps}
              showCurvature={showCurvature}
              onShowCurvatureChange={setShowCurvature}
              showPressure={showPressure}
              onShowPressureChange={setShowPressure}
              onExportSvg={handleExportSvg}
              onExportReport={handleExportReport}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default NeckFitModelingTool;

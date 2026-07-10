import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { surveyPublicUrl } from '../../utils/haloSurveyApi';

export default function BrazeUrlPanel({ survey, onTemplateChange }) {
  const [copied, setCopied] = useState(false);

  const defaultTemplate =
    survey?.braze_url_template ||
    `${surveyPublicUrl(survey?.slug || 'your-slug')}?external_id={{${'${user_id}'}}}&utm_source=braze&utm_campaign=your_campaign`;

  const template = survey?.braze_url_template || defaultTemplate;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(template);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="border border-halo-blue/30 rounded-lg bg-halo-blue-light p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-halo-black">Braze campaign URL</h4>
        <a
          href={surveyPublicUrl(survey?.slug)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-halo-blue hover:underline"
        >
          Preview <ExternalLink className="h-3 w-3" />
        </a>
      </div>
      <p className="text-xs text-gray-600 mb-2">
        Copy this URL into Braze. Query params are saved with each response for attribution.
      </p>
      <div className="flex gap-2">
        <input
          type="text"
          readOnly={!onTemplateChange}
          value={template}
          onChange={(e) => onTemplateChange?.(e.target.value)}
          className="flex-1 text-xs font-mono px-3 py-2 border border-gray-300 rounded-lg bg-white"
        />
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm bg-halo-yellow text-halo-black rounded-lg hover:bg-halo-yellow-dark"
        >
          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-2">
        Public link: <code className="text-halo-blue">{surveyPublicUrl(survey?.slug)}</code>
      </p>
    </div>
  );
}

import React, { useMemo, useState } from 'react';
import QuestionRenderer from './QuestionRenderer';
import {
  evaluateEndState,
  getVisibleSections,
  isQuestionAnswered,
  sectionProgress,
  setAnswerValue,
} from '../../utils/surveyLogic';

export default function SurveyPreview({ survey, interactive = true, onComplete }) {
  const [answers, setAnswers] = useState({});
  const [sectionIndex, setSectionIndex] = useState(0);
  const [finalized, setFinalized] = useState(null);

  const visibleSections = useMemo(
    () => getVisibleSections(survey, answers),
    [survey, answers]
  );

  const currentSection = visibleSections[sectionIndex];
  const progress = sectionProgress(survey, answers);

  const handleChange = (question, value) => {
    const next = setAnswerValue(question, answers, value);
    setAnswers(next);
    const end = evaluateEndState(survey, next);
    if (end) {
      setFinalized(end);
      if (onComplete) onComplete({ status: end.status, endMessage: end.message, answers: next });
    }
  };

  const getValue = (question) => {
    if (question.type === 'rating_with_text') {
      return {
        rating: answers[`${question.id}__rating`],
        text: answers[`${question.id}__text`],
      };
    }
    return answers[question.id];
  };

  const handleChangeWrapper = (question, value) => {
    if (question.type === 'rating_with_text') {
      const next = { ...answers };
      if (value?.rating != null) next[`${question.id}__rating`] = value.rating;
      if (value?.text != null) next[`${question.id}__text`] = value.text;
      handleChange(question, value);
      setAnswers(next);
      return;
    }
    handleChange(question, value);
  };

  if (!survey) {
    return <div className="text-gray-500 text-sm p-4">No survey to preview</div>;
  }

  if (finalized) {
    return (
      <div className="p-6 text-center">
        <div className="inline-block p-4 rounded-lg bg-halo-yellow-light border border-halo-yellow">
          <p className="text-halo-black font-medium">{finalized.message || 'Survey ended.'}</p>
        </div>
      </div>
    );
  }

  if (sectionIndex >= visibleSections.length && visibleSections.length > 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-halo-black font-medium">Preview complete — all sections shown.</p>
        <button
          type="button"
          onClick={() => {
            setSectionIndex(0);
            setAnswers({});
            setFinalized(null);
          }}
          className="mt-3 text-sm text-halo-blue hover:underline"
        >
          Reset preview
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>
            Section {sectionIndex + 1} of {visibleSections.length}
          </span>
          <span>{progress.answered} / {progress.total} answered</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-halo-yellow transition-all"
            style={{
              width: `${visibleSections.length ? ((sectionIndex + 1) / visibleSections.length) * 100 : 0}%`,
            }}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {currentSection && (
          <>
            <h3 className="text-lg font-semibold text-halo-black mb-4">{currentSection.title}</h3>
            {currentSection.questions.map((q) => (
              <QuestionRenderer
                key={q.id}
                question={q}
                value={getValue(q)}
                onChange={(v) => handleChangeWrapper(q, v)}
                disabled={!interactive}
              />
            ))}
          </>
        )}
      </div>

      {interactive && currentSection && (
        <div className="p-4 border-t border-gray-100 flex justify-between gap-2">
          <button
            type="button"
            disabled={sectionIndex === 0}
            onClick={() => setSectionIndex((i) => Math.max(0, i - 1))}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="button"
            onClick={() => {
              const missing = currentSection.questions.filter(
                (q) => q.required && !isQuestionAnswered(q, answers)
              );
              if (missing.length) return;
              if (sectionIndex + 1 >= visibleSections.length) {
                setSectionIndex(visibleSections.length);
                if (onComplete) onComplete({ status: 'complete', answers });
              } else {
                setSectionIndex((i) => i + 1);
              }
            }}
            className="px-4 py-2 text-sm bg-halo-yellow text-halo-black font-medium rounded-lg hover:bg-halo-yellow-dark"
          >
            {sectionIndex + 1 >= visibleSections.length ? 'Finish' : 'Next'}
          </button>
        </div>
      )}
    </div>
  );
}

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { Loader2, ChevronLeft, ChevronRight, CheckCircle } from 'lucide-react';
import QuestionRenderer from './QuestionRenderer';
import {
  captureBrazeMetadata,
  fetchPublicSurvey,
  patchSurveyResponse,
  startSurveyResponse,
} from '../../utils/haloSurveyApi';
import {
  evaluateEndState,
  getVisibleSections,
  isQuestionAnswered,
  sectionProgress,
} from '../../utils/surveyLogic';

const STORAGE_PREFIX = 'halo_survey_response_';

export default function SurveyParticipantPage() {
  const location = useLocation();
  const slug = location.pathname.match(/^\/s\/([^/]+)/)?.[1];
  const [searchParams] = useSearchParams();
  const [survey, setSurvey] = useState(null);
  const [responseId, setResponseId] = useState(null);
  const [answers, setAnswers] = useState({});
  const [sectionIndex, setSectionIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [finalized, setFinalized] = useState(null);

  const visibleSections = useMemo(
    () => (survey ? getVisibleSections(survey, answers) : []),
    [survey, answers]
  );
  const currentSection = visibleSections[sectionIndex];
  const progress = survey ? sectionProgress(survey, answers) : { total: 0, answered: 0 };

  const init = useCallback(async () => {
    if (!slug) {
      setError('Invalid survey link.');
      setLoading(false);
      return;
    }
    try {
      const data = await fetchPublicSurvey(slug);
      if (!data.success) {
        setError(data.error || 'Survey not found');
        setLoading(false);
        return;
      }
      setSurvey(data.survey);

      const storageKey = `${STORAGE_PREFIX}${slug}`;
      const savedId = localStorage.getItem(storageKey);
      const meta = captureBrazeMetadata(searchParams);

      if (savedId) {
        setResponseId(savedId);
      } else {
        const start = await startSurveyResponse(slug, meta);
        if (start.success) {
          setResponseId(start.response_id);
          localStorage.setItem(storageKey, start.response_id);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [slug, searchParams]);

  useEffect(() => {
    init();
  }, [init]);

  const getValue = (question) => {
    if (question.type === 'rating_with_text') {
      return {
        rating: answers[`${question.id}__rating`],
        text: answers[`${question.id}__text`],
      };
    }
    return answers[question.id];
  };

  const buildAnswersPayload = (nextAnswers) => {
    const payload = { ...nextAnswers };
    return payload;
  };

  const handleChange = async (question, value) => {
    let next = { ...answers };
    if (question.type === 'rating_with_text') {
      if (value?.rating != null) next[`${question.id}__rating`] = value.rating;
      if (value?.text != null) next[`${question.id}__text`] = value.text;
    } else {
      next[question.id] = value;
    }
    setAnswers(next);

    const end = evaluateEndState(survey, next);
    if (end && responseId) {
      setSubmitting(true);
      try {
        const res = await patchSurveyResponse(slug, responseId, buildAnswersPayload(next), false);
        if (res.success && res.finalized) {
          setFinalized({ message: res.end_message || end.message, status: res.status });
          localStorage.removeItem(`${STORAGE_PREFIX}${slug}`);
        }
      } catch (err) {
        setError(err.response?.data?.error || err.message);
      } finally {
        setSubmitting(false);
      }
    }
  };

  const handleNext = async () => {
    if (!currentSection || !responseId) return;
    const missing = currentSection.questions.filter(
      (q) => q.required && !isQuestionAnswered(q, answers)
    );
    if (missing.length) {
      setError(`Please answer all required questions (${missing.length} remaining).`);
      return;
    }
    setError(null);

    const isLast = sectionIndex + 1 >= visibleSections.length;
    setSubmitting(true);
    try {
      const res = await patchSurveyResponse(
        slug,
        responseId,
        buildAnswersPayload(answers),
        isLast
      );
      if (res.success) {
        if (res.finalized) {
          setFinalized({
            message: res.end_message || (isLast ? 'Thank you for your feedback!' : ''),
            status: res.status,
            complete: res.status === 'complete',
          });
          localStorage.removeItem(`${STORAGE_PREFIX}${slug}`);
        } else if (!isLast) {
          setSectionIndex((i) => i + 1);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBack = () => {
    setSectionIndex((i) => Math.max(0, i - 1));
    setError(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-halo-yellow" />
      </div>
    );
  }

  if (error && !survey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md text-center">
          <p className="text-red-600 font-medium">{error}</p>
          <p className="text-sm text-gray-500 mt-2">This survey may not be published yet.</p>
        </div>
      </div>
    );
  }

  if (finalized) {
    const isIneligible = finalized.status === 'ineligible';
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b-4 border-halo-yellow px-4 py-4 shadow-sm">
          <h1 className="text-lg font-semibold text-halo-black text-center">Halo Collar Survey</h1>
        </header>
        <div className="max-w-lg mx-auto p-6 mt-8 text-center">
          {finalized.complete && !isIneligible ? (
            <CheckCircle className="h-12 w-12 text-halo-blue mx-auto mb-4" />
          ) : null}
          <p className="text-halo-black font-medium text-lg">
            {finalized.message || (isIneligible ? 'Survey ended.' : 'Thank you for your feedback!')}
          </p>
          {!isIneligible && finalized.complete && (
            <p className="text-sm text-gray-500 mt-2">Your responses help us improve Halo Collar.</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b-4 border-halo-yellow px-4 py-4 shadow-sm">
        <h1 className="text-lg font-semibold text-halo-black">{survey.title}</h1>
        {survey.description && (
          <p className="text-sm text-gray-600 mt-1">{survey.description}</p>
        )}
        {survey.audience && (
          <p className="text-xs text-gray-400 mt-1">Audience: {survey.audience}</p>
        )}
      </header>

      <div className="px-4 py-3 bg-white border-b border-gray-100">
        <div className="max-w-2xl mx-auto">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>
              Section {sectionIndex + 1} of {visibleSections.length}
            </span>
            <span>{progress.answered} / {progress.total} answered</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-halo-yellow transition-all duration-300"
              style={{
                width: `${visibleSections.length ? ((sectionIndex + 1) / visibleSections.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      </div>

      <main className="flex-1 max-w-2xl w-full mx-auto p-4 pb-24">
        {currentSection && (
          <>
            <h2 className="text-xl font-semibold text-halo-black mb-6">{currentSection.title}</h2>
            {currentSection.questions.map((q) => (
              <QuestionRenderer
                key={q.id}
                question={q}
                value={getValue(q)}
                onChange={(v) => handleChange(q, v)}
                disabled={submitting}
              />
            ))}
          </>
        )}
        {error && survey && (
          <p className="text-red-600 text-sm mt-2">{error}</p>
        )}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
        <div className="max-w-2xl mx-auto flex justify-between gap-3">
          <button
            type="button"
            onClick={handleBack}
            disabled={sectionIndex === 0 || submitting}
            className="inline-flex items-center gap-1 px-4 py-2.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" /> Back
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={submitting}
            className="inline-flex items-center gap-1 px-6 py-2.5 text-sm bg-halo-yellow text-halo-black font-semibold rounded-lg hover:bg-halo-yellow-dark disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : sectionIndex + 1 >= visibleSections.length ? (
              'Submit'
            ) : (
              <>
                Next <ChevronRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </footer>
    </div>
  );
}

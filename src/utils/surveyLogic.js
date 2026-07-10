/**
 * Client-side survey conditional logic — mirrors backend halo_survey_logic.py
 */

export function evaluateCondition(condition, answers) {
  if (!condition || !condition.question_id) return true;

  const answer = answers[condition.question_id];
  const op = (condition.operator || 'equals').toLowerCase();
  const expected = condition.value;

  if (op === 'equals') return answer === expected;
  if (op === 'not_equals') return answer !== expected;
  if (op === 'in') {
    const list = Array.isArray(expected) ? expected : [expected];
    if (Array.isArray(answer)) return answer.some((a) => list.includes(a));
    return list.includes(answer);
  }
  if (op === 'not_in') {
    const list = Array.isArray(expected) ? expected : [expected];
    if (Array.isArray(answer)) return !answer.some((a) => list.includes(a));
    return !list.includes(answer);
  }
  if (op === 'contains') {
    if (Array.isArray(answer)) {
      const list = Array.isArray(expected) ? expected : [expected];
      return list.some((e) => answer.includes(e));
    }
    if (typeof answer === 'string' && expected != null) return answer.includes(String(expected));
    return false;
  }
  if (op === 'not_contains') {
    return !evaluateCondition(
      { question_id: condition.question_id, operator: 'contains', value: expected },
      answers
    );
  }
  if (op === 'answered') {
    if (answer == null) return false;
    if (typeof answer === 'string') return answer.trim() !== '';
    if (Array.isArray(answer)) return answer.length > 0;
    if (typeof answer === 'object') return Object.keys(answer).length > 0;
    return true;
  }
  return true;
}

export function isQuestionVisible(question, answers) {
  return evaluateCondition(question.show_if, answers);
}

export function checkEndCondition(question, answers) {
  if (!question.end_if) return null;
  if (evaluateCondition(question.end_if, answers)) return question.end_if;
  return null;
}

export function getVisibleSections(survey, answers) {
  if (!survey?.sections) return [];
  return survey.sections
    .map((section) => ({
      ...section,
      questions: (section.questions || []).filter((q) => isQuestionVisible(q, answers)),
    }))
    .filter((section) => section.questions.length > 0);
}

export function evaluateEndState(survey, answers) {
  for (const section of survey.sections || []) {
    for (const question of section.questions || []) {
      const hasAnswer =
        answers[question.id] != null ||
        answers[`${question.id}__rating`] != null;
      if (!hasAnswer) continue;
      const end = checkEndCondition(question, answers);
      if (end) {
        return {
          message: end.message,
          status: end.status || 'ineligible',
          questionId: question.id,
        };
      }
    }
  }
  return null;
}

export function getAnswerValue(question, answers) {
  if (question.type === 'rating_with_text') {
    return {
      rating: answers[`${question.id}__rating`],
      text: answers[`${question.id}__text`],
    };
  }
  return answers[question.id];
}

export function setAnswerValue(question, answers, value) {
  const next = { ...answers };
  if (question.type === 'rating_with_text') {
    if (typeof value === 'object' && value != null) {
      if ('rating' in value) next[`${question.id}__rating`] = value.rating;
      if ('text' in value) next[`${question.id}__text`] = value.text;
    }
  } else {
    next[question.id] = value;
  }
  return next;
}

export function isQuestionAnswered(question, answers) {
  if (!question.required) return true;
  if (question.type === 'rating_with_text') {
    return answers[`${question.id}__rating`] != null;
  }
  const val = answers[question.id];
  if (val == null || val === '') return false;
  if (Array.isArray(val) && val.length === 0) return false;
  return true;
}

export function sectionProgress(survey, answers) {
  const visible = getVisibleSections(survey, answers);
  const total = visible.reduce((n, s) => n + s.questions.length, 0);
  let answered = 0;
  visible.forEach((section) => {
    section.questions.forEach((q) => {
      if (isQuestionAnswered(q, answers)) answered += 1;
    });
  });
  return { total, answered, sections: visible.length };
}

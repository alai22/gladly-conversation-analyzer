"""
Survey conditional logic engine — shared evaluation for show_if / end_if rules.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..models.halo_survey import (
    Condition,
    EndCondition,
    HaloSurvey,
    ResponseStatus,
    SurveyQuestion,
    SurveySection,
)


def _normalize_answer(answer: Any) -> Any:
    if answer is None:
        return None
    if isinstance(answer, list):
        return answer
    return answer


def evaluate_condition(condition: Optional[Condition], answers: Dict[str, Any]) -> bool:
    """Return True if condition is satisfied (question should show / rule applies)."""
    if not condition or not condition.question_id:
        return True

    answer = _normalize_answer(answers.get(condition.question_id))
    op = (condition.operator or "equals").lower()
    expected = condition.value

    if op == "equals":
        return answer == expected
    if op == "not_equals":
        return answer != expected
    if op == "in":
        if not isinstance(expected, list):
            expected = [expected]
        if isinstance(answer, list):
            return any(a in expected for a in answer)
        return answer in expected
    if op == "not_in":
        if not isinstance(expected, list):
            expected = [expected]
        if isinstance(answer, list):
            return not any(a in expected for a in answer)
        return answer not in expected
    if op == "contains":
        if isinstance(answer, list):
            if isinstance(expected, list):
                return any(e in answer for e in expected)
            return expected in answer
        if isinstance(answer, str) and expected is not None:
            return str(expected) in answer
        return False
    if op == "not_contains":
        return not evaluate_condition(
            Condition(question_id=condition.question_id, operator="contains", value=expected),
            answers,
        )
    if op == "answered":
        if answer is None:
            return False
        if isinstance(answer, str):
            return answer.strip() != ""
        if isinstance(answer, list):
            return len(answer) > 0
        if isinstance(answer, dict):
            return bool(answer)
        return True
    return True


def is_question_visible(question: SurveyQuestion, answers: Dict[str, Any]) -> bool:
    return evaluate_condition(question.show_if, answers)


def check_end_condition(question: SurveyQuestion, answers: Dict[str, Any]) -> Optional[EndCondition]:
    if not question.end_if:
        return None
    if evaluate_condition(question.end_if, answers):
        return question.end_if
    return None


def get_visible_questions(survey: HaloSurvey, answers: Dict[str, Any]) -> List[SurveyQuestion]:
    visible: List[SurveyQuestion] = []
    for section in survey.sections:
        for question in section.questions:
            if is_question_visible(question, answers):
                visible.append(question)
    return visible


def get_visible_sections(survey: HaloSurvey, answers: Dict[str, Any]) -> List[SurveySection]:
    result: List[SurveySection] = []
    for section in survey.sections:
        visible_qs = [q for q in section.questions if is_question_visible(q, answers)]
        if visible_qs:
            result.append(SurveySection(id=section.id, title=section.title, questions=visible_qs))
    return result


def evaluate_end_state(
    survey: HaloSurvey, answers: Dict[str, Any]
) -> Tuple[Optional[str], Optional[ResponseStatus], Optional[str]]:
    """
    Check all answered questions for end_if triggers.
    Returns (end_message, status, triggering_question_id) or (None, None, None).
    """
    for question in survey.all_questions():
        if question.id not in answers and question.id not in _compound_answer_keys(answers, question.id):
            continue
        end = check_end_condition(question, answers)
        if end:
            status_str = end.status or "ineligible"
            try:
                status = ResponseStatus(status_str)
            except ValueError:
                status = ResponseStatus.INELIGIBLE
            return end.message, status, question.id
    return None, None, None


def _compound_answer_keys(answers: Dict[str, Any], question_id: str) -> List[str]:
    return [k for k in answers if k.startswith(f"{question_id}__")]


def validate_required_answers(
    survey: HaloSurvey, answers: Dict[str, Any]
) -> List[str]:
    """Return list of missing required question ids."""
    missing: List[str] = []
    for question in get_visible_questions(survey, answers):
        if not question.required:
            continue
        if question.type.value == "rating_with_text":
            rating_key = f"{question.id}__rating"
            if answers.get(rating_key) is None and answers.get(question.id) is None:
                missing.append(question.id)
            continue
        val = answers.get(question.id)
        if val is None or val == "" or (isinstance(val, list) and len(val) == 0):
            missing.append(question.id)
    return missing


def flatten_questions_for_export(survey: HaloSurvey) -> List[Dict[str, Any]]:
    """Flat question list for CSV headers."""
    rows: List[Dict[str, Any]] = []
    for section in survey.sections:
        for q in section.questions:
            if q.type.value == "rating_with_text":
                rows.append({"id": f"{q.id}__rating", "text": f"{q.text} (rating)", "section": section.title})
                rows.append({"id": f"{q.id}__text", "text": f"{q.text} (text)", "section": section.title})
            else:
                rows.append({"id": q.id, "text": q.text, "section": section.title})
    return rows

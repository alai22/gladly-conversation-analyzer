"""
AI survey response analyzer — aggregates stats and generates insights.
"""

import json
from collections import Counter
from typing import Any, Dict, List, Optional

from ..models.halo_survey import HaloSurvey, SurveyResponse, SurveyStatus
from ..services.halo_survey_logic import flatten_questions_for_export
from ..services.halo_survey_prompts import ANALYZER_SYSTEM_PROMPT
from ..utils.logging import get_logger

logger = get_logger("halo_survey_analyzer")


def _format_answer(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return "; ".join(str(v) for v in val)
    if isinstance(val, dict):
        return json.dumps(val)
    return str(val)


class HaloSurveyAnalyzer:
    def __init__(self, claude_service=None):
        self.claude_service = claude_service

    def aggregate_stats(
        self, survey: HaloSurvey, responses: List[SurveyResponse]
    ) -> Dict[str, Any]:
        complete = [r for r in responses if r.status.value == "complete"]
        ineligible = [r for r in responses if r.status.value == "ineligible"]
        in_progress = [r for r in responses if r.status.value == "in_progress"]

        total = len(responses)
        completion_rate = round(len(complete) / total * 100, 1) if total else 0

        question_stats: Dict[str, Any] = {}
        flat_qs = flatten_questions_for_export(survey)

        for fq in flat_qs:
            qid = fq["id"]
            qtype = None
            for section in survey.sections:
                for q in section.questions:
                    if q.id == qid or qid.startswith(q.id):
                        qtype = q.type.value
                        break

            values = []
            for r in complete:
                val = r.answers.get(qid)
                if val is not None and val != "":
                    values.append(val)

            if not values:
                question_stats[qid] = {"text": fq["text"], "answered": 0}
                continue

            stat: Dict[str, Any] = {"text": fq["text"], "answered": len(values)}

            if qtype == "rating" or qid.endswith("__rating"):
                nums = [float(v) for v in values if str(v).replace(".", "").isdigit()]
                if nums:
                    stat["average"] = round(sum(nums) / len(nums), 2)
                    stat["distribution"] = dict(Counter(str(int(n)) for n in nums))
            elif qtype in ("single_choice",) or (isinstance(values[0], str) and not isinstance(values[0], list)):
                flat_vals = []
                for v in values:
                    if isinstance(v, list):
                        flat_vals.extend(v)
                    else:
                        flat_vals.append(str(v))
                stat["counts"] = dict(Counter(flat_vals))
            elif qtype == "multi_select" or any(isinstance(v, list) for v in values):
                flat_vals = []
                for v in values:
                    if isinstance(v, list):
                        flat_vals.extend(v)
                    else:
                        flat_vals.append(str(v))
                stat["counts"] = dict(Counter(flat_vals))
            else:
                stat["sample_responses"] = [_format_answer(v) for v in values[:5]]

            question_stats[qid] = stat

        return {
            "total_responses": total,
            "complete": len(complete),
            "ineligible": len(ineligible),
            "in_progress": len(in_progress),
            "completion_rate": completion_rate,
            "question_stats": question_stats,
        }

    def analyze(
        self,
        survey: HaloSurvey,
        responses: List[SurveyResponse],
        question: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        stats = self.aggregate_stats(survey, responses)
        context = {
            "survey_title": survey.title,
            "audience": survey.audience,
            "stats": stats,
        }

        # Include text samples for open-ended questions
        text_samples: Dict[str, List[str]] = {}
        for fq in flatten_questions_for_export(survey):
            qid = fq["id"]
            if qid.endswith("__text") or "long_text" in qid or "short_text" in qid:
                samples = []
                for r in responses:
                    if r.status.value != "complete":
                        continue
                    val = r.answers.get(qid)
                    if val and str(val).strip():
                        samples.append(str(val)[:500])
                if samples:
                    text_samples[fq["text"]] = samples[:10]
        context["text_samples"] = text_samples

        if not self.claude_service:
            return {
                "success": True,
                "stats": stats,
                "analysis": "AI analysis unavailable (Claude service not configured).",
                "stats_only": True,
            }

        user_prompt = question or (
            "Provide an executive summary of these survey results: key findings, "
            "notable patterns, areas of concern, and recommended next steps."
        )
        full_prompt = f"""Survey data context:
{json.dumps(context, indent=2)}

Analyst question:
{user_prompt}"""

        try:
            response = self.claude_service.send_message(
                message=full_prompt,
                system_prompt=ANALYZER_SYSTEM_PROMPT,
                conversation_history=conversation_history or [],
                max_tokens=4096,
                temperature=0.4,
            )
            analysis = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("Analysis failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "stats": stats,
                "error": str(exc),
            }

        return {
            "success": True,
            "stats": stats,
            "analysis": analysis,
        }

    def responses_to_csv_rows(
        self, survey: HaloSurvey, responses: List[SurveyResponse]
    ) -> tuple:
        flat_qs = flatten_questions_for_export(survey)
        headers = (
            ["response_id", "status", "started_at", "completed_at"]
            + [fq["id"] for fq in flat_qs]
            + ["external_id", "utm_source", "utm_campaign"]
        )
        rows = []
        for r in responses:
            meta = r.metadata or {}
            row = [
                r.response_id,
                r.status.value if hasattr(r.status, "value") else r.status,
                r.started_at,
                r.completed_at or "",
            ]
            for fq in flat_qs:
                val = r.answers.get(fq["id"])
                row.append(_format_answer(val))
            row.append(meta.get("external_id", meta.get("external_id", "")))
            row.append(meta.get("utm_source", ""))
            row.append(meta.get("utm_campaign", ""))
            rows.append(row)
        return headers, rows

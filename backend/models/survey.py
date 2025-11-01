"""
Survey data models
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SurveyResponse:
    """Represents a single survey response"""
    response_uuid: str
    respondent_uuid: str
    date_time: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    user_id: Optional[str]
    answers: Dict[str, Any]  # Dictionary of question answers
    metadata: Dict[str, Any]  # Device, Platform, Page, etc.
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SurveyResponse':
        """Create SurveyResponse from dictionary"""
        return cls(
            response_uuid=data.get('response_uuid', ''),
            respondent_uuid=data.get('respondent_uuid', ''),
            date_time=data.get('date_time', ''),
            email=data.get('email'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            user_id=data.get('user_id'),
            answers=data.get('answers', {}),
            metadata=data.get('metadata', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'response_uuid': self.response_uuid,
            'respondent_uuid': self.respondent_uuid,
            'date_time': self.date_time,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'user_id': self.user_id,
            'answers': self.answers,
            'metadata': self.metadata
        }
    
    @property
    def searchable_text(self) -> str:
        """Get all searchable text content"""
        text_parts = []
        
        # Add all answer values
        for question, answer in self.answers.items():
            if answer:
                if isinstance(answer, dict):
                    # Handle Answer/Comment structure
                    answer_text = answer.get('Answer', '') or answer.get('answer', '')
                    comment_text = answer.get('Comment', '') or answer.get('comment', '')
                    text_parts.append(str(answer_text))
                    if comment_text:
                        text_parts.append(str(comment_text))
                else:
                    text_parts.append(str(answer))
        
        # Add metadata
        if self.email:
            text_parts.append(self.email)
        if self.first_name:
            text_parts.append(self.first_name)
        if self.last_name:
            text_parts.append(self.last_name)
        
        return ' '.join(text_parts).lower()
    
    def get_answer(self, question_key: str) -> Optional[str]:
        """Get answer for a specific question"""
        answer_data = self.answers.get(question_key)
        if not answer_data:
            return None
        
        if isinstance(answer_data, dict):
            # Return Answer field, or Comment if Answer is empty
            return answer_data.get('Answer') or answer_data.get('answer') or answer_data.get('Comment') or answer_data.get('comment')
        return str(answer_data)


@dataclass
class SurveySummary:
    """Summary statistics for survey data"""
    total_responses: int
    date_range: Dict[str, str]
    question_stats: Dict[str, Dict[str, int]]  # Question -> {answer: count}
    response_rate_by_question: Dict[str, float]  # Question -> response rate percentage
    
    def to_string(self) -> str:
        """Convert to formatted string"""
        summary = f"""Survey Data Summary:
- Total responses: {self.total_responses}
- Date range: {self.date_range.get('start', 'Unknown')} to {self.date_range.get('end', 'Unknown')}

Question Response Rates:
"""
        for question, rate in sorted(self.response_rate_by_question.items()):
            summary += f"  - {question}: {rate:.1f}%\n"
        
        summary += "\nTop Answers by Question:\n"
        for question, stats in sorted(self.question_stats.items()):
            summary += f"\n  {question}:\n"
            # Sort by count and show top 5
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for answer, count in sorted_stats:
                summary += f"    - {answer}: {count}\n"
        
        return summary


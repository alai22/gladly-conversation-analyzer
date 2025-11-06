"""
Survey Parser Service for Survicate CSV files
"""

import csv
import os
from typing import List, Dict, Any, Optional
from ..utils.logging import get_logger
from ..models.survey import SurveyResponse

logger = get_logger('survey_parser_service')


class SurveyParserService:
    """Service for parsing Survicate CSV survey files"""
    
    def __init__(self, csv_path: str):
        """Initialize parser with CSV file path"""
        self.csv_path = csv_path
    
    def parse_csv(self) -> List[SurveyResponse]:
        """Parse the CSV file and return list of SurveyResponse objects"""
        if not os.path.exists(self.csv_path):
            logger.error(f"CSV file not found: {self.csv_path}")
            return []
        
        responses = []
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                logger.info(f"Parsing {len(rows)} survey responses from {self.csv_path}")
                
                for row_num, row in enumerate(rows, start=2):  # Start at 2 because row 1 is headers
                    try:
                        response = self._parse_row(row)
                        if response:
                            responses.append(response)
                    except Exception as e:
                        logger.warning(f"Failed to parse row {row_num}: {str(e)}")
                        continue
                
                logger.info(f"Successfully parsed {len(responses)} survey responses")
                
        except Exception as e:
            logger.error(f"Failed to parse CSV file: {str(e)}")
            raise
        
        return responses
    
    def _parse_row(self, row: Dict[str, str]) -> Optional[SurveyResponse]:
        """Parse a single CSV row into a SurveyResponse"""
        
        # Extract basic fields
        response_uuid = row.get('Response uuid', '').strip()
        respondent_uuid = row.get('Respondent uuid', '').strip()
        date_time = row.get('Date & Time (UTC)', '').strip()
        
        if not response_uuid or not date_time:
            # Skip invalid rows
            return None
        
        # Extract user information
        email = row.get('email', '').strip() or None
        first_name = row.get('first_name', '').strip() or None
        last_name = row.get('last_name', '').strip() or None
        user_id = row.get('user_id', '').strip() or None
        
        # Extract metadata
        metadata = {
            'device': row.get('Device', '').strip() or None,
            'platform': row.get('Platform', '').strip() or None,
            'page': row.get('Page', '').strip() or None,
            'braze_id': row.get('braze_id', '').strip() or None,
            'sso_id': row.get('sso_id', '').strip() or None,
        }
        
        # Extract all question answers (Q#1 through Q#19)
        # Cleaned CSV has headers like "Q#1: ... (Answer)" and "Q#1: ... (Comment)"
        answers = {}
        processed_questions = set()  # Track which questions we've processed
        
        for col_name, col_value in row.items():
            # Skip non-question columns
            if not col_name.startswith('Q#') and 'Q#' not in col_name:
                continue
            
            # Check if this is an Answer or Comment column
            is_answer = '(Answer)' in col_name
            is_comment = '(Comment)' in col_name
            
            if not (is_answer or is_comment):
                # Old format or question without Answer/Comment structure
                question_key = self._normalize_question_key(col_name)
                if question_key and question_key not in processed_questions:
                    answer_value = col_value.strip() if col_value else ''
                    if answer_value:
                        answers[question_key] = {
                            'Answer': answer_value,
                            'Comment': None
                        }
                        processed_questions.add(question_key)
                continue
            
            # Extract question key from cleaned header format
            question_key = self._normalize_question_key(col_name)
            if not question_key:
                continue
            
            # Initialize answer dict if not already present
            if question_key not in answers:
                answers[question_key] = {'Answer': None, 'Comment': None}
            
            # Set Answer or Comment value
            value = col_value.strip() if col_value else ''
            if is_answer:
                answers[question_key]['Answer'] = value if value else None
            elif is_comment:
                answers[question_key]['Comment'] = value if value else None
            
            processed_questions.add(question_key)
        
        # Remove entries with no Answer or Comment
        answers = {k: v for k, v in answers.items() if v.get('Answer') or v.get('Comment')}
        
        return SurveyResponse(
            response_uuid=response_uuid,
            respondent_uuid=respondent_uuid,
            date_time=date_time,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_id=user_id,
            answers=answers,
            metadata=metadata
        )
    
    def _normalize_question_key(self, col_name: str) -> Optional[str]:
        """Normalize column name to question key"""
        # Remove emoji and extra characters
        col_name = col_name.strip()
        
        # Look for Q# pattern
        import re
        match = re.search(r'Q#(\d+)', col_name)
        if match:
            question_num = match.group(1)
            return f"Q{question_num}"
        
        return None
    
    def _find_comment_column(self, answer_col: str, all_columns: List[str]) -> Optional[str]:
        """Find the Comment column that corresponds to an Answer column"""
        # The CSV has Answer/Comment pairs
        # Comment columns are typically empty columns right after Answer columns
        # or have the same question number
        
        # Extract question number from answer column
        import re
        match = re.search(r'Q#(\d+)', answer_col)
        if not match:
            return None
        
        question_num = match.group(1)
        
        # Find columns with same question number that might be Comment columns
        # Comments might be in the next column or have "Comment" in the header row
        # Since CSV structure has Answer/Comment pairs, we'll look for the pattern
        
        for col in all_columns:
            if f"Q#{question_num}" in col and "Comment" in col:
                return col
        
        # If no explicit Comment column, check if next column after answer is empty (might be comment)
        return None


"""
Survey data service
"""

from typing import List, Dict, Optional, Any
from ..utils.config import Config
from ..utils.logging import get_logger
from ..models.survey import SurveyResponse, SurveySummary
from .survey_parser_service import SurveyParserService

logger = get_logger('survey_service')


class SurveyService:
    """Service for managing survey data"""
    
    def __init__(self, csv_path: Optional[str] = None):
        """Initialize survey service"""
        self.csv_path = csv_path or Config.SURVICATE_CSV_PATH
        self.surveys: List[SurveyResponse] = []
        self.load_surveys()
    
    def load_surveys(self):
        """Load surveys from CSV file"""
        try:
            parser = SurveyParserService(self.csv_path)
            self.surveys = parser.parse_csv()
            logger.info(f"Surveys loaded: {len(self.surveys)}")
        except Exception as e:
            logger.error(f"Failed to load surveys: {str(e)}")
            self.surveys = []
    
    def get_summary(self) -> SurveySummary:
        """Get survey data summary"""
        if not self.surveys:
            return SurveySummary(
                total_responses=0,
                date_range={'start': 'Unknown', 'end': 'Unknown'},
                question_stats={},
                response_rate_by_question={}
            )
        
        # Calculate date range
        dates = [s.date_time for s in self.surveys if s.date_time]
        dates.sort()
        date_range = {
            'start': dates[0] if dates else 'Unknown',
            'end': dates[-1] if dates else 'Unknown'
        }
        
        # Calculate question statistics
        question_stats = {}
        question_response_counts = {}
        
        for survey in self.surveys:
            for question_key, answer_data in survey.answers.items():
                if question_key not in question_stats:
                    question_stats[question_key] = {}
                    question_response_counts[question_key] = 0
                
                # Extract answer value
                if isinstance(answer_data, dict):
                    answer_value = answer_data.get('Answer') or answer_data.get('answer') or ''
                    comment_value = answer_data.get('Comment') or answer_data.get('comment') or ''
                    # Use answer if available, otherwise use comment
                    answer_text = answer_value if answer_value else comment_value
                else:
                    answer_text = str(answer_data) if answer_data else ''
                
                if answer_text:
                    question_response_counts[question_key] += 1
                    answer_text = answer_text.strip()
                    if answer_text:
                        question_stats[question_key][answer_text] = question_stats[question_key].get(answer_text, 0) + 1
        
        # Calculate response rates
        total_surveys = len(self.surveys)
        response_rate_by_question = {}
        for question_key, count in question_response_counts.items():
            response_rate_by_question[question_key] = (count / total_surveys * 100) if total_surveys > 0 else 0
        
        return SurveySummary(
            total_responses=total_surveys,
            date_range=date_range,
            question_stats=question_stats,
            response_rate_by_question=response_rate_by_question
        )
    
    def search_surveys(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search surveys for specific content"""
        if not self.surveys:
            return []
        
        query_lower = query.lower()
        results = []
        
        for survey in self.surveys:
            if query_lower in survey.searchable_text:
                results.append(survey.to_dict())
                if len(results) >= limit:
                    break
        
        logger.info(f"Search completed: query={query}, results_count={len(results)}")
        return results
    
    def semantic_search_surveys(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Enhanced semantic search with concept mappings"""
        if not self.surveys:
            logger.warning(f"Semantic search called but no surveys available (total: {len(self.surveys)})")
            return []
        
        query_lower = query.lower()
        scored_results = []
        
        # Define concept mappings for survey-specific terms
        concept_mappings = {
            'cancel': ['cancel', 'cancelled', 'cancellation', 'canceled', 'stopped', 'ended'],
            'reason': ['reason', 'why', 'because', 'due to', 'caused by'],
            'gps': ['gps', 'location', 'pin', 'coordinates', 'position', 'map', 'tracking', 'accuracy'],
            'battery': ['battery', 'charge', 'charging', 'power', 'dead', 'low', 'drain', 'life'],
            'expensive': ['expensive', 'cost', 'price', 'pricing', 'afford', 'value', 'worth'],
            'dog': ['dog', 'pet', 'animal', 'puppy', 'canine'],
            'response': ['response', 'respond', 'feedback', 'reaction', 'react'],
            'training': ['training', 'train', 'learn', 'curriculum', 'teach'],
            'customer_service': ['customer service', 'support', 'help', 'service', 'contact'],
            'containment': ['containment', 'fence', 'boundary', 'correction', 'feedback'],
            'feedback': ['feedback', 'correction', 'static', 'vibration', 'sound'],
        }
        
        # Find related concepts
        related_terms = set()
        for concept, terms in concept_mappings.items():
            if any(term in query_lower for term in terms):
                related_terms.update(terms)
        
        # Add original query terms
        related_terms.update(word.lower() for word in query.split())
        
        query_words = query_lower.split()
        for word in query_words:
            related_terms.add(word)
            if len(word) > 4:
                related_terms.add(word[:4])
        
        items_checked = 0
        items_with_searchable_text = 0
        
        for survey in self.surveys:
            items_checked += 1
            score = 0
            
            searchable = survey.searchable_text
            if searchable:
                items_with_searchable_text += 1
            
            # Calculate relevance score
            for term in related_terms:
                term_lower = term.lower()
                if term_lower and searchable and term_lower in searchable:
                    if term_lower == query_lower:
                        score += 10
                    elif term_lower in concept_mappings.get(query_lower, []):
                        score += 5
                    elif any(term_lower in mapped_term for mapped_term in concept_mappings.values()):
                        score += 2
                    else:
                        score += 1
            
            if score > 0:
                scored_results.append((survey.to_dict(), score))
        
        # Sort by relevance score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        results = [item for item, score in scored_results[:limit]]
        
        logger.info(f"Semantic search: query='{query}', checked={items_checked} surveys, "
                   f"with_searchable_text={items_with_searchable_text}, scored={len(scored_results)}, "
                   f"returning={len(results)} results")
        
        return results
    
    def get_surveys_by_date_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get surveys within a date range"""
        if not self.surveys:
            return []
        
        from datetime import datetime
        
        results = []
        for survey in self.surveys:
            if not survey.date_time:
                continue
            
            try:
                survey_date = datetime.strptime(survey.date_time, '%Y-%m-%d %H:%M:%S')
                
                if start_date:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    if survey_date < start:
                        continue
                
                if end_date:
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    # Set end to end of day
                    from datetime import timedelta
                    end = end + timedelta(days=1) - timedelta(seconds=1)
                    if survey_date > end:
                        continue
                
                results.append(survey.to_dict())
            except:
                # Skip surveys with invalid dates
                continue
        
        logger.info(f"Retrieved {len(results)} surveys for date range: {start_date} to {end_date}")
        return results
    
    def refresh_surveys(self):
        """Refresh surveys from CSV file"""
        logger.info("Refreshing surveys from CSV")
        self.load_surveys()
        logger.info(f"Surveys refreshed: {len(self.surveys)}")
    
    def is_available(self) -> bool:
        """Check if survey service is available"""
        return len(self.surveys) > 0


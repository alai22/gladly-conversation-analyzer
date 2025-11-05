"""
Survicate RAG (Retrieval-Augmented Generation) service for survey analysis
"""

from typing import Dict, Any, List
from ..utils.logging import get_logger
from ..utils.helpers import extract_json_from_text
from ..models.response import RAGProcess, RAGStep
from .claude_service import ClaudeService
from .survey_service import SurveyService

logger = get_logger('survicate_rag_service')


class SurvicateRAGService:
    """Service for RAG-powered survey analysis"""
    
    def __init__(self, claude_service: ClaudeService, survey_service: SurveyService):
        """Initialize Survicate RAG service"""
        self.claude_service = claude_service
        self.survey_service = survey_service
    
    def process_query(self, question: str, model: str = None, max_tokens: int = 2000) -> Dict[str, Any]:
        """Process a RAG query about surveys"""
        logger.info(f"Starting Survicate RAG query processing: {question[:100]}")
        
        # Check if surveys are loaded, and if not, try to refresh
        if not self.survey_service.is_available():
            logger.info("Surveys not available, attempting to refresh...")
            try:
                self.survey_service.refresh_surveys()
                logger.info(f"Surveys refreshed: {len(self.survey_service.surveys)} responses loaded")
            except Exception as e:
                logger.warning(f"Failed to auto-refresh surveys: {e}")
        
        # Initialize RAG process tracking
        rag_process = RAGProcess(steps=[])
        
        # Step 1: Query Planning
        plan = self._plan_query(question, model, rag_process)
        
        # Step 2: Data Retrieval
        relevant_data = self._retrieve_data(plan, rag_process)
        
        # Step 3: Data Analysis
        response = self._analyze_data(question, relevant_data, plan, model, max_tokens, rag_process)
        
        logger.info(f"Survicate RAG query processing completed: data_retrieved={len(relevant_data)}, tokens_used={response.tokens_used}")
        
        return {
            'success': True,
            'response': {
                'content': [{'type': 'text', 'text': response.content}],
                'usage': {'output_tokens': response.tokens_used}
            },
            'rag_process': {
                'steps': [
                    {
                        'step': step.step,
                        'name': step.name,
                        'description': step.description,
                        'status': step.status,
                        'details': step.details,
                        'warning': step.warning
                    } for step in rag_process.steps
                ],
                'plan': rag_process.plan,
                'retrieval_stats': rag_process.retrieval_stats,
                'data_summary': rag_process.data_summary
            },
            'data_retrieved': len(relevant_data),
            'plan': plan
        }
    
    def _plan_query(self, question: str, model: str, rag_process: RAGProcess) -> Dict[str, Any]:
        """Step 1: Query Planning"""
        rag_process.add_step(1, 'Query Planning', 'Claude analyzes your question and creates a retrieval plan')
        
        query_planning_prompt = f"""You are a survey analysis assistant. I have customer cancellation survey data from Survicate with the following structure:

Data Available:
- Survey responses with answers to Q#1 through Q#19
- Date & Time (UTC) for each response
- User information (email, name, user_id)
- Questions cover cancellation reasons, GPS issues, battery problems, training, customer service, etc.

Each survey response contains:
- Date/time of response
- Answers to multiple-choice and open-ended questions
- Some questions have both "Answer" and "Comment" fields

Question: "{question}"

Based on this question, provide a JSON response with:
1. "search_terms": List of specific terms to search for in survey responses
2. "questions_of_interest": List of question keys (Q1, Q2, etc.) that might be relevant
3. "time_filters": Any time-based filtering needed (e.g., "last_30_days", "date_range", "all")
4. "analysis_focus": What specific aspects to focus on in the analysis (themes, trends, patterns)
5. "max_items": Maximum number of survey responses to retrieve (suggest 50-200)
6. "trend_analysis": Whether this query requires trend analysis over time (true/false)

Be specific and comprehensive in your search terms. Think about synonyms and different ways users might express the same issue.

Respond with valid JSON only."""
        
        try:
            planning_response = self.claude_service.send_message(
                message=query_planning_prompt,
                model=model,
                max_tokens=500
            )
            
            # Extract JSON from response
            plan = extract_json_from_text(planning_response.content)
            if not plan:
                raise ValueError("Could not extract JSON from planning response")
            
            rag_process.plan = plan
            rag_process.update_step(1, 'completed', {
                'search_terms': plan.get('search_terms', []),
                'questions_of_interest': plan.get('questions_of_interest', []),
                'time_filters': plan.get('time_filters', 'all'),
                'analysis_focus': plan.get('analysis_focus', 'general analysis'),
                'max_items': plan.get('max_items', 100),
                'trend_analysis': plan.get('trend_analysis', False)
            })
            
        except Exception as e:
            logger.warning(f"Query planning failed, using fallback: {str(e)}")
            plan = {
                "search_terms": [question],
                "questions_of_interest": [],
                "time_filters": "all",
                "analysis_focus": "general analysis",
                "max_items": 100,
                "trend_analysis": False
            }
            rag_process.plan = plan
            rag_process.update_step(1, 'completed', plan, f"Planning failed, using fallback: {str(e)}")
        
        return plan
    
    def _retrieve_data(self, plan: Dict[str, Any], rag_process: RAGProcess) -> List[Dict[str, Any]]:
        """Step 2: Data Retrieval"""
        rag_process.add_step(2, 'Data Retrieval', 'Semantic search retrieves relevant survey responses')
        
        relevant_data = []
        retrieval_stats = {
            'total_searched': 0,
            'by_search_term': {},
            'filtered_out': 0,
            'total_available': len(self.survey_service.surveys),
            'diagnostics': {}
        }
        
        # Check if surveys are loaded
        if not self.survey_service.is_available():
            logger.warning("No surveys loaded in survey service - retrieval will return empty")
            retrieval_stats['diagnostics']['error'] = 'No surveys loaded in service'
            retrieval_stats['diagnostics']['service_status'] = {
                'is_available': False,
                'survey_count': len(self.survey_service.surveys)
            }
            rag_process.retrieval_stats = retrieval_stats
            rag_process.update_step(2, 'completed', retrieval_stats, 
                                   "Warning: No survey data is currently loaded. Please ensure the CSV file exists and refresh the survey service.")
            return []
        
        total_available = len(self.survey_service.surveys)
        retrieval_stats['diagnostics']['total_available'] = total_available
        retrieval_stats['diagnostics']['search_terms_count'] = len(plan.get('search_terms', []))
        
        # Search using the planned terms with semantic search
        search_terms = plan.get('search_terms', [])
        for term in search_terms:
            term_limit = max(1, plan.get('max_items', 100) // max(len(search_terms), 1))
            results = self.survey_service.semantic_search_surveys(
                term, limit=term_limit
            )
            relevant_data.extend(results)
            retrieval_stats['by_search_term'][term] = {
                'count': len(results),
                'limit_requested': term_limit
            }
            retrieval_stats['total_searched'] += len(results)
            logger.info(f"Search term '{term}': found {len(results)} results (requested {term_limit})")
        
        logger.info(f"Retrieved {len(relevant_data)} survey responses using search terms: {search_terms}")
        
        # Add minimum threshold check - if we got very few results, use fallback to get diverse sample
        # This handles broad queries like "what do people say in the surveys" that might not match well semantically
        MIN_RESULTS_THRESHOLD = 20  # If we get fewer than this, use fallback for better coverage
        if len(relevant_data) < MIN_RESULTS_THRESHOLD and total_available > 0:
            logger.warning(f"Semantic search returned only {len(relevant_data)} results (below threshold of {MIN_RESULTS_THRESHOLD}). Using fallback to get diverse sample for better analysis coverage.")
            retrieval_stats['diagnostics']['fallback_used'] = True
            retrieval_stats['diagnostics']['fallback_reason'] = f'Semantic search returned only {len(relevant_data)} results, below minimum threshold'
            retrieval_stats['diagnostics']['min_threshold'] = MIN_RESULTS_THRESHOLD
            
            # Clear the sparse results and use fallback instead
            relevant_data = []
            fallback_limit = min(plan.get('max_items', 100), total_available)
            seen_uuids = set()
            
            # Get a diverse sample across all surveys
            for survey in self.survey_service.surveys:
                if len(relevant_data) >= fallback_limit:
                    break
                
                survey_dict = survey.to_dict()
                response_uuid = survey_dict.get('response_uuid')
                if response_uuid in seen_uuids:
                    continue
                seen_uuids.add(response_uuid)
                relevant_data.append(survey_dict)
            
            retrieval_stats['by_search_term']['_fallback'] = {'count': len(relevant_data), 'reason': f'Below threshold ({len(relevant_data)} < {MIN_RESULTS_THRESHOLD})'}
            retrieval_stats['total_searched'] = len(relevant_data)
            logger.info(f"Fallback: Returning {len(relevant_data)} diverse sample surveys for comprehensive analysis")
        
        # Apply time filters if specified
        time_filters = plan.get('time_filters', 'all')
        if time_filters != 'all':
            from datetime import datetime, timedelta
            
            if time_filters == 'last_30_days':
                cutoff = datetime.now() - timedelta(days=30)
            elif time_filters == 'last_7_days':
                cutoff = datetime.now() - timedelta(days=7)
            elif time_filters == 'last_90_days':
                cutoff = datetime.now() - timedelta(days=90)
            else:
                cutoff = None
            
            if cutoff:
                before_filter = len(relevant_data)
                filtered_data = []
                for item in relevant_data:
                    date_time = item.get('date_time')
                    if date_time:
                        try:
                            survey_date = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                            if survey_date >= cutoff:
                                filtered_data.append(item)
                        except:
                            # Include items with invalid dates
                            filtered_data.append(item)
                    else:
                        # Include items without dates
                        filtered_data.append(item)
                
                relevant_data = filtered_data
                retrieval_stats['filtered_out'] = before_filter - len(relevant_data)
                retrieval_stats['diagnostics']['time_filter'] = {
                    'type': time_filters,
                    'before_filter': before_filter,
                    'after_filter': len(relevant_data)
                }
        
        # Remove duplicates and limit
        seen_uuids = set()
        unique_data = []
        for item in relevant_data:
            response_uuid = item.get('response_uuid')
            if response_uuid and response_uuid not in seen_uuids:
                seen_uuids.add(response_uuid)
                unique_data.append(item)
                if len(unique_data) >= plan.get('max_items', 100):
                    break
        
        retrieval_stats['final_count'] = len(unique_data)
        retrieval_stats['duplicates_removed'] = len(relevant_data) - len(unique_data)
        retrieval_stats['diagnostics']['unique_items'] = len(unique_data)
        
        rag_process.retrieval_stats = retrieval_stats
        status_message = f"Retrieved {len(unique_data)} survey responses"
        if retrieval_stats.get('diagnostics', {}).get('fallback_used'):
            fallback_reason = retrieval_stats.get('diagnostics', {}).get('fallback_reason', 'insufficient results')
            if '0 results' in fallback_reason:
                status_message += " (using fallback: semantic search returned no results)"
            else:
                status_message += f" (using fallback: {fallback_reason})"
        rag_process.update_step(2, 'completed', retrieval_stats, status_message if len(unique_data) > 0 else None)
        
        return unique_data
    
    def _analyze_data(self, question: str, relevant_data: List[Dict[str, Any]], 
                     plan: Dict[str, Any], model: str, max_tokens: int, 
                     rag_process: RAGProcess):
        """Step 3: Data Analysis"""
        rag_process.add_step(3, 'Analysis', 'Claude analyzes the retrieved survey data to answer your question')
        
        # Get survey summary for context
        summary = self.survey_service.get_summary().to_string()
        
        # Format the survey data for Claude
        from ..utils.helpers import format_survey_for_claude
        survey_text = format_survey_for_claude(relevant_data)
        
        # Create system prompt
        from ..utils.helpers import create_survicate_rag_system_prompt
        system_prompt = create_survicate_rag_system_prompt(summary, survey_text, plan, question)
        
        response = self.claude_service.send_message(
            message=question,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
        
        rag_process.update_step(3, 'completed', {
            'tokens_used': response.tokens_used,
            'model_used': model
        })
        
        # Create data summary
        date_range = {'earliest': 'Unknown', 'latest': 'Unknown'}
        if relevant_data:
            dates = [item.get('date_time') for item in relevant_data if item.get('date_time')]
            if dates:
                dates.sort()
                date_range = {'earliest': dates[0], 'latest': dates[-1]}
        
        rag_process.data_summary = {
            'total_responses': len(relevant_data),
            'date_range': date_range,
            'questions_covered': list(set(
                question_key 
                for item in relevant_data 
                for question_key in item.get('answers', {}).keys()
            ))
        }
        
        return response


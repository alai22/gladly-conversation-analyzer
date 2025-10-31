"""
RAG (Retrieval-Augmented Generation) service
"""

from typing import Dict, Any, List
from ..utils.logging import get_logger
from ..utils.helpers import extract_json_from_text, format_conversation_for_claude, create_rag_system_prompt
from ..models.response import RAGProcess, RAGStep
from .claude_service import ClaudeService
from .conversation_service import ConversationService

logger = get_logger('rag_service')


class RAGService:
    """Service for RAG-powered conversation analysis"""
    
    def __init__(self, claude_service: ClaudeService, conversation_service: ConversationService):
        """Initialize RAG service"""
        self.claude_service = claude_service
        self.conversation_service = conversation_service
    
    def process_query(self, question: str, model: str = None, max_tokens: int = 2000) -> Dict[str, Any]:
        """Process a RAG query"""
        logger.info(f"Starting RAG query processing: {question[:100]}")
        
        # Initialize RAG process tracking
        rag_process = RAGProcess(steps=[])
        
        # Step 1: Query Planning
        plan = self._plan_query(question, model, rag_process)
        
        # Step 2: Data Retrieval
        relevant_data = self._retrieve_data(plan, rag_process)
        
        # Step 3: Data Analysis
        response = self._analyze_data(question, relevant_data, plan, model, max_tokens, rag_process)
        
        logger.info(f"RAG query processing completed: data_retrieved={len(relevant_data)}, tokens_used={response.tokens_used}")
        
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
        
        query_planning_prompt = f"""You are a data analysis assistant. I have customer support conversation data with the following structure:

Data Types Available:
- CHAT_MESSAGE: Customer and agent chat messages
- EMAIL: Email communications with subjects and content
- CONVERSATION_NOTE: Agent notes and internal documentation
- CONVERSATION_STATUS_CHANGE: Status updates (OPEN/CLOSED)
- PHONE_CALL: Phone call records
- TOPIC_CHANGE: Topic changes in conversations

Each item has: timestamp, customerId, conversationId, and content (which varies by type).

Question: "{question}"

Based on this question, provide a JSON response with:
1. "search_terms": List of specific terms to search for in the conversation content
2. "content_types": List of content types to focus on (e.g., ["CHAT_MESSAGE", "EMAIL"])
3. "time_filters": Any time-based filtering needed (e.g., "last_24_hours", "specific_date_range", "all")
4. "analysis_focus": What specific aspects to focus on in the analysis
5. "max_items": Maximum number of conversation items to retrieve (suggest 50-200)

Be specific and comprehensive in your search terms. Think about synonyms, related terms, and different ways the same issue might be expressed.

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
                'search_terms': plan['search_terms'],
                'content_types': plan['content_types'],
                'time_filters': plan['time_filters'],
                'analysis_focus': plan['analysis_focus'],
                'max_items': plan['max_items']
            })
            
        except Exception as e:
            logger.warning(f"Query planning failed, using fallback: {str(e)}")
            plan = {
                "search_terms": [question],
                "content_types": ["CHAT_MESSAGE", "EMAIL", "CONVERSATION_NOTE"],
                "time_filters": "all",
                "analysis_focus": "general analysis",
                "max_items": 100
            }
            rag_process.plan = plan
            rag_process.update_step(1, 'completed', plan, f"Planning failed, using fallback: {str(e)}")
        
        return plan
    
    def _retrieve_data(self, plan: Dict[str, Any], rag_process: RAGProcess) -> List[Dict[str, Any]]:
        """Step 2: Data Retrieval"""
        rag_process.add_step(2, 'Data Retrieval', 'Semantic search retrieves relevant conversation data')
        
        relevant_data = []
        retrieval_stats = {
            'total_searched': 0,
            'by_content_type': {},
            'by_search_term': {},
            'filtered_out': 0
        }
        
        # Check if conversations are loaded
        if not self.conversation_service.is_available():
            logger.warning("No conversations loaded in conversation service - retrieval will return empty")
            rag_process.retrieval_stats = retrieval_stats
            rag_process.update_step(2, 'completed', retrieval_stats, 
                                   "Warning: No conversation data is currently loaded. Please ensure conversations have been downloaded and aggregated.")
            return []
        
        # Search using the planned terms with semantic search
        for term in plan['search_terms']:
            results = self.conversation_service.semantic_search_conversations(
                term, limit=plan['max_items'] // len(plan['search_terms'])
            )
            relevant_data.extend(results)
            retrieval_stats['by_search_term'][term] = len(results)
            retrieval_stats['total_searched'] += len(results)
            
        logger.info(f"Retrieved {len(relevant_data)} items using search terms: {plan['search_terms']}")
        
        # Filter by content types if specified
        if plan['content_types'] != ["all"]:
            before_filter = len(relevant_data)
            relevant_data = [item for item in relevant_data 
                           if item.get('content', {}).get('type') in plan['content_types']]
            retrieval_stats['filtered_out'] = before_filter - len(relevant_data)
            
            # Count by content type
            for item in relevant_data:
                content_type = item.get('content', {}).get('type', 'Unknown')
                retrieval_stats['by_content_type'][content_type] = retrieval_stats['by_content_type'].get(content_type, 0) + 1
        
        # Apply time filters if specified (intersect with existing results, don't replace)
        if plan['time_filters'] == "last_24_hours":
            recent_ids = {item.get('id') for item in self.conversation_service.get_recent_conversations(24)}
            if recent_ids:
                relevant_data = [item for item in relevant_data if item.get('id') in recent_ids]
            else:
                # If no recent conversations, keep what we have but note it in stats
                logger.warning("Time filter 'last_24_hours' found no recent conversations, keeping all search results")
        elif plan['time_filters'] == "last_7_days":
            recent_ids = {item.get('id') for item in self.conversation_service.get_recent_conversations(24 * 7)}
            if recent_ids:
                relevant_data = [item for item in relevant_data if item.get('id') in recent_ids]
            else:
                logger.warning("Time filter 'last_7_days' found no recent conversations, keeping all search results")
        
        # Remove duplicates and limit
        seen_ids = set()
        unique_data = []
        for item in relevant_data:
            if item.get('id') not in seen_ids:
                seen_ids.add(item.get('id'))
                unique_data.append(item)
                if len(unique_data) >= plan['max_items']:
                    break
        
        retrieval_stats['final_count'] = len(unique_data)
        retrieval_stats['duplicates_removed'] = len(relevant_data) - len(unique_data)
        
        rag_process.retrieval_stats = retrieval_stats
        rag_process.update_step(2, 'completed', retrieval_stats)
        
        return unique_data
    
    def _analyze_data(self, question: str, relevant_data: List[Dict[str, Any]], 
                     plan: Dict[str, Any], model: str, max_tokens: int, 
                     rag_process: RAGProcess):
        """Step 3: Data Analysis"""
        rag_process.add_step(3, 'Analysis', 'Claude analyzes the retrieved data to answer your question')
        
        # Get conversation summary for context
        summary = self.conversation_service.get_summary().to_string()
        
        # Format the conversation data for Claude
        conversation_text = format_conversation_for_claude(relevant_data)
        
        # Create system prompt
        system_prompt = create_rag_system_prompt(summary, conversation_text, plan, question)
        
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
        content_types_found = list(set(item.get('content', {}).get('type', 'Unknown') for item in relevant_data)) if relevant_data else []
        
        date_range = {'earliest': 'Unknown', 'latest': 'Unknown'}
        if relevant_data:
            timestamps = [item.get('timestamp', '') for item in relevant_data if item.get('timestamp')]
            if timestamps:
                date_range = {
                    'earliest': min(timestamps),
                    'latest': max(timestamps)
                }
        
        rag_process.data_summary = {
            'total_conversations': len(self.conversation_service.conversations),
            'retrieved_items': len(relevant_data),
            'content_types_found': content_types_found,
            'date_range': date_range
        }
        
        return response

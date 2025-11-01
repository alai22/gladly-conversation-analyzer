"""
API routes for Survicate survey analysis
"""

from flask import Blueprint, request, jsonify, g
from ...utils.logging import get_logger
from ...utils.config import Config

logger = get_logger('survicate_routes')

# Create blueprint
survicate_bp = Blueprint('survicate', __name__, url_prefix='/api/survicate')


@survicate_bp.route('/ask', methods=['POST'])
def survicate_ask():
    """Ask Claude about survey data with detailed RAG process information"""
    try:
        # Get services from container (injected via Flask's g)
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        claude_service = service_container.get_claude_service()
        survicate_rag_service = service_container.get_survicate_rag_service()
        
        data = request.get_json()
        question = data.get('question')
        # Default to configured model (falls back to working model via fallback system if needed)
        model = data.get('model', Config.CLAUDE_MODEL)
        max_tokens = data.get('max_tokens', 2000)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        logger.info(f"Survicate RAG query request: question={question[:100]}, model={model}, max_tokens={max_tokens}")
        
        # Check if Claude service is initialized
        if claude_service is None or survicate_rag_service is None:
            error_msg = "Claude API service is not initialized. Please check ANTHROPIC_API_KEY configuration."
            logger.error(error_msg)
            return jsonify({
                'error': error_msg, 
                'details': 'ANTHROPIC_API_KEY environment variable is not set or invalid. Please configure it in your .env file or environment.'
            }), 503
        
        result = survicate_rag_service.process_query(question, model, max_tokens)
        
        return jsonify(result)
    
    except TimeoutError as e:
        error_msg = str(e) if str(e) else "Request to Claude API timed out. The query may be too complex."
        logger.error(f"Survicate RAG query timeout: {error_msg}")
        return jsonify({
            'error': 'Request timeout',
            'details': error_msg,
            'type': 'TimeoutError',
            'suggestion': 'Try simplifying your query or increasing CLAUDE_API_TIMEOUT if needed.'
        }), 504
    
    except ValueError as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        return jsonify({'error': error_msg, 'details': 'Please check your API configuration (ANTHROPIC_API_KEY)'}), 500
    except Exception as e:
        import traceback
        logger.error(f"Survicate RAG query error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        error_details = str(e)
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            error_details = f"{str(e)} - Response: {e.response.text}"
        
        return jsonify({
            'error': str(e),
            'details': error_details,
            'type': type(e).__name__
        }), 500


@survicate_bp.route('/refresh', methods=['POST'])
def refresh_surveys():
    """Refresh survey data from CSV file"""
    try:
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        survey_service = service_container.get_survey_service()
        survey_service.refresh_surveys()
        
        summary = survey_service.get_summary()
        
        return jsonify({
            'success': True,
            'message': f'Surveys refreshed: {len(survey_service.surveys)} responses loaded',
            'summary': {
                'total_responses': summary.total_responses,
                'date_range': summary.date_range
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to refresh surveys: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to refresh survey data from CSV file'
        }), 500


@survicate_bp.route('/summary', methods=['GET'])
def get_survey_summary():
    """Get survey statistics"""
    try:
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        survey_service = service_container.get_survey_service()
        summary = survey_service.get_summary()
        
        return jsonify({
            'success': True,
            'summary': {
                'total_responses': summary.total_responses,
                'date_range': summary.date_range,
                'question_stats': summary.question_stats,
                'response_rate_by_question': summary.response_rate_by_question
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to get survey summary: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to get survey summary'
        }), 500


@survicate_bp.route('/search', methods=['POST'])
def search_surveys():
    """Search survey responses"""
    try:
        service_container = getattr(g, 'service_container', None)
        if not service_container:
            logger.error("Service container not available in request context")
            return jsonify({'error': 'Service container not initialized'}), 500
        
        survey_service = service_container.get_survey_service()
        
        data = request.get_json()
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        results = survey_service.semantic_search_surveys(query, limit=limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        logger.error(f"Failed to search surveys: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to search survey data'
        }), 500


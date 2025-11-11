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


@survicate_bp.route('/churn-trends', methods=['GET'])
def get_churn_trends():
    """Get churn reason trends by month for visualization"""
    try:
        import pandas as pd
        import os
        
        # Get the path to the CSV file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, '..', '..', '..', 'data', 
                                'survicate_cancelled_subscriptions_augmented.csv')
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found at {csv_path}")
            return jsonify({
                'error': 'Data file not found',
                'details': f'Expected file at: {csv_path}'
            }), 404
        
        # Read the CSV
        df = pd.read_csv(csv_path)
        
        # Filter out rows with missing data
        df = df[df['augmented_churn_reason'].notna() & df['year_month'].notna()]
        
        if len(df) == 0:
            return jsonify({
                'error': 'No valid data found',
                'details': 'No rows with valid augmented_churn_reason and year_month'
            }), 400
        
        # Group by year_month and augmented_churn_reason
        grouped = df.groupby(['year_month', 'augmented_churn_reason']).size().reset_index(name='count')
        
        # Calculate percentages for each month
        monthly_totals = df.groupby('year_month').size()
        grouped['percentage'] = grouped.apply(
            lambda row: (row['count'] / monthly_totals[row['year_month']]) * 100, 
            axis=1
        )
        
        # Get unique months and reasons
        months = sorted(grouped['year_month'].unique())
        reasons = sorted(grouped['augmented_churn_reason'].unique())
        
        # Format data for frontend - create array of objects with month and all reason percentages and counts
        data = []
        for month in months:
            month_data = {'month': month}
            month_total = int(monthly_totals[month])
            month_data['_total'] = month_total  # Store total for the month
            month_df = grouped[grouped['year_month'] == month]
            for reason in reasons:
                reason_data = month_df[month_df['augmented_churn_reason'] == reason]
                count_key = f'{reason}_count'
                if len(reason_data) > 0:
                    month_data[reason] = round(reason_data['percentage'].values[0], 2)
                    month_data[count_key] = int(reason_data['count'].values[0])
                else:
                    month_data[reason] = 0
                    month_data[count_key] = 0
            data.append(month_data)
        
        # Calculate total counts for each reason (for sorting/legend)
        reason_totals = {}
        for reason in reasons:
            reason_totals[reason] = int(grouped[grouped['augmented_churn_reason'] == reason]['count'].sum())
        
        # Sort reasons by total count (descending) for consistent ordering
        sorted_reasons = sorted(reasons, key=lambda x: reason_totals[x], reverse=True)
        
        return jsonify({
            'success': True,
            'data': data,
            'reasons': sorted_reasons,
            'months': months,
            'reason_totals': reason_totals,
            'total_responses': int(len(df))
        })
    
    except Exception as e:
        import traceback
        logger.error(f"Failed to get churn trends: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to process churn trends data'
        }), 500


@survicate_bp.route('/generate-pdf-report', methods=['POST'])
def generate_pdf_report():
    """Generate and return a PDF report of churn trends"""
    try:
        import sys
        import os
        
        # Get the path to the script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, '..', '..', '..', 'generate_churn_report.py')
        
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'PDF generation script not found',
                'details': f'Expected script at: {script_path}'
            }), 404
        
        # Import and run the PDF generation
        sys.path.insert(0, os.path.dirname(script_path))
        from generate_churn_report import generate_churn_report
        
        # Get CSV path
        csv_path = os.path.join(current_dir, '..', '..', '..', 'data', 
                                'survicate_cancelled_subscriptions_augmented.csv')
        
        # Generate PDF in a temporary location
        import tempfile
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, 'churn_reasons_report.pdf')
        
        result = generate_churn_report(csv_path=csv_path, output_path=output_path)
        
        if result and os.path.exists(result):
            from flask import send_file
            return send_file(
                result,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='churn_reasons_report.pdf'
            )
        else:
            return jsonify({
                'error': 'Failed to generate PDF',
                'details': 'PDF generation completed but file not found'
            }), 500
    
    except ImportError as e:
        logger.error(f"Failed to import PDF generation script: {str(e)}")
        return jsonify({
            'error': 'PDF generation dependencies not available',
            'details': 'Please ensure matplotlib and pandas are installed. You can also run generate_churn_report.py directly.'
        }), 500
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate PDF: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to generate PDF report'
        }), 500
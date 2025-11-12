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
        
        # Filter out November 2024 (low data volume)
        df = df[df['year_month'] != '2024-11']
        
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
        
        # Keep only top 11 reasons, aggregate the rest into "Other"
        top_n = 11
        top_reasons = sorted_reasons[:top_n]
        other_reasons = sorted_reasons[top_n:] if len(sorted_reasons) > top_n else []
        
        # Aggregate data: combine non-top reasons into "Other"
        aggregated_data = []
        for month in months:
            month_data = {'month': month}
            month_total = int(monthly_totals[month])
            month_data['_total'] = month_total
            
            # Get data for this month
            month_df = grouped[grouped['year_month'] == month]
            
            # Add top reasons
            for reason in top_reasons:
                reason_data = month_df[month_df['augmented_churn_reason'] == reason]
                count_key = f'{reason}_count'
                if len(reason_data) > 0:
                    month_data[reason] = round(reason_data['percentage'].values[0], 2)
                    month_data[count_key] = int(reason_data['count'].values[0])
                else:
                    month_data[reason] = 0
                    month_data[count_key] = 0
            
            # Aggregate "Other" reasons
            other_count = 0
            other_percentage = 0
            for reason in other_reasons:
                reason_data = month_df[month_df['augmented_churn_reason'] == reason]
                if len(reason_data) > 0:
                    other_count += int(reason_data['count'].values[0])
                    other_percentage += reason_data['percentage'].values[0]
            
            # Add "Other" category
            if len(other_reasons) > 0:
                month_data['Other'] = round(other_percentage, 2)
                month_data['Other_count'] = other_count
            
            aggregated_data.append(month_data)
        
        # Create final reasons list with "Other" if needed
        final_reasons = top_reasons.copy()
        if len(other_reasons) > 0:
            final_reasons.append('Other')
            reason_totals['Other'] = sum(reason_totals[r] for r in other_reasons)
        
        return jsonify({
            'success': True,
            'data': aggregated_data,
            'reasons': final_reasons,
            'months': months,
            'reason_totals': {r: reason_totals[r] for r in final_reasons},
            'total_responses': int(len(df)),
            'other_reasons_count': len(other_reasons)
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


@survicate_bp.route('/generate-slides-report', methods=['POST'])
def generate_slides_report():
    """Generate and return a PowerPoint presentation of churn trends"""
    try:
        import sys
        import os
        
        # Get the path to the script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, '..', '..', '..', 'generate_churn_slides.py')
        
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'Slides generation script not found',
                'details': f'Expected script at: {script_path}'
            }), 404
        
        # Import and run the slides generation
        sys.path.insert(0, os.path.dirname(script_path))
        from generate_churn_slides import generate_churn_slides
        
        # Get CSV path
        csv_path = os.path.join(current_dir, '..', '..', '..', 'data', 
                                'survicate_cancelled_subscriptions_augmented.csv')
        
        # Generate PowerPoint in a temporary location
        import tempfile
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, 'churn_trends_slides.pptx')
        
        result = generate_churn_slides(csv_path=csv_path, output_path=output_path)
        
        if result and os.path.exists(result):
            from flask import send_file
            return send_file(
                result,
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                as_attachment=True,
                download_name='churn_trends_slides.pptx'
            )
        else:
            return jsonify({
                'error': 'Failed to generate PowerPoint',
                'details': 'PowerPoint generation completed but file not found'
            }), 500
    
    except ImportError as e:
        logger.error(f"Failed to import slides generation script: {str(e)}")
        return jsonify({
            'error': 'Slides generation dependencies not available',
            'details': 'Please ensure python-pptx, matplotlib, and pandas are installed.'
        }), 500
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate PowerPoint: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to generate PowerPoint presentation'
        }), 500


@survicate_bp.route('/question-trends', methods=['GET'])
def get_question_trends():
    """Get trends for specific survey questions by month (COUNTA of non-empty values)"""
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
        
        # Get question parameter
        question = request.args.get('question')
        if not question:
            return jsonify({
                'error': 'Question parameter required',
                'details': 'Specify question as Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, or Q11'
            }), 400
        
        # Read the CSV first to get actual column names
        df = pd.read_csv(csv_path)
        
        # Map question codes to search patterns (flexible matching)
        question_patterns = {
            'Q2': ['location pin', 'not match', 'dog'],
            'Q3': ['pet location pin', 'grayed out', 'inaccurate'],
            'Q4': ['collar', 'not sending feedback', 'dog not responding'],
            'Q5': ['screw in', 'contact tips', 'static feedback'],
            'Q6': ['battery life', 'charging', 'power issues'],
            'Q7': ['containment solution', 'purchase'],
            'Q8': ['engage', 'Learn training curriculum'],
            'Q9': ['main reason', 'didn\'t complete', 'Learn curriculum'],
            'Q10': ['contact', 'Customer Service', 'Dog Park'],
            'Q11': ['free session', 'trainer', 'collar effectively']
        }
        
        if question not in question_patterns:
            return jsonify({
                'error': 'Invalid question',
                'details': f'Valid questions: {", ".join(sorted(question_patterns.keys()))}'
            }), 400
        
        # Find the column that matches the pattern
        pattern = question_patterns[question]
        column_name = None
        
        # First try pattern matching
        for col in df.columns:
            col_lower = str(col).lower()
            # Check if all pattern words are in the column name
            if all(word.lower() in col_lower for word in pattern):
                # Also check if it starts with the question number
                if f'q#{question[1:]}' in col_lower or f'q{question[1:]}' in col_lower:
                    column_name = col
                    break
        
        # If pattern matching didn't work, try exact match
        if not column_name:
            # Look for columns that start with the question number
            for col in df.columns:
                col_str = str(col)
                if col_str.startswith(f'Q#{question[1:]}:') or col_str.startswith(f'Q{question[1:]}:'):
                    # For Q4, Q6, Q9, prefer the (Answer) version
                    if question in ['Q4', 'Q6', 'Q9']:
                        if '(Answer)' in col_str:
                            column_name = col
                            break
                    else:
                        column_name = col
                        break
        
        if not column_name:
            logger.error(f"Could not find column for question {question}. Available columns: {[c for c in df.columns if question[1:] in str(c)]}")
            return jsonify({
                'error': 'Column not found',
                'details': f'Could not find matching column for question {question}'
            }), 404
        
        # Filter out rows with missing year_month
        df = df[df['year_month'].notna()]
        
        # Filter out November 2024 (low data volume)
        df = df[df['year_month'] != '2024-11']
        
        if len(df) == 0:
            return jsonify({
                'error': 'No valid data found',
                'details': 'No rows with valid year_month'
            }), 400
        
        # Filter to only rows with responses to this question
        df_with_responses = df[df[column_name].notna() & (df[column_name].astype(str).str.strip() != '')].copy()
        
        if len(df_with_responses) == 0:
            return jsonify({
                'error': 'No responses found',
                'details': f'No responses found for question {question}'
            }), 400
        
        # Get unique answers
        df_with_responses['answer'] = df_with_responses[column_name].astype(str).str.strip()
        unique_answers = df_with_responses['answer'].unique().tolist()
        
        # Group by month and answer to get counts
        grouped = df_with_responses.groupby(['year_month', 'answer']).size().reset_index(name='count')
        
        # Get total responses per month (for this question only)
        monthly_totals = df_with_responses.groupby('year_month').size()
        
        # Get unique months
        months = sorted(df_with_responses['year_month'].unique())
        
        # Calculate total counts for each answer (for sorting)
        answer_totals = {}
        for answer in unique_answers:
            answer_totals[answer] = int(grouped[grouped['answer'] == answer]['count'].sum())
        
        # Sort answers by total count (descending) for consistent ordering
        sorted_answers = sorted(unique_answers, key=lambda x: answer_totals[x], reverse=True)
        
        # Format data for frontend - create array with month and all answer counts
        data = []
        for month in months:
            month_data = {'month': month}
            month_total = int(monthly_totals[month])
            month_df = grouped[grouped['year_month'] == month]
            
            for answer in sorted_answers:
                answer_data = month_df[month_df['answer'] == answer]
                if len(answer_data) > 0:
                    count = int(answer_data['count'].values[0])
                    month_data[answer] = count
                    month_data[f'{answer}_percentage'] = round((count / month_total) * 100, 2)
                else:
                    month_data[answer] = 0
                    month_data[f'{answer}_percentage'] = 0
            
            month_data['_total'] = month_total
            data.append(month_data)
        
        return jsonify({
            'success': True,
            'question': question,
            'question_text': column_name,
            'data': data,
            'answers': sorted_answers,
            'months': months,
            'total_responses': int(len(df_with_responses))
        })
    
    except Exception as e:
        import traceback
        logger.error(f"Failed to get question trends: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'details': 'Failed to process question trends data'
        }), 500
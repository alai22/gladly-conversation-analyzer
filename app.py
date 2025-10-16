#!/usr/bin/env python3
"""
Flask backend API for Gladly web interface
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
from claude_api_client import ClaudeAPIClient, ConversationAnalyzer

app = Flask(__name__)
CORS(app)

# Initialize clients
claude_client = None
conversation_analyzer = None

def initialize_clients():
    """Initialize Claude client and conversation analyzer"""
    global claude_client, conversation_analyzer
    try:
        claude_client = ClaudeAPIClient()
        conversation_analyzer = ConversationAnalyzer()
        return True
    except Exception as e:
        print(f"Error initializing clients: {e}")
        return False

@app.route('/')
def index():
    """Serve the React app"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#000000" />
        <meta name="description" content="Gladly Conversation Testing Interface" />
        <title>Gladly Conversation Tester</title>
    </head>
    <body>
        <noscript>You need to enable JavaScript to run this app.</noscript>
        <div id="root"></div>
    </body>
    </html>
    """)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'claude_initialized': claude_client is not None,
        'conversation_analyzer_initialized': conversation_analyzer is not None
    })

@app.route('/api/claude/chat', methods=['POST'])
def claude_chat():
    """Send message to Claude API"""
    try:
        data = request.get_json()
        message = data.get('message')
        model = data.get('model', 'claude-3-5-sonnet-20241022')
        max_tokens = data.get('max_tokens', 1000)
        system_prompt = data.get('system_prompt')
        stream = data.get('stream', False)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not claude_client:
            return jsonify({'error': 'Claude client not initialized'}), 500
        
        if stream:
            # For streaming, we'll collect all chunks and return them
            chunks = []
            for chunk in claude_client.stream_message(
                message=message,
                model=model,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            ):
                chunks.append(chunk)
            
            return jsonify({
                'success': True,
                'response': chunks,
                'streamed': True
            })
        else:
            response = claude_client.send_message(
                message=message,
                model=model,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
            
            return jsonify({
                'success': True,
                'response': response,
                'streamed': False
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/summary')
def conversations_summary():
    """Get conversation data summary"""
    try:
        if not conversation_analyzer:
            return jsonify({'error': 'Conversation analyzer not initialized'}), 500
        
        summary = conversation_analyzer.get_conversation_summary()
        return jsonify({
            'success': True,
            'summary': summary
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/search', methods=['POST'])
def conversations_search():
    """Search conversations"""
    try:
        data = request.get_json()
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if not conversation_analyzer:
            return jsonify({'error': 'Conversation analyzer not initialized'}), 500
        
        results = conversation_analyzer.semantic_search_conversations(query, limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/ask', methods=['POST'])
def conversations_ask():
    """Ask Claude about conversation data with detailed RAG process information"""
    try:
        data = request.get_json()
        question = data.get('question')
        model = data.get('model', 'claude-3-5-sonnet-20241022')
        max_tokens = data.get('max_tokens', 2000)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if not claude_client or not conversation_analyzer:
            return jsonify({'error': 'Clients not initialized'}), 500
        
        # Initialize RAG process tracking
        rag_process = {
            'steps': [],
            'plan': None,
            'retrieval_stats': {},
            'data_summary': {}
        }
        
        # Step 1: Query Planning - Use Claude to understand what data we need
        rag_process['steps'].append({
            'step': 1,
            'name': 'Query Planning',
            'description': 'Claude analyzes your question and creates a retrieval plan',
            'status': 'running'
        })
        
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
            planning_response = claude_client.send_message(
                message=query_planning_prompt,
                model=model,
                max_tokens=500
            )
            
            # Extract JSON from response
            planning_text = planning_response['content'][0]['text']
            import re
            json_match = re.search(r'\{.*\}', planning_text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # Fallback to basic plan
                plan = {
                    "search_terms": [question],
                    "content_types": ["CHAT_MESSAGE", "EMAIL", "CONVERSATION_NOTE"],
                    "time_filters": "all",
                    "analysis_focus": "general analysis",
                    "max_items": 100
                }
            
            rag_process['plan'] = plan
            rag_process['steps'][0]['status'] = 'completed'
            rag_process['steps'][0]['details'] = {
                'search_terms': plan['search_terms'],
                'content_types': plan['content_types'],
                'time_filters': plan['time_filters'],
                'analysis_focus': plan['analysis_focus'],
                'max_items': plan['max_items']
            }
        
        except Exception as e:
            print(f"Query planning failed, using fallback: {e}")
            plan = {
                "search_terms": [question],
                "content_types": ["CHAT_MESSAGE", "EMAIL", "CONVERSATION_NOTE"],
                "time_filters": "all",
                "analysis_focus": "general analysis",
                "max_items": 100
            }
            rag_process['plan'] = plan
            rag_process['steps'][0]['status'] = 'completed'
            rag_process['steps'][0]['details'] = plan
            rag_process['steps'][0]['warning'] = f"Planning failed, using fallback: {str(e)}"
        
        # Step 2: Data Retrieval - Get relevant conversations based on the plan
        rag_process['steps'].append({
            'step': 2,
            'name': 'Data Retrieval',
            'description': 'Semantic search retrieves relevant conversation data',
            'status': 'running'
        })
        
        relevant_data = []
        retrieval_stats = {
            'total_searched': 0,
            'by_content_type': {},
            'by_search_term': {},
            'filtered_out': 0
        }
        
        # Search using the planned terms with semantic search
        for term in plan['search_terms']:
            results = conversation_analyzer.semantic_search_conversations(term, limit=plan['max_items'] // len(plan['search_terms']))
            relevant_data.extend(results)
            retrieval_stats['by_search_term'][term] = len(results)
            retrieval_stats['total_searched'] += len(results)
        
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
        
        # Apply time filters if specified
        if plan['time_filters'] == "last_24_hours":
            relevant_data = conversation_analyzer.get_recent_conversations(24)
        elif plan['time_filters'] == "last_7_days":
            relevant_data = conversation_analyzer.get_recent_conversations(24 * 7)
        
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
        
        # Debug logging (commented out for production)
        # print(f"DEBUG: Total searched: {retrieval_stats['total_searched']}")
        # print(f"DEBUG: After filtering: {len(relevant_data)}")
        # print(f"DEBUG: Final unique count: {len(unique_data)}")
        # print(f"DEBUG: Content types in final data: {list(set(item.get('content', {}).get('type', 'Unknown') for item in unique_data))}")
        
        rag_process['retrieval_stats'] = retrieval_stats
        rag_process['steps'][1]['status'] = 'completed'
        rag_process['steps'][1]['details'] = retrieval_stats
        
        # Step 3: Data Analysis - Send the retrieved data to Claude for analysis
        rag_process['steps'].append({
            'step': 3,
            'name': 'Analysis',
            'description': 'Claude analyzes the retrieved data to answer your question',
            'status': 'running'
        })
        
        # Get conversation summary for context
        summary = conversation_analyzer.get_conversation_summary()
        
        # Format the conversation data for Claude (limit to first 50 items for performance)
        conversation_text = "Retrieved Conversation Data:\n\n"
        items_to_process = unique_data[:50]  # Limit to first 50 items for performance
        
        for i, item in enumerate(items_to_process, 1):
            content = item.get('content', {})
            timestamp = item.get('timestamp', 'No timestamp')
            content_type = content.get('type', 'Unknown type')
            customer_id = item.get('customerId', 'Unknown customer')
            conversation_id = item.get('conversationId', 'Unknown conversation')
            
            conversation_text += f"--- Item {i} ---\n"
            conversation_text += f"Type: {content_type}\n"
            conversation_text += f"Timestamp: {timestamp}\n"
            conversation_text += f"Customer: {customer_id}\n"
            conversation_text += f"Conversation: {conversation_id}\n"
            
            # Add content based on type (truncate long content)
            if 'content' in content:
                content_text = str(content['content'])
                if len(content_text) > 500:
                    content_text = content_text[:500] + "... [truncated]"
                conversation_text += f"Content: {content_text}\n"
            if 'subject' in content:
                conversation_text += f"Subject: {content['subject']}\n"
            if 'body' in content:
                body_text = str(content['body'])
                if len(body_text) > 500:
                    body_text = body_text[:500] + "... [truncated]"
                conversation_text += f"Body: {body_text}\n"
            
            conversation_text += "\n"
        
        if len(unique_data) > 50:
            conversation_text += f"\n[Note: Showing first 50 of {len(unique_data)} retrieved items for performance]\n"
        
        # Create a system prompt with conversation context
        system_prompt = f"""You are analyzing customer support conversation data. Here's a summary of the data:

{summary}

{conversation_text}

Analysis Focus: {plan['analysis_focus']}

Please analyze the conversation data and answer the question: "{question}"

Be specific and reference the actual conversation content when possible. Look for patterns, themes, and specific examples in the data. Provide detailed insights based on the retrieved conversations."""
        
        response = claude_client.send_message(
            message=question,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
        
        rag_process['steps'][2]['status'] = 'completed'
        rag_process['steps'][2]['details'] = {
            'tokens_used': response.get('usage', {}).get('output_tokens', 0),
            'model_used': model
        }
        
        # Create data summary
        content_types_found = list(set(item.get('content', {}).get('type', 'Unknown') for item in unique_data)) if unique_data else []
        
        date_range = {'earliest': 'Unknown', 'latest': 'Unknown'}
        if unique_data:
            timestamps = [item.get('timestamp', '') for item in unique_data if item.get('timestamp')]
            if timestamps:
                date_range = {
                    'earliest': min(timestamps),
                    'latest': max(timestamps)
                }
        
        rag_process['data_summary'] = {
            'total_conversations': len(conversation_analyzer.conversations),
            'retrieved_items': len(unique_data),
            'content_types_found': content_types_found,
            'date_range': date_range
        }
        
        return jsonify({
            'success': True,
            'response': response,
            'rag_process': rag_process,
            'data_retrieved': len(unique_data),
            'plan': plan
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Initializing Gladly Web Interface...")
    if initialize_clients():
        print("✅ Clients initialized successfully")
        print("🚀 Starting Flask server on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize clients. Please check your configuration.")
        print("Make sure you have:")
        print("1. Set your API key in config_local.py")
        print("2. Have conversation_items.jsonl file in the current directory")

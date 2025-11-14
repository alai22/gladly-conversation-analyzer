"""
Utility functions
"""

import json
import re
from typing import Dict, Any, Optional
from .pii_protection import create_pii_protector
from .config import Config


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object from text"""
    try:
        # Try to find JSON in the text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    return None


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "... [truncated]"


def format_conversation_for_claude(conversations: list, max_items: int = 50) -> str:
    """Format conversation data for Claude analysis with PII protection"""
    if not conversations:
        return "No conversation data was retrieved from the search. This could mean:\n- The search terms did not match any conversations\n- The conversations have not been loaded yet\n- The content type filters excluded all results\n\nPlease inform the user that no data was found and suggest they try different search terms or check if conversation data has been loaded."
    
    # Apply PII protection if enabled
    pii_config = Config.get_pii_config()
    if pii_config.get('redact_mode'):
        protector = create_pii_protector(pii_config)
        conversations = protector.sanitize_list(conversations, item_type='conversation')
    
    # Group items by conversation ID to show structure
    conversation_groups = {}
    for item in conversations:
        conv_id = item.get('conversationId', 'NO_CONVERSATION_ID')
        if conv_id not in conversation_groups:
            conversation_groups[conv_id] = []
        conversation_groups[conv_id].append(item)
    
    conversation_text = f"Retrieved Conversation Data: {len(conversations)} conversation items (messages, notes, events) found across {len(conversation_groups)} unique conversations\n\n"
    conversation_text += "Each item below is a message, email, note, or event within a customer support conversation:\n\n"
    
    items_to_process = conversations[:max_items]
    processed_conv_ids = set()
    
    for item in items_to_process:
        content = item.get('content', {})
        timestamp = item.get('timestamp', 'No timestamp')
        content_type = content.get('type', 'Unknown type')
        customer_id = item.get('customerId', 'Unknown customer')
        conversation_id = item.get('conversationId', 'Unknown conversation')
        item_id = item.get('id', 'Unknown item')
        
        # Show conversation grouping information
        if conversation_id not in processed_conv_ids:
            items_in_conv = len([i for i in conversations if i.get('conversationId') == conversation_id])
            conversation_text += f"\n{'='*60}\n"
            conversation_text += f"CONVERSATION: {conversation_id} (contains {items_in_conv} items)\n"
            conversation_text += f"{'='*60}\n\n"
            processed_conv_ids.add(conversation_id)
        
        # Use conversation ID as the primary identifier
        conversation_text += f"--- Message/Event Item (Item ID: {item_id}) ---\n"
        conversation_text += f"Conversation ID: {conversation_id}\n"
        conversation_text += f"Type: {content_type}\n"
        conversation_text += f"Timestamp: {timestamp}\n"
        conversation_text += f"Customer: {customer_id}\n"
        
        # Add content based on type (truncate long content)
        if 'content' in content:
            content_text = truncate_text(str(content['content']))
            conversation_text += f"Content: {content_text}\n"
        if 'subject' in content:
            conversation_text += f"Subject: {content['subject']}\n"
        if 'body' in content:
            body_text = truncate_text(str(content['body']))
            conversation_text += f"Body: {body_text}\n"
        
        conversation_text += "\n"
    
    if len(conversations) > max_items:
        conversation_text += f"\n[Note: Showing first {max_items} conversation items of {len(conversations)} total items across {len(conversation_groups)} conversations for performance]\n"
    
    return conversation_text


def create_rag_system_prompt(summary: str, conversation_text: str, plan: Dict[str, Any], question: str) -> str:
    """Create system prompt for RAG analysis"""
    return f"""You are analyzing customer support conversation data. 

DATA STRUCTURE:
Each "item" in the data represents a single message, event, or note within a customer support conversation. Multiple items belong to the same conversation (identified by conversationId). For example:
- A conversation might have multiple CHAT_MESSAGE items (back-and-forth messages)
- A conversation might have EMAIL items, CONVERSATION_NOTE items, and status changes
- All items with the same conversationId are part of the same customer conversation

Here's a summary of the entire dataset:

{summary}

Below are the retrieved conversation items (messages, notes, events) that are relevant to the question. These items ARE conversation data - each item is part of a customer conversation:

{conversation_text}

Analysis Focus: {plan.get('analysis_focus', 'general analysis')}

Please analyze the conversation data and answer the question: "{question}"

Be specific and reference the actual conversation content when possible. Look for patterns, themes, and specific examples in the data. Provide detailed insights based on the retrieved conversations.

IMPORTANT: Each item in the retrieved data IS part of a conversation. The items contain conversation messages, emails, notes, and events. When you see "items", understand that these are conversation messages/events grouped by conversationId.

IMPORTANT: When referencing specific conversations, ALWAYS use the Conversation ID (e.g., `abc123xyz`) instead of item numbers. Format conversation IDs using backticks for code formatting like this: `conversation-id-here`. This makes it easy for users to identify and access the specific conversations.

IMPORTANT: Format your response using proper Markdown formatting:
- Use **bold** for headings and important terms
- Use bullet points (- or *) for lists
- Use proper indentation for sub-items
- Use numbered lists (1., 2., 3.) for sequential items
- Use ## for main headings and ### for sub-headings
- Use `code formatting` for conversation IDs and specific terms when needed

Make your response well-structured and easy to read with clear visual hierarchy."""


def format_survey_for_claude(surveys: list, max_items: int = 50) -> str:
    """Format survey data for Claude analysis with PII protection"""
    if not surveys:
        return "No survey data was retrieved from the search. This could mean:\n- The search terms did not match any survey responses\n- The surveys have not been loaded yet\n\nPlease inform the user that no data was found and suggest they try different search terms or check if survey data has been loaded."
    
    # Apply PII protection if enabled
    pii_config = Config.get_pii_config()
    if pii_config.get('redact_mode'):
        protector = create_pii_protector(pii_config)
        surveys = protector.sanitize_list(surveys, item_type='survey')
    
    survey_text = f"Retrieved Survey Data: {len(surveys)} survey responses found\n\n"
    survey_text += "Each response below represents a customer's cancellation survey response:\n\n"
    
    items_to_process = surveys[:max_items]
    
    for item in items_to_process:
        response_uuid = item.get('response_uuid', 'Unknown')
        date_time = item.get('date_time', 'No timestamp')
        email = item.get('email', 'No email')
        user_id = item.get('user_id', 'No user ID')
        answers = item.get('answers', {})
        
        survey_text += f"\n{'='*60}\n"
        survey_text += f"SURVEY RESPONSE: {response_uuid}\n"
        survey_text += f"{'='*60}\n"
        survey_text += f"Date & Time: {date_time}\n"
        survey_text += f"Email: {email}\n"
        if user_id:
            survey_text += f"User ID: {user_id}\n"
        survey_text += "\nAnswers:\n"
        
        # Format each answer
        for question_key, answer_data in sorted(answers.items()):
            if isinstance(answer_data, dict):
                answer_value = answer_data.get('Answer') or answer_data.get('answer') or ''
                comment_value = answer_data.get('Comment') or answer_data.get('comment') or ''
                
                if answer_value or comment_value:
                    survey_text += f"  {question_key}:\n"
                    if answer_value:
                        answer_text = truncate_text(str(answer_value), max_length=300)
                        survey_text += f"    Answer: {answer_text}\n"
                    if comment_value:
                        comment_text = truncate_text(str(comment_value), max_length=300)
                        survey_text += f"    Comment: {comment_text}\n"
            else:
                answer_value = str(answer_data) if answer_data else ''
                if answer_value:
                    answer_text = truncate_text(str(answer_value), max_length=300)
                    survey_text += f"  {question_key}: {answer_text}\n"
        
        survey_text += "\n"
    
    if len(surveys) > max_items:
        survey_text += f"\n[Note: Showing first {max_items} survey responses of {len(surveys)} total for performance]\n"
    
    return survey_text


def create_survicate_rag_system_prompt(summary: str, survey_text: str, plan: Dict[str, Any], question: str) -> str:
    """Create system prompt for Survicate survey RAG analysis"""
    
    trend_instruction = ""
    if plan.get('trend_analysis', False):
        trend_instruction = """

TREND ANALYSIS:
This query requires trend analysis over time. Pay special attention to:
- How themes and issues change over the date range
- Comparing early vs. late responses
- Identifying patterns that emerge or fade over time
- Provide specific time-based insights and data points
"""
    
    return f"""You are analyzing customer cancellation survey data from Survicate. 

DATA STRUCTURE:
Each survey response represents a customer's feedback when cancelling their Halo Collar subscription. The surveys contain:
- Structured answers to questions (Q1-Q19) about cancellation reasons
- Open-ended comments providing additional context
- Timestamps showing when each response was submitted
- User identifiers (email, user_id) for tracking

Questions typically cover:
- Main cancellation reason (Q1)
- GPS/location accuracy issues (Q2, Q3)
- Feedback/correction issues (Q4, Q5)
- Battery and charging problems (Q6)
- Training curriculum engagement (Q8, Q9)
- Customer service experiences (Q10, Q11)
- Additional feedback (Q12)
- Dog characteristics (Q14-Q17)
- Purchase information (Q18)

Here's a summary of the entire dataset:

{summary}
{trend_instruction}
Below are the retrieved survey responses that are relevant to the question:

{survey_text}

Analysis Focus: {plan.get('analysis_focus', 'general analysis')}

Please analyze the survey data and answer the question: "{question}"

Be specific and reference actual survey responses when possible. Look for:
- Common themes and patterns across responses
- Frequency of specific issues or reasons
- Trends over time (if date information is available)
- Relationships between different questions
- Direct quotes from customer feedback

IMPORTANT: When referencing specific survey responses, use the Response UUID (e.g., `abc123xyz`) for identification. Format response UUIDs using backticks like this: `response-uuid-here`.

IMPORTANT: For trend analysis, clearly state the time periods being compared and provide specific counts or percentages.

IMPORTANT: Format your response using proper Markdown formatting:
- Use **bold** for headings and important terms
- Use bullet points (- or *) for lists
- Use proper indentation for sub-items
- Use numbered lists (1., 2., 3.) for sequential items
- Use ## for main headings and ### for sub-headings
- Use `code formatting` for response UUIDs and specific terms when needed
- Use tables when comparing data across time periods or categories

Make your response well-structured and easy to read with clear visual hierarchy."""
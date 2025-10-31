"""
Utility functions
"""

import json
import re
from typing import Dict, Any, Optional


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
    """Format conversation data for Claude analysis"""
    if not conversations:
        return "No conversation data was retrieved from the search. This could mean:\n- The search terms did not match any conversations\n- The conversations have not been loaded yet\n- The content type filters excluded all results\n\nPlease inform the user that no data was found and suggest they try different search terms or check if conversation data has been loaded."
    
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

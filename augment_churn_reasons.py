"""
Script to augment churn reason categorization by analyzing "Other" comments
and creating a hybrid categorization column.
"""

import csv
import os
import sys
import json
import re
from typing import Dict, Optional, List
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.config import Config
from backend.services.claude_service import ClaudeService
from backend.utils.logging import get_logger

logger = get_logger('augment_churn_reasons')

# Category name normalization mapping
# Maps original category names to preferred normalized names
# This allows consolidating similar categories for easier grouping
CATEGORY_NORMALIZATION_MAP = {
    'Purchased another containment solution': 'Found Alternative Solution',
    # GPS/Location Issues - combine specific case into broader category
    'The location pin does not match where my dog is': 'GPS and Location Accuracy Issues',
    # Feedback Issues - combine specific case into broader category
    'Collar sends feedback at unexpected times': 'Feedback Timing / Response Delay Issues',
    # Add more mappings here as needed
    # Example:
    # 'Original Category Name': 'Preferred Category Name',
}

def normalize_category_name(category: str) -> str:
    """
    Normalize a category name using the mapping.
    Returns the normalized name if a mapping exists, otherwise returns the original.
    """
    return CATEGORY_NORMALIZATION_MAP.get(category, category)

# Category mapping for "Other" comments
OTHER_CATEGORIES = {
    'life_situation_change': {
        'keywords': ['moved', 'moving', 'relocated', 'temporary', 'seasonal', 'winter', 'summer', 'not using right now', 'pause', 'staying somewhere', 'fenced yard', 'later date', 'postpone'],
        'mapped_reason': 'Life Situation Change / Temporary Circumstance'
    },
    'low_usage': {
        'keywords': ["don't use", "don't use", 'not using', 'hardly use', 'rarely use', 'not worth', 'not using it', "don't use it", 'not worth paying', 'not using anymore'],
        'mapped_reason': 'Low Usage / Not Worth Monthly Fee'
    },
    'product_complexity': {
        'keywords': ['complicated', 'complex', 'too difficult', 'time commitment', 'too much work', 'hard to use', 'too cumbersome', 'too much time'],
        'mapped_reason': 'Product Too Complex / Time Consuming'
    },
    'gps_connectivity': {
        'keywords': ['gps', 'connectivity', 'signal', 'connection', 'location pin', 'tracking', 'accuracy', 'pin does not match', 'pin is not correct'],
        'mapped_reason': 'GPS and Location Accuracy Issues'
    },
    'customer_service': {
        'keywords': ['customer service', 'support', 'no response', 'contacted', 'help', 'assistance', 'unresponsive', 'email', 'reimbursed', 'reimbursement'],
        'mapped_reason': 'Customer Service / Support Issues'
    },
    'environment_suitability': {
        'keywords': ['trees', 'remote', 'cell service', 'signal', "doesn't work", "doesn't work", "won't work", "won't work", 'not suitable', 'small yard', 'cabin', 'boundary line'],
        'mapped_reason': 'Environment / Location Not Suitable'
    },
    'found_alternative': {
        'keywords': ['fence', 'built a fence', 'another solution', 'alternative', 'competitor', 'other product', 'temporary fence'],
        'mapped_reason': 'Found Alternative Solution'
    },
    'lost_item': {
        'keywords': ['lost', 'missing', 'replacement', "don't want to invest", "don't want to invest", 'another collar', 'invest in another'],
        'mapped_reason': 'Lost Item / Unwilling to Replace'
    },
    'hardware_reliability': {
        'keywords': ['pins', 'collar fell apart', 'hardware', 'component', 'broke', 'broken', 'defective', 'pins coming out', 'charger', 'update'],
        'mapped_reason': 'Hardware Reliability Issues'
    },
    'training_success': {
        'keywords': ['dog trained', 'no longer need', "doesn't need", "doesn't need", 'trained well', 'matured', 'dog knows boundaries', 'stays within'],
        'mapped_reason': 'Training Successful / No Longer Needed'
    },
    'subscription_management': {
        'keywords': ['password', 'account', 'subscription', 'pause', 'cancel', 'billing', 'change password'],
        'mapped_reason': 'Subscription / Account Management Issues'
    },
    'general_product_failure': {
        'keywords': ['useless', 'garbage', 'disappointment', 'failure', "doesn't work", "doesn't work", 'terrible', 'waste of money', 'huge disappointment'],
        'mapped_reason': 'General Product Failure / Dissatisfaction'
    },
    'feedback_timing': {
        'keywords': ['late', 'slow', 'delayed', 'emergency feedback', 'fence response', 'response time', 'timing'],
        'mapped_reason': 'Feedback Timing / Response Delay Issues'
    }
}

def extract_json_array_from_text(text: str) -> Optional[List[str]]:
    """Extract JSON array from text"""
    try:
        # Try to find JSON array in the text
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    return None

def categorize_other_comment_batch(comments: List[str], claude_service: ClaudeService) -> List[str]:
    """
    Categorize multiple comments in a single Claude API call.
    Returns list of categories in same order as input comments.
    """
    if not comments:
        return []
    
    # Build category list for reference
    valid_categories = [c['mapped_reason'] for c in OTHER_CATEGORIES.values()] + ['Other (please specify)']
    category_list = '\n'.join([f'  "{cat}"' for cat in valid_categories])
    
    batch_prompt = f"""You must categorize exactly {len(comments)} customer cancellation comments.

CRITICAL REQUIREMENTS:
1. Return EXACTLY {len(comments)} categories (one per comment)
2. Use ONLY the exact category names from the list below
3. Return ONLY a JSON array, no explanations or other text
4. Categories must be in the same order as the comments (1-{len(comments)})

VALID CATEGORIES (use exact spelling):
{category_list}

COMMENTS TO CATEGORIZE:
{chr(10).join(f"{i+1}. {json.dumps(comment)}" for i, comment in enumerate(comments))}

RESPONSE FORMAT:
Return ONLY this JSON array format (copy the structure exactly):
["Category Name 1", "Category Name 2", "Category Name 3", ...]

Do not include any text before or after the JSON array. Do not explain your choices."""

    try:
        response = claude_service.send_message(
            message=batch_prompt,
            model=Config.CLAUDE_MODEL,
            max_tokens=max(1000, 100 * len(comments))  # More tokens: 100 per comment minimum
        )
        
        # More robust JSON extraction
        content = response.content.strip()
        
        # Try multiple extraction strategies
        categories = None
        
        # Strategy 1: Direct JSON array match
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            try:
                categories = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Strategy 2: Look for array-like structure with quotes
        if not categories or not isinstance(categories, list):
            # Try to find all quoted strings in order
            quoted_strings = re.findall(r'"([^"]+)"', content)
            if len(quoted_strings) >= len(comments):
                # Filter to only valid categories
                categories = []
                for qs in quoted_strings:
                    if qs in valid_categories:
                        categories.append(qs)
                    elif len(categories) < len(comments):
                        # If we're building the list and this doesn't match, might be a category name
                        # Try fuzzy matching
                        matched = False
                        for valid_cat in valid_categories:
                            if valid_cat.lower() == qs.lower() or valid_cat.replace(' / ', '/').lower() == qs.replace(' / ', '/').lower():
                                categories.append(valid_cat)
                                matched = True
                                break
                        if not matched and len(categories) < len(comments):
                            categories.append('Other (please specify)')
        
        # Strategy 3: Fallback - try to parse as JSON directly
        if not categories or not isinstance(categories, list):
            try:
                categories = json.loads(content)
            except json.JSONDecodeError:
                pass
        
        # Validate and fix length
        if isinstance(categories, list):
            # If we got fewer categories, pad with "Other"
            while len(categories) < len(comments):
                categories.append('Other (please specify)')
            # If we got more, truncate
            categories = categories[:len(comments)]
            
            # Validate each category
            validated_categories = []
            for cat in categories:
                cat_str = str(cat).strip().strip('"').strip("'")
                
                # Exact match
                if cat_str in valid_categories:
                    validated_categories.append(cat_str)
                else:
                    # Try fuzzy matching for common variations
                    matched = False
                    for valid_cat in valid_categories:
                        # Case-insensitive match
                        if valid_cat.lower() == cat_str.lower():
                            validated_categories.append(valid_cat)
                            matched = True
                            break
                        # Handle variations like "Too Complex / Time Consuming" vs "Product Too Complex / Time Consuming"
                        if 'too complex' in cat_str.lower() and 'too complex' in valid_cat.lower():
                            validated_categories.append(valid_cat)
                            matched = True
                            break
                        # Handle "Not Able to Use" -> might be "General Product Failure / Dissatisfaction"
                        if 'not able to use' in cat_str.lower() or 'unable to use' in cat_str.lower():
                            validated_categories.append('General Product Failure / Dissatisfaction')
                            matched = True
                            break
                        # Handle "Just Isn't Necessary" -> might be "Low Usage / Not Worth Monthly Fee"
                        if 'not necessary' in cat_str.lower() or "isn't necessary" in cat_str.lower():
                            validated_categories.append('Low Usage / Not Worth Monthly Fee')
                            matched = True
                            break
                        # Handle "Never Used / Unboxed" -> might be "Low Usage / Not Worth Monthly Fee"
                        if 'never used' in cat_str.lower() or 'unboxed' in cat_str.lower():
                            validated_categories.append('Low Usage / Not Worth Monthly Fee')
                            matched = True
                            break
                        # Handle "Financial Issues" -> might be "Low Usage / Not Worth Monthly Fee"
                        if 'financial' in cat_str.lower():
                            validated_categories.append('Low Usage / Not Worth Monthly Fee')
                            matched = True
                            break
                    
                    if not matched:
                        logger.warning(f"Claude returned invalid category: {cat_str}, using 'Other (please specify)'")
                        validated_categories.append('Other (please specify)')
            
            return validated_categories
        else:
            logger.warning(f"Claude batch response format invalid. Could not parse JSON array. Response: {content[:200]}")
            return ['Other (please specify)'] * len(comments)
            
    except Exception as e:
        logger.warning(f"Claude batch categorization failed: {e}")
        return ['Other (please specify)'] * len(comments)

def categorize_other_comment(comment: str, claude_service: Optional[ClaudeService] = None) -> str:
    """
    Categorize an "Other" comment into a churn reason.
    Uses keyword matching first, then falls back to Claude if available.
    """
    if not comment or not comment.strip():
        return 'Other (please specify)'  # Keep original if no comment
    
    comment_lower = comment.lower()
    
    # Try keyword matching first (faster, cheaper)
    for category, config in OTHER_CATEGORIES.items():
        if any(keyword in comment_lower for keyword in config['keywords']):
            return config['mapped_reason']
    
    # If keyword matching fails and Claude is available, use it
    if claude_service:
        try:
            categorization_prompt = f"""Categorize this customer cancellation reason comment into one of these categories:

Categories:
1. "Life Situation Change / Temporary Circumstance" - moved, temporary housing, seasonal usage, fenced yard temporarily
2. "Low Usage / Not Worth Monthly Fee" - don't use it enough, not worth the cost
3. "Product Too Complex / Time Consuming" - too complicated, too much time required
4. "GPS and Location Accuracy Issues" - GPS problems, location tracking issues, pin accuracy
5. "Customer Service / Support Issues" - poor support, unresponsive service, reimbursement issues
6. "Environment / Location Not Suitable" - trees, remote location, cell service issues, small yard
7. "Found Alternative Solution" - built a fence, bought competitor product, temporary fence
8. "Lost Item / Unwilling to Replace" - lost collar, don't want to buy another
9. "Hardware Reliability Issues" - pins falling out, hardware failures, charger issues
10. "Training Successful / No Longer Needed" - dog trained, no longer needs collar
11. "Subscription / Account Management Issues" - password, billing, account problems
12. "Feedback Timing / Response Delay Issues" - slow feedback, delayed corrections
13. "General Product Failure / Dissatisfaction" - product doesn't work, general disappointment
14. "Other (please specify)" - doesn't fit any category

Comment: "{comment}"

Respond with ONLY the category name (exact match from the list above)."""
            
            response = claude_service.send_message(
                message=categorization_prompt,
                model=Config.CLAUDE_MODEL,
                max_tokens=100
            )
            
            category = response.content.strip().strip('"').strip("'")
            
            # Validate it's one of our categories
            valid_categories = [c['mapped_reason'] for c in OTHER_CATEGORIES.values()] + ['Other (please specify)']
            if category in valid_categories:
                return category
            
            logger.warning(f"Claude returned unexpected category: {category}, using 'Other (please specify)'")
            return 'Other (please specify)'
            
        except Exception as e:
            logger.warning(f"Claude categorization failed: {e}, using 'Other (please specify)'")
    
    # Fallback: keep as "Other" if we can't categorize
    return 'Other (please specify)'


# Removed duplicate functions - using the ones defined earlier in the file

def augment_csv(input_path: str, output_path: str, use_claude: bool = True):
    """
    Process CSV and create augmented version with hybrid churn reason column.

    Args:
        input_path: Path to input CSV file (should be cleaned CSV with proper headers)
        output_path: Path to output CSV file with augmented column
        use_claude: Whether to use Claude for categorization (slower but more accurate)
    """
    claude_service = None
    if use_claude:
        try:
            claude_service = ClaudeService()
            logger.info("Claude service initialized for categorization")
        except Exception as e:
            logger.warning(f"Could not initialize Claude service: {e}. Using keyword matching only.")
            use_claude = False

    # Read input CSV - should be cleaned CSV with proper headers
    logger.info(f"Reading CSV from: {input_path}")

    # Read with DictReader - cleaned CSV has single header row
    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    # Add new columns
    if 'augmented_churn_reason' not in fieldnames:
        fieldnames = fieldnames + ['augmented_churn_reason']
    if 'categorization_method' not in fieldnames:
        fieldnames = fieldnames + ['categorization_method']
    if 'year_month' not in fieldnames:
        fieldnames = fieldnames + ['year_month']

    # Find Q1 columns - cleaned CSV has explicit (Answer) and (Comment) in headers
    q1_answer_col = None
    q1_comment_col = None

    # Find Q1 Answer column (has "Q#1:" and "main reason" and "(Answer)" in it)
    for col in fieldnames:
        if 'Q#1' in col and 'main reason' in col.lower() and '(Answer)' in col:
            q1_answer_col = col
            break

    # Find Q1 Comment column (has "Q#1:" and "main reason" and "(Comment)" in it)
    for col in fieldnames:
        if 'Q#1' in col and 'main reason' in col.lower() and '(Comment)' in col:
            q1_comment_col = col
            break

    if not q1_answer_col:
        raise ValueError("Could not find Q1 Answer column. Make sure you're using the cleaned CSV with proper headers.")

    if not q1_comment_col:
        raise ValueError("Could not find Q1 Comment column. Make sure you're using the cleaned CSV with proper headers.")

    logger.info(f"Processing {len(rows)} rows")
    logger.info(f"Q1 Answer column: {q1_answer_col}")
    logger.info(f"Q1 Comment column: {q1_comment_col}")
    
    # Print initial status
    print(f"\n{'='*60}")
    print(f"Processing {len(rows):,} survey responses...")
    print(f"{'='*60}\n")
    
    # Process each row - first pass: keyword matching
    categorized_count = 0
    other_count = 0
    keyword_matched = 0
    claude_categorized = 0
    
    # Collect comments that need Claude categorization
    claude_queue = []  # List of (row_index, comment) tuples
    
    # Progress tracking
    import time
    start_time = time.time()
    # Less frequent logging for Phase 1 since keyword matching is fast
    # Log at 0%, 25%, 50%, 75%, and 100% only
    log_points = [0, 0.25, 0.5, 0.75, 1.0]
    logged_milestones = set()  # Track which milestones we've already logged
    
    print("Phase 1: Keyword matching...")
    for i, row in enumerate(rows):
        q1_answer = row.get(q1_answer_col, '').strip()

        # Get comment from the Q1 Comment column (cleaned CSV has proper header)
        q1_comment = row.get(q1_comment_col, '').strip() if q1_comment_col else ''
        
        # Extract year-month from "Date & Time (UTC)" column
        date_time_str = row.get('Date & Time (UTC)', '').strip()
        year_month = ''
        if date_time_str:
            try:
                # Try parsing common date formats
                # Format: "2024-11-25 19:05:23" or "2024-11-25T19:05:23" or "2024-11-25"
                date_obj = None
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
                    try:
                        date_obj = datetime.strptime(date_time_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj:
                    year_month = date_obj.strftime('%Y-%m')
                else:
                    # Fallback: try to extract YYYY-MM pattern
                    match = re.search(r'(\d{4})-(\d{2})', date_time_str)
                    if match:
                        year_month = f"{match.group(1)}-{match.group(2)}"
            except Exception as e:
                logger.debug(f"Failed to parse date '{date_time_str}': {e}")
                year_month = ''
        
        row['year_month'] = year_month

        # Progress logging - only at key milestones (25%, 50%, 75%, 100%)
        progress_pct = (i + 1) / len(rows)
        # Check if we've crossed a milestone we haven't logged yet
        for point in log_points:
            if point not in logged_milestones and progress_pct >= point:
                logged_milestones.add(point)
                elapsed = time.time() - start_time
                if point == 0:
                    print(f"Starting processing...")
                else:
                    print(f"Progress: {i+1:,}/{len(rows):,} ({progress_pct*100:.1f}%) | "
                          f"Other: {other_count:,} | Keyword matched: {keyword_matched:,} | "
                          f"Queued for Claude: {len(claude_queue):,}")
                break  # Only log once per milestone
        
        # Debug: log first few "Other" comments to verify reading
        if q1_answer.lower() == 'other (please specify)' and i < 5:
            print(f"  Sample 'Other' response {i+1}: Comment='{q1_comment[:60]}...' (len={len(q1_comment)})")
        
        # Determine augmented reason and categorization method
        if q1_answer.lower() == 'other (please specify)':
            other_count += 1
            if q1_comment:
                # Try keyword matching first
                original_category = categorize_other_comment(q1_comment, None)
                if original_category != 'Other (please specify)':
                    keyword_matched += 1
                    augmented_reason = original_category
                    categorization_method = 'keyword'
                    categorized_count += 1
                    if categorized_count <= 5:  # Show first 5 categorizations
                        print(f"  [OK] Keyword matched: '{q1_comment[:60]}...' -> '{augmented_reason}'")
                elif use_claude and claude_service:
                    # Queue for batch Claude processing
                    claude_queue.append((i, q1_comment))
                    augmented_reason = None  # Will be set in batch processing
                    categorization_method = None  # Will be set in batch processing
                else:
                    augmented_reason = 'Other (please specify)'
                    categorization_method = 'uncategorized'
            else:
                augmented_reason = 'Other (please specify)'
                categorization_method = 'uncategorized'
        else:
            # Use original answer for non-"Other" responses
            # Normalize the original answer as well (e.g., "Purchased another containment solution" -> "Found Alternative Solution")
            original_answer = q1_answer if q1_answer else 'Other (please specify)'
            augmented_reason = normalize_category_name(original_answer)
            categorization_method = 'original'
        
        # Set augmented reason and method (or None if queued for Claude)
        if augmented_reason is not None:
            # Normalize category name using mapping (already normalized above, but keeping for consistency)
            normalized_reason = normalize_category_name(augmented_reason)
            row['augmented_churn_reason'] = normalized_reason
            row['categorization_method'] = categorization_method
    
    # Phase 2: Batch Claude categorization
    if claude_queue and use_claude and claude_service:
        print(f"\n{'='*60}")
        print(f"Phase 2: Claude batch categorization")
        print(f"{'='*60}")
        print(f"Processing {len(claude_queue)} comments in batches...\n")
        
        BATCH_SIZE = 20  # Process 20 comments per API call
        total_batches = (len(claude_queue) + BATCH_SIZE - 1) // BATCH_SIZE
        
        batch_start_time = time.time()
        for batch_num in range(total_batches):
            batch_start = batch_num * BATCH_SIZE
            batch_end = min(batch_start + BATCH_SIZE, len(claude_queue))
            batch_items = claude_queue[batch_start:batch_end]
            
            batch_indices = [idx for idx, _ in batch_items]
            batch_comments = [comment for _, comment in batch_items]
            
            elapsed = time.time() - batch_start_time
            rate = (batch_num * BATCH_SIZE) / elapsed if elapsed > 0 else 0
            remaining = (len(claude_queue) - batch_num * BATCH_SIZE) / rate if rate > 0 else 0
            
            print(f"Batch {batch_num + 1}/{total_batches}: Processing {len(batch_comments)} comments...", end=' ', flush=True)
            
            try:
                batch_categories = categorize_other_comment_batch(batch_comments, claude_service)
                
                # Apply categories back to rows
                for j, category in enumerate(batch_categories):
                    row_idx = batch_indices[j]
                    # Normalize category name using mapping
                    normalized_category = normalize_category_name(category)
                    rows[row_idx]['augmented_churn_reason'] = normalized_category
                    rows[row_idx]['categorization_method'] = 'llm'  # All Claude-processed items are marked as 'llm'
                    
                    if category != 'Other (please specify)':
                        claude_categorized += 1
                        categorized_count += 1
                        if claude_categorized <= 5:  # Show first 5 Claude categorizations
                            print(f"\n  [OK] Claude categorized: '{batch_comments[j][:60]}...' -> '{category}'")
                
                print(f"✓ ({claude_categorized}/{len(claude_queue)} categorized, ETA: {remaining:.0f}s)")
                
            except Exception as e:
                logger.error(f"Batch {batch_num + 1} failed: {e}")
                # Fallback: set all to "Other" with method "llm_failed"
                for row_idx in batch_indices:
                    rows[row_idx]['augmented_churn_reason'] = 'Other (please specify)'
                    rows[row_idx]['categorization_method'] = 'llm_failed'
                print(f"✗ (fallback to 'Other')")
        
        print(f"\n✓ Batch processing complete: {claude_categorized} comments categorized by Claude\n")
    elif claude_queue:
        # Claude was requested but service not available - set all to "Other"
        print(f"\nWarning: {len(claude_queue)} comments queued for Claude but service not available. Setting to 'Other (please specify)'.")
        for row_idx, _ in claude_queue:
            rows[row_idx]['augmented_churn_reason'] = 'Other (please specify)'
            rows[row_idx]['categorization_method'] = 'uncategorized'
    
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"{'='*60}")
    print(f"Total rows processed: {len(rows):,}")
    print(f"Time elapsed: {total_time:.1f}s")
    print(f"\nCategorization Summary:")
    print(f"  - 'Other' responses found: {other_count:,}")
    if other_count > 0:
        print(f"  - Successfully categorized: {categorized_count:,} ({categorized_count/other_count*100:.1f}% of 'Other' responses)")
        print(f"    • Keyword matching: {keyword_matched:,}")
        if use_claude:
            print(f"    • Claude categorization: {claude_categorized:,}")
        print(f"  - Remaining uncategorized: {other_count - categorized_count:,}")
    else:
        print(f"  - No 'Other' responses found")
    
    logger.info(f"\nProcessing complete!")
    logger.info(f"Total rows processed: {len(rows)}")
    logger.info(f"Found {other_count} 'Other' responses")
    logger.info(f"Successfully categorized {categorized_count} of {other_count} 'Other' responses")
    logger.info(f"  - Keyword matched: {keyword_matched}")
    logger.info(f"  - Claude categorized: {claude_categorized}")
    logger.info(f"Uncategorized: {other_count - categorized_count}")
    
    # Write output CSV
    print(f"\nWriting augmented CSV to: {output_path}")
    logger.info(f"\nWriting augmented CSV to: {output_path}")
    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"[OK] Augmented CSV written successfully!")
    logger.info(f"Augmented CSV written successfully!")
    
    # Print summary statistics
    augmented_stats = {}
    for row in rows:
        reason = row.get('augmented_churn_reason', 'Unknown')
        augmented_stats[reason] = augmented_stats.get(reason, 0) + 1
    
    logger.info("\n" + "="*60)
    logger.info("Augmented Churn Reason Distribution:")
    logger.info("="*60)
    for reason, count in sorted(augmented_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(rows) * 100
        logger.info(f"  {reason}: {count} ({percentage:.1f}%)")
    
    return augmented_stats

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Augment Survicate survey CSV with categorized churn reasons')
    parser.add_argument('--input', '-i', default='data/survicate_cancelled_subscriptions_cleaned.csv',
                       help='Input CSV file path (should be cleaned CSV with proper headers)')
    parser.add_argument('--output', '-o', default='data/survicate_cancelled_subscriptions_augmented.csv',
                       help='Output CSV file path')
    parser.add_argument('--no-claude', action='store_true',
                       help='Use only keyword matching (faster, no API calls)')
    
    args = parser.parse_args()
    
    augment_csv(
        input_path=args.input,
        output_path=args.output,
        use_claude=not args.no_claude
    )


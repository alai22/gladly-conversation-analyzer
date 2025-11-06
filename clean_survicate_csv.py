"""
Clean Survicate CSV by merging two header rows into one proper header row.
This makes the CSV easier to work with in standard CSV readers.
"""
import csv
import sys
import os
from typing import List, Tuple

def clean_survicate_csv(input_path: str, output_path: str):
    """
    Clean Survicate CSV with two header rows into a single header row.
    
    Row 1: Question headers (e.g., "Q#1: What was the main reason...")
    Row 2: Answer/Comment labels (e.g., "Answer", "Comment", or empty)
    
    Output: Single header row with combined names like:
    - "Q#1: What was the main reason... (Answer)"
    - "Q#1: What was the main reason... (Comment)"
    """
    print(f"Reading CSV from: {input_path}")
    
    # Read raw CSV
    with open(input_path, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header_row1 = next(reader)  # Question headers
        header_row2 = next(reader)   # Answer/Comment labels
        data_rows = list(reader)
    
    print(f"Found {len(data_rows)} data rows")
    print(f"Header row 1 has {len(header_row1)} columns")
    print(f"Header row 2 has {len(header_row2)} columns")
    
    # Create cleaned headers
    cleaned_headers = []
    i = 0
    
    while i < len(header_row1):
        question_header = header_row1[i].strip() if i < len(header_row1) else ''
        label = header_row2[i].strip() if i < len(header_row2) else ''
        
        if question_header:
            # This is a question column
            if label and label.lower() in ['answer', 'comment', 'insight', 'action']:
                # This question has a label - create combined header
                cleaned_headers.append(f"{question_header} ({label})")
                i += 1
            else:
                # Question without a label, or label is empty
                # Check if next column is a comment column
                if i + 1 < len(header_row2) and header_row2[i + 1].strip().lower() == 'comment':
                    # Current column is Answer, next is Comment
                    cleaned_headers.append(f"{question_header} (Answer)")
                    i += 1
                    # Add comment column
                    cleaned_headers.append(f"{question_header} (Comment)")
                    i += 1
                else:
                    # Just the question header
                    cleaned_headers.append(question_header)
                    i += 1
        else:
            # Empty header - likely a comment column for previous question
            if label and label.lower() == 'comment':
                # This is a comment column - we should have handled it above
                # But if we're here, the previous column didn't have a label
                # So this comment belongs to the previous question
                if cleaned_headers:
                    # Update previous header to indicate it's an Answer
                    prev_header = cleaned_headers[-1]
                    if '(Answer)' not in prev_header and '(Comment)' not in prev_header:
                        cleaned_headers[-1] = f"{prev_header} (Answer)"
                    cleaned_headers.append(f"{prev_header.replace(' (Answer)', '')} (Comment)")
                else:
                    cleaned_headers.append(f"Comment_{i}")
                i += 1
            else:
                # Truly empty column - use generic name
                cleaned_headers.append(f"Column_{i}")
                i += 1
    
    # Ensure we have headers for all columns
    max_cols = max(len(header_row1), len(header_row2), 
                   max((len(row) for row in data_rows), default=0))
    
    while len(cleaned_headers) < max_cols:
        cleaned_headers.append(f"Column_{len(cleaned_headers)}")
    
    print(f"Created {len(cleaned_headers)} cleaned headers")
    
    # Verify data rows have consistent column count
    for i, row in enumerate(data_rows):
        if len(row) != len(cleaned_headers):
            # Pad or truncate row to match header count
            if len(row) < len(cleaned_headers):
                row.extend([''] * (len(cleaned_headers) - len(row)))
            else:
                row = row[:len(cleaned_headers)]
            data_rows[i] = row
    
    # Write cleaned CSV
    print(f"Writing cleaned CSV to: {output_path}")
    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(cleaned_headers)
        writer.writerows(data_rows)
    
    print(f"Successfully cleaned CSV: {len(data_rows)} rows written")
    
    # Print sample of cleaned headers
    print("\nSample cleaned headers:")
    for i, header in enumerate(cleaned_headers[:15]):
        # Use repr to avoid encoding issues
        header_preview = repr(header[:60]) if len(header) > 60 else repr(header)
        print(f"  Column {i}: {header_preview}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean Survicate CSV headers")
    parser.add_argument('--input', '-i', type=str, 
                       default='data/survicate_cancelled_subscriptions.csv',
                       help='Input CSV file path')
    parser.add_argument('--output', '-o', type=str,
                       default='data/survicate_cancelled_subscriptions_cleaned.csv',
                       help='Output CSV file path')
    args = parser.parse_args()
    
    clean_survicate_csv(args.input, args.output)


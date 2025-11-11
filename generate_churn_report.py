"""
Generate a PDF report with stacked bar chart of churn reasons over time
from the augmented Survicate cancelled subscriptions data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from collections import OrderedDict
import os
import sys

def generate_churn_report(csv_path='data/survicate_cancelled_subscriptions_augmented.csv', 
                          output_path='churn_reasons_report.pdf'):
    """
    Generate a PDF report with stacked bar chart of churn reasons over time
    
    Args:
        csv_path: Path to the augmented CSV file
        output_path: Path where the PDF will be saved
    """
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print(f"Current working directory: {os.getcwd()}")
        return None
    
    print(f"Reading data from: {csv_path}")
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    print(f"Total rows: {len(df)}")
    
    # Filter out rows with missing data
    df = df[df['augmented_churn_reason'].notna() & df['year_month'].notna()]
    
    print(f"Rows with valid churn reason and year_month: {len(df)}")
    
    if len(df) == 0:
        print("Error: No valid data found after filtering")
        return None
    
    # Group by year_month and augmented_churn_reason
    grouped = df.groupby(['year_month', 'augmented_churn_reason']).size().reset_index(name='count')
    
    # Calculate percentages for each month
    monthly_totals = df.groupby('year_month').size()
    grouped['percentage'] = grouped.apply(
        lambda row: (row['count'] / monthly_totals[row['year_month']]) * 100, 
        axis=1
    )
    
    # Pivot to get months as columns and reasons as rows
    pivot_data = grouped.pivot(index='augmented_churn_reason', columns='year_month', values='percentage').fillna(0)
    
    # Sort months chronologically
    months = sorted(pivot_data.columns)
    pivot_data = pivot_data[months]
    
    # Sort reasons by total percentage (descending) to keep largest on top
    reason_totals = pivot_data.sum(axis=1).sort_values(ascending=False)
    pivot_data = pivot_data.loc[reason_totals.index]
    
    print(f"Found {len(pivot_data)} unique churn reasons across {len(months)} months")
    
    # Google Sheets-style color palette - light, vibrant, and easy to distinguish
    # These colors are bright, have good contrast, and are colorblind-friendly
    colors = [
        '#4285F4',  # Google Blue
        '#EA4335',  # Google Red
        '#FBBC04',  # Google Yellow
        '#34A853',  # Google Green
        '#FF6D01',  # Bright Orange
        '#9334E6',  # Bright Purple
        '#00ACC1',  # Cyan
        '#FF5252',  # Light Red
        '#66BB6A',  # Light Green
        '#42A5F5',  # Light Blue
        '#AB47BC',  # Light Purple
        '#FFA726',  # Light Orange
        '#26A69A',  # Teal
        '#EF5350',  # Coral
        '#5C6BC0',  # Indigo
        '#FFCA28',  # Amber
        '#26C6DA',  # Light Cyan
        '#EC407A',  # Pink
        '#7E57C2',  # Deep Purple
        '#78909C',  # Blue Grey
    ]
    
    # If we need more colors, use a light, vibrant colormap
    import matplotlib.colors as mcolors
    import numpy as np
    
    if len(pivot_data) > len(colors):
        # Use 'Pastel1' or 'Set3' for additional light, vibrant colors
        cmap = plt.cm.get_cmap('Pastel1')
        additional_colors = [mcolors.to_hex(cmap(i)) for i in np.linspace(0, 1, len(pivot_data) - len(colors))]
        colors.extend(additional_colors)
    
    # Create the figure
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Create stacked bar chart with vibrant, light styling
    bottom = None
    bars = []
    for i, (reason, row) in enumerate(pivot_data.iterrows()):
        bar = ax.bar(months, row.values, bottom=bottom, 
                    label=reason, color=colors[i % len(colors)], alpha=0.9, 
                    edgecolor='white', linewidth=1.0)
        bars.append(bar)
        if bottom is None:
            bottom = row.values
        else:
            bottom = bottom + row.values
    
    # Modern formatting with clean aesthetics
    ax.set_xlabel('Year Month', fontsize=13, fontweight='600', color='#333333')
    ax.set_ylabel('Percentage of Churn (%)', fontsize=13, fontweight='600', color='#333333')
    ax.set_title('Churn Reasons Over Time', fontsize=17, fontweight='600', pad=20, color='#1a1a1a')
    
    # Set y-axis limits and ticks properly
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
    
    ax.grid(axis='y', alpha=0.2, linestyle='--', color='#cccccc')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    
    # Rotate x-axis labels with modern styling
    plt.xticks(rotation=45, ha='right', fontsize=10, color='#666666')
    plt.yticks(fontsize=10, color='#666666')
    
    # Add legend with modern styling - place it outside the plot area
    legend = ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8.5, 
                       framealpha=0.95, frameon=True, edgecolor='#e0e0e0', 
                       facecolor='white', title='Churn Reasons', 
                       title_fontsize=9.5)
    legend.get_frame().set_linewidth(0.5)
    
    plt.tight_layout()
    
    # Save to PDF
    print(f"Generating PDF: {output_path}")
    with PdfPages(output_path) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
        
        # Add metadata
        d = pdf.infodict()
        d['Title'] = 'Churn Reasons Over Time Report'
        d['Author'] = 'Gladly Conversation Analyzer'
        d['Subject'] = 'Monthly Churn Reason Analysis'
        d['Keywords'] = 'churn analysis, customer retention, subscription cancellations'
    
    plt.close()
    print(f"[OK] Report generated successfully: {output_path}")
    print(f"  - {len(months)} months analyzed")
    print(f"  - {len(pivot_data)} unique churn reasons")
    print(f"  - Total responses: {len(df)}")
    return output_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate churn reasons report PDF')
    parser.add_argument('--input', '-i', 
                       default='data/survicate_cancelled_subscriptions_augmented.csv',
                       help='Path to input CSV file')
    parser.add_argument('--output', '-o',
                       default='churn_reasons_report.pdf',
                       help='Path to output PDF file')
    
    args = parser.parse_args()
    
    result = generate_churn_report(args.input, args.output)
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


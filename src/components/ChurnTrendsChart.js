import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { RefreshCw, AlertCircle, Download } from 'lucide-react';
import axios from 'axios';
import QuestionTrendsChart from './QuestionTrendsChart';

const ChurnTrendsChart = () => {
  const [data, setData] = useState([]);
  const [reasons, setReasons] = useState([]);
  const [months, setMonths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalResponses, setTotalResponses] = useState(0);

  // Google Sheets-style color palette - light, vibrant, and easy to distinguish
  // These colors are bright, have good contrast, and are colorblind-friendly
  const colors = [
    '#4285F4',  // Google Blue
    '#EA4335',  // Google Red
    '#FBBC04',  // Google Yellow
    '#34A853',  // Google Green
    '#FF6D01',  // Bright Orange
    '#9334E6',  // Bright Purple
    '#00ACC1',  // Cyan
    '#FF5252',  // Light Red
    '#66BB6A',  // Light Green
    '#42A5F5',  // Light Blue
    '#AB47BC',  // Light Purple
    '#FFA726',  // Light Orange
    '#26A69A',  // Teal
    '#EF5350',  // Coral
    '#5C6BC0',  // Indigo
    '#FFCA28',  // Amber
    '#26C6DA',  // Light Cyan
    '#EC407A',  // Pink
    '#7E57C2',  // Deep Purple
    '#78909C',  // Blue Grey
  ];

  const fetchChurnTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/survicate/churn-trends');
      if (response.data.success) {
        setData(response.data.data);
        setReasons(response.data.reasons);
        setMonths(response.data.months);
        setTotalResponses(response.data.total_responses || 0);
      } else {
        setError(response.data.error || 'Failed to load churn trends');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load churn trends');
      console.error('Error fetching churn trends:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChurnTrends();
  }, []);

  const handleDownloadPDF = async () => {
    try {
      // Trigger PDF generation on backend
      const response = await axios.post('/api/survicate/generate-pdf-report', {}, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'churn_reasons_report.pdf');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading PDF:', err);
      alert('Failed to generate PDF. You can run the generate_churn_report.py script manually.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading churn trends data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-2 font-semibold">Error loading data</p>
          <p className="text-gray-600 text-sm mb-4">{error}</p>
          <button
            onClick={fetchChurnTrends}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <p className="text-gray-600">No data available</p>
        </div>
      </div>
    );
  }

  // Prepare data for Recharts (stacked bar chart)
  // Also store counts for tooltip display
  const chartData = data.map(item => {
    const chartItem = { month: item.month, _total: item._total || 0 };
    reasons.forEach(reason => {
      chartItem[reason] = item[reason] || 0;
      chartItem[`${reason}_count`] = item[`${reason}_count`] || 0;
    });
    return chartItem;
  });

  return (
    <div className="h-full flex flex-col p-6 bg-white" style={{ minHeight: '800px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Churn Reasons Over Time</h2>
          <p className="text-sm text-gray-600 mt-1">
            {totalResponses.toLocaleString()} total responses across {months.length} months
          </p>
          <div className="mt-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-md inline-block">
            <p className="text-xs text-amber-800">
              <span className="font-semibold">Note:</span> November 2024 data excluded due to low response volume
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchChurnTrends}
            className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleDownloadPDF}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Download PDF</span>
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1" style={{ minHeight: '500px', height: '600px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="month" 
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              label={{ value: 'Percentage of Churn (%)', angle: -90, position: 'insideLeft' }}
              domain={[0, 100]}
              ticks={[0, 20, 40, 60, 80, 100]}
              tickFormatter={(value) => `${value}%`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '0',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }}
              cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) {
                  return null;
                }
                
                // Filter to only show segments with non-zero values
                // In a stacked bar, we want to show only the segment being hovered
                // Recharts provides all segments, but we'll show the one that's most relevant
                // (typically the one with the highest value in the hover area)
                const nonZeroSegments = payload.filter(item => item.value > 0);
                
                if (nonZeroSegments.length === 0) {
                  return null;
                }
                
                // For stacked bars, show the segment that's likely being hovered
                // We'll show the segment with the highest value (top of stack) or use the first non-zero
                const activeSegment = nonZeroSegments[0]; // Recharts orders by stack position
                
                const reasonName = activeSegment.dataKey;
                const percentage = activeSegment.value;
                const count = activeSegment.payload[`${reasonName}_count`] || 0;
                const total = activeSegment.payload._total || 0;
                const color = activeSegment.color;
                
                return (
                  <div style={{ padding: '12px' }}>
                    <div style={{ 
                      fontWeight: '600', 
                      fontSize: '14px', 
                      color: '#1f2937', 
                      marginBottom: '8px', 
                      borderBottom: '1px solid #e5e7eb', 
                      paddingBottom: '8px' 
                    }}>
                      Month: {label}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <div 
                        style={{ 
                          width: '12px', 
                          height: '12px', 
                          backgroundColor: color,
                          borderRadius: '2px',
                          flexShrink: 0,
                          marginTop: '2px'
                        }} 
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '600', color: '#1f2937', fontSize: '14px', marginBottom: '6px' }}>
                          {reasonName}
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: '700', color: '#1f2937', marginBottom: '4px' }}>
                          {percentage.toFixed(2)}%
                        </div>
                        {count > 0 && (
                          <div style={{ fontSize: '12px', color: '#6b7280' }}>
                            {count.toLocaleString()} of {total.toLocaleString()} responses
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              }}
            />
            <Legend 
              wrapperStyle={{ 
                paddingTop: '20px',
                paddingBottom: '10px'
              }}
              iconType="rect"
              iconSize={14}
              formatter={(value) => {
                // Truncate long labels but keep them readable
                return value.length > 35 ? value.substring(0, 32) + '...' : value;
              }}
              content={({ payload }) => {
                if (!payload || payload.length === 0) return null;
                
                // Organize legend into columns for better readability
                // Use 3 columns for better space utilization
                const itemsPerColumn = Math.ceil(payload.length / 3);
                const columns = [];
                for (let i = 0; i < payload.length; i += itemsPerColumn) {
                  columns.push(payload.slice(i, i + itemsPerColumn));
                }
                
                return (
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    gap: '40px',
                    padding: '24px 20px 16px 20px',
                    flexWrap: 'wrap',
                    backgroundColor: '#f9fafb',
                    borderRadius: '8px',
                    marginTop: '20px'
                  }}>
                    {columns.map((column, colIndex) => (
                      <div key={colIndex} style={{ 
                        display: 'flex', 
                        flexDirection: 'column', 
                        gap: '10px', 
                        minWidth: '220px',
                        maxWidth: '280px'
                      }}>
                        {column.map((entry, index) => (
                          <div 
                            key={`legend-item-${index}`}
                            style={{ 
                              display: 'flex', 
                              alignItems: 'flex-start', 
                              gap: '10px',
                              fontSize: '13px',
                              lineHeight: '1.6',
                              padding: '4px 0'
                            }}
                          >
                            <div 
                              style={{ 
                                width: '16px', 
                                height: '16px', 
                                backgroundColor: entry.color,
                                borderRadius: '3px',
                                flexShrink: 0,
                                marginTop: '2px',
                                border: '1px solid rgba(0, 0, 0, 0.1)'
                              }} 
                            />
                            <span style={{ 
                              color: '#1f2937',
                              fontWeight: '500',
                              wordBreak: 'break-word'
                            }}>
                              {entry.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                );
              }}
            />
            {reasons.map((reason, index) => (
              <Bar
                key={reason}
                dataKey={reason}
                stackId="a"
                fill={colors[index % colors.length]}
                name={reason}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Additional Question Trends */}
      <div className="mt-8 pt-8 border-t border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Additional Survey Question Trends</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <QuestionTrendsChart 
            question="Q2"
            questionText="Q#2: Where does the location pin not match your dog's location?"
          />
          <QuestionTrendsChart 
            question="Q3"
            questionText="Q#3: Was the pet location pin grayed out when the location was inaccurate?"
          />
        </div>
      </div>
    </div>
  );
};

export default ChurnTrendsChart;


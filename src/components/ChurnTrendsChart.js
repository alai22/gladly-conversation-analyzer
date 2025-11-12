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
  const [reasonTotals, setReasonTotals] = useState({});

  // Google Sheets style: Fixed hue sequence repeated at progressively lower saturation levels
  // Sequence: Blue, Red, Yellow, Green, Orange, Purple, Teal (repeated 3 times with decreasing saturation)
  const colors = [
    // Cycle 1: Vibrant colors
    '#4285F4',  // Blue - vibrant
    '#EA4335',  // Red - vibrant
    '#FBBC04',  // Yellow - vibrant
    '#34A853',  // Green - vibrant
    '#FF6D01',  // Orange - vibrant
    '#9334E6',  // Purple - vibrant
    '#00ACC1',  // Teal - vibrant
    // Cycle 2: Softer pastels (same hue sequence, lower saturation)
    '#64B5F6',  // Blue - softer pastel
    '#F28B82',  // Red - softer pastel
    '#FFF176',  // Yellow - softer pastel
    '#81C784',  // Green - softer pastel
    '#FFB74D',  // Orange - softer pastel
    '#BA68C8',  // Purple - softer pastel
    '#4DB6AC',  // Teal - softer pastel
    // Cycle 3: Very soft pastels (same hue sequence, even lower saturation)
    '#BBDEFB',  // Blue - very soft pastel
    '#FAD2CF',  // Red - very soft pastel
    '#FFF9C4',  // Yellow - very soft pastel
    '#C8E6C9',  // Green - very soft pastel
    '#FFE0B2',  // Orange - very soft pastel
    '#E1BEE7',  // Purple - very soft pastel
    '#B2DFDB',  // Teal - very soft pastel
    // Additional very pale for overflow
    '#E8F0FE',  // Very pale Blue
    '#FCE8E6',  // Very pale Red
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
        setReasonTotals(response.data.reason_totals || {});
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
    <div className="flex flex-col p-6 bg-white" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
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

      {/* Chart - Fixed height that won't shrink */}
      <div style={{ height: '750px', flexShrink: 0 }}>
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
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                padding: '0',
                boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)',
                maxWidth: '400px'
              }}
              cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) {
                  return null;
                }
                
                // Filter to only show segments with non-zero values
                const nonZeroSegments = payload.filter(item => item.value > 0);
                
                if (nonZeroSegments.length === 0) {
                  return null;
                }
                
                // Sort segments by value (highest to lowest) for better readability
                const sortedSegments = [...nonZeroSegments].sort((a, b) => b.value - a.value);
                
                // Get total for this month
                const total = nonZeroSegments[0]?.payload?._total || 0;
                
                return (
                  <div style={{ padding: '16px' }}>
                    {/* Header */}
                    <div style={{ 
                      fontWeight: '600', 
                      fontSize: '15px', 
                      color: '#111827', 
                      marginBottom: '12px', 
                      borderBottom: '2px solid #e5e7eb', 
                      paddingBottom: '10px' 
                    }}>
                      {label}
                    </div>
                    
                    {/* Segments list */}
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: 'column', 
                      gap: '8px',
                      maxHeight: '400px',
                      overflowY: 'auto',
                      paddingRight: '4px'
                    }}>
                      {sortedSegments.map((segment, index) => {
                        const reasonName = segment.dataKey;
                        const percentage = segment.value;
                        const count = segment.payload[`${reasonName}_count`] || 0;
                        const color = segment.color;
                        
                        return (
                          <div
                            key={index}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              padding: '8px',
                              borderRadius: '6px',
                              backgroundColor: index % 2 === 0 ? 'transparent' : '#f9fafb',
                              transition: 'background-color 0.2s'
                            }}
                          >
                            {/* Color indicator */}
                            <div 
                              style={{ 
                                width: '14px', 
                                height: '14px', 
                                backgroundColor: color,
                                borderRadius: '3px',
                                flexShrink: 0,
                                border: '1px solid rgba(0, 0, 0, 0.1)',
                                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
                              }} 
                            />
                            
                            {/* Content */}
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ 
                                fontWeight: '500', 
                                color: '#1f2937', 
                                fontSize: '13px', 
                                marginBottom: '4px',
                                lineHeight: '1.4'
                              }}>
                                {reasonName}
                              </div>
                              <div style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '8px',
                                fontSize: '12px'
                              }}>
                                <span style={{ 
                                  fontWeight: '600', 
                                  color: '#111827',
                                  fontSize: '14px'
                                }}>
                                  {percentage.toFixed(2)}%
                                </span>
                                {count > 0 && (
                                  <span style={{ 
                                    color: '#6b7280',
                                    fontSize: '11px'
                                  }}>
                                    ({count.toLocaleString()} of {total.toLocaleString()})
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              }}
            />
            <Legend 
              wrapperStyle={{ 
                paddingTop: '10px',
                paddingBottom: '5px'
              }}
              iconType="rect"
              iconSize={14}
              formatter={(value) => {
                // Truncate long labels but keep them readable
                return value.length > 35 ? value.substring(0, 32) + '...' : value;
              }}
              content={({ payload }) => {
                if (!payload || payload.length === 0) return null;
                
                // Sort payload by total count (highest to lowest) to match bar chart order
                const sortedPayload = [...payload].sort((a, b) => {
                  const totalA = reasonTotals[a.dataKey] || 0;
                  const totalB = reasonTotals[b.dataKey] || 0;
                  return totalB - totalA; // Descending order
                });
                
                // Organize legend into columns - use 4-5 columns when there's space
                // Determine number of columns based on screen width and item count
                const screenWidth = window.innerWidth;
                let numColumns = 3; // Default
                if (screenWidth >= 1920) {
                  numColumns = 5; // Large screens
                } else if (screenWidth >= 1440) {
                  numColumns = 4; // Medium-large screens
                } else if (screenWidth >= 1024) {
                  numColumns = 3; // Standard desktop
                } else {
                  numColumns = 2; // Smaller screens
                }
                
                const itemsPerColumn = Math.ceil(sortedPayload.length / numColumns);
                const columns = [];
                for (let i = 0; i < sortedPayload.length; i += itemsPerColumn) {
                  columns.push(sortedPayload.slice(i, i + itemsPerColumn));
                }
                
                return (
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    gap: '40px',
                    padding: '12px 20px 8px 20px',
                    flexWrap: 'wrap',
                    backgroundColor: '#f9fafb',
                    borderRadius: '8px',
                    marginTop: '10px'
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
      <div className="mt-8 pt-8 border-t border-gray-200 flex-shrink-0">
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
          <QuestionTrendsChart 
            question="Q4"
            questionText="Q#4: Is the collar not sending feedback or is your dog not responding to the feedback sent?"
          />
          <QuestionTrendsChart 
            question="Q5"
            questionText="Q#5: Did you screw in the contact tips required for static feedback to work properly?"
          />
          <QuestionTrendsChart 
            question="Q6"
            questionText="Q#6: What battery life, charging or power issues did you encounter?"
          />
          <QuestionTrendsChart 
            question="Q7"
            questionText="Q#7: Which containment solution did you purchase?"
          />
          <QuestionTrendsChart 
            question="Q8"
            questionText="Q#8: Did you engage with the Learn training curriculum?"
          />
          <QuestionTrendsChart 
            question="Q9"
            questionText="Q#9: What was the main reason you didn't complete the Learn curriculum?"
          />
          <QuestionTrendsChart 
            question="Q10"
            questionText="Q#10: Did you contact our Customer Service team via Dog Park?"
          />
          <QuestionTrendsChart 
            question="Q11"
            questionText="Q#11: Would a free session with a trainer to help your dog use the collar effectively have helped you continue to use it?"
          />
        </div>
      </div>
    </div>
  );
};

export default ChurnTrendsChart;


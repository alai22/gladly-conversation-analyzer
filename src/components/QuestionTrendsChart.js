import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { RefreshCw, AlertCircle } from 'lucide-react';
import axios from 'axios';

const QuestionTrendsChart = ({ question, questionText }) => {
  const [data, setData] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalResponses, setTotalResponses] = useState(0);
  
  // Color palette for answer segments
  const answerColors = [
    '#4285F4',  // Google Blue
    '#EA4335',  // Google Red
    '#FBBC04',  // Google Yellow
    '#34A853',  // Google Green
    '#FF6D01',  // Bright Orange
    '#9334E6',  // Bright Purple
  ];

  const fetchQuestionTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`/api/survicate/question-trends?question=${question}`);
      if (response.data.success) {
        setData(response.data.data);
        setAnswers(response.data.answers || []);
        setTotalResponses(response.data.total_responses || 0);
      } else {
        setError(response.data.error || 'Failed to load question trends');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load question trends');
      console.error('Error fetching question trends:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestionTrends();
  }, [question]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 p-8">
        <div className="text-center">
          <RefreshCw className="h-6 w-6 text-blue-500 animate-spin mx-auto mb-2" />
          <p className="text-gray-600 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 p-8">
        <div className="text-center max-w-md">
          <AlertCircle className="h-6 w-6 text-red-500 mx-auto mb-2" />
          <p className="text-red-600 text-sm font-semibold">Error loading data</p>
          <p className="text-gray-600 text-xs mb-3">{error}</p>
          <button
            onClick={fetchQuestionTrends}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 p-8">
        <div className="text-center">
          <p className="text-gray-600 text-sm">No data available</p>
        </div>
      </div>
    );
  }

  // Prepare chart data - use percentages instead of counts
  const chartData = data.map(item => {
    const chartItem = { month: item.month, _total: item._total || 0 };
    answers.forEach(answer => {
      // Use percentage for the bar value instead of count
      chartItem[answer] = item[`${answer}_percentage`] || 0;
      chartItem[`${answer}_count`] = item[answer] || 0; // Keep count for tooltip
      chartItem[`${answer}_percentage`] = item[`${answer}_percentage`] || 0;
    });
    return chartItem;
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">{questionText}</h3>
      </div>
      
      <div style={{ height: '340px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 10, bottom: 40 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="month" 
              angle={-45}
              textAnchor="end"
              height={60}
              tick={{ fontSize: 11 }}
            />
            <YAxis 
              label={{ value: 'Percentage (%)', angle: -90, position: 'insideLeft', fontSize: 12 }}
              domain={[0, 100]}
              ticks={[0, 20, 40, 60, 80, 100]}
              tickFormatter={(value) => `${value}%`}
              tick={{ fontSize: 11 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                padding: '0',
                boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)',
                maxWidth: '400px',
                opacity: 1
              }}
              wrapperStyle={{ 
                opacity: 1,
                backgroundColor: '#ffffff'
              }}
              cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) {
                  return null;
                }
                
                // Find the non-zero segment being hovered
                const activeSegment = payload.find(item => item.value > 0);
                if (!activeSegment) return null;
                
                const answerName = activeSegment.dataKey;
                const percentage = activeSegment.value; // Now value is percentage
                const count = activeSegment.payload[`${answerName}_count`] || 0;
                const total = activeSegment.payload._total || 0;
                const color = activeSegment.color;
                
                return (
                  <div style={{ padding: '10px', backgroundColor: '#ffffff' }}>
                    <div style={{ 
                      fontWeight: '600', 
                      fontSize: '13px', 
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
                        <div style={{ fontWeight: '600', color: '#1f2937', fontSize: '13px', marginBottom: '4px' }}>
                          {answerName}
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '700', color: '#1f2937', marginBottom: '2px' }}>
                          {percentage.toFixed(1)}%
                        </div>
                        <div style={{ fontSize: '12px', color: '#6b7280' }}>
                          {count.toLocaleString()} of {total.toLocaleString()} responses
                        </div>
                      </div>
                    </div>
                  </div>
                );
              }}
            />
            <Legend 
              wrapperStyle={{ paddingTop: '10px', fontSize: '11px' }}
              iconType="rect"
              iconSize={12}
            />
            {answers.map((answer, index) => (
              <Bar
                key={answer}
                dataKey={answer}
                stackId="a"
                fill={answerColors[index % answerColors.length]}
                name={answer}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default QuestionTrendsChart;


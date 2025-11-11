import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { RefreshCw, AlertCircle, Download } from 'lucide-react';
import axios from 'axios';

const ChurnTrendsChart = () => {
  const [data, setData] = useState([]);
  const [reasons, setReasons] = useState([]);
  const [months, setMonths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalResponses, setTotalResponses] = useState(0);

  // Modern, professional color palette - muted and aesthetically pleasing
  // These colors are colorblind-friendly and work well in both digital and print
  const colors = [
    '#2E86AB',  // Modern Blue
    '#A23B72',  // Muted Purple
    '#F18F01',  // Warm Orange
    '#C73E1D',  // Muted Red
    '#6A994E',  // Forest Green
    '#BC4749',  // Soft Red
    '#F77F00',  // Burnt Orange
    '#FCBF49',  // Golden Yellow
    '#06A77D',  // Teal
    '#118AB2',  // Ocean Blue
    '#073B4C',  // Dark Navy
    '#EF476F',  // Coral Pink
    '#06FFA5',  // Mint Green
    '#7209B7',  // Deep Purple
    '#F72585',  // Magenta
    '#4CC9F0',  // Sky Blue
    '#560BAD',  // Purple
    '#B5179E',  // Pink
    '#3A0CA3',  // Indigo
    '#7209B7',  // Violet
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
  const chartData = data.map(item => {
    const chartItem = { month: item.month };
    reasons.forEach(reason => {
      chartItem[reason] = item[reason] || 0;
    });
    return chartItem;
  });

  return (
    <div className="h-full flex flex-col p-6 bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Churn Reasons Over Time</h2>
          <p className="text-sm text-gray-600 mt-1">
            {totalResponses.toLocaleString()} total responses across {months.length} months
          </p>
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
      <div className="flex-1 min-h-0">
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
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '8px'
              }}
              formatter={(value, name) => [`${value.toFixed(2)}%`, name]}
              labelFormatter={(label) => `Month: ${label}`}
            />
            <Legend 
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="rect"
              formatter={(value) => {
                // Truncate long labels
                return value.length > 40 ? value.substring(0, 37) + '...' : value;
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

      {/* Summary Stats */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Churn Reasons (All Time)</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {reasons.slice(0, 8).map((reason, index) => {
            const total = data.reduce((sum, item) => sum + (item[reason] || 0), 0);
            const avg = total / months.length;
            return (
              <div key={reason} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-2 mb-1">
                  <div 
                    className="w-3 h-3 rounded"
                    style={{ backgroundColor: colors[index % colors.length] }}
                  />
                  <span className="text-xs font-medium text-gray-700 truncate" title={reason}>
                    {reason.length > 25 ? reason.substring(0, 22) + '...' : reason}
                  </span>
                </div>
                <div className="text-xs text-gray-600">
                  Avg: {avg.toFixed(1)}%
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ChurnTrendsChart;


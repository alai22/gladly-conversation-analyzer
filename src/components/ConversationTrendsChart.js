import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { RefreshCw, AlertCircle } from 'lucide-react';
import axios from 'axios';

const ConversationTrendsChart = () => {
  const [data, setData] = useState([]);
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [date, setDate] = useState('2025-10-20');
  const [chartType, setChartType] = useState('bar'); // 'bar' or 'pie'

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

  const fetchTopicTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`/api/conversations/topic-trends?date=${date}`);
      if (response.data.success) {
        setData(response.data.data);
        setTopics(response.data.topics);
        setTotal(response.data.total || 0);
      } else {
        setError(response.data.error || 'Failed to load topic trends');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load topic trends');
      console.error('Error fetching topic trends:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopicTrends();
  }, [date]);

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading conversation topic trends...</p>
          <p className="text-gray-500 text-sm mt-2">This may take a moment as we analyze conversations...</p>
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
            onClick={fetchTopicTrends}
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
          <p className="text-gray-600">No conversation data available for {formatDate(date)}</p>
          <p className="text-gray-500 text-sm mt-2">Try selecting a different date or check if conversations have been loaded.</p>
        </div>
      </div>
    );
  }

  // Prepare data for charts
  const chartData = data.map(item => ({
    topic: item.topic,
    count: item.count,
    percentage: item.percentage
  }));

  // For pie chart, we need the data in the right format
  const pieData = chartData.map(item => ({
    name: item.topic,
    value: item.percentage
  }));

  return (
    <div className="flex flex-col p-4 bg-white" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Conversation Topic Trends</h2>
          <p className="text-sm text-gray-600 mt-1">
            {total.toLocaleString()} conversations on {formatDate(date)}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => setChartType(chartType === 'bar' ? 'pie' : 'bar')}
            className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            {chartType === 'bar' ? 'Pie Chart' : 'Bar Chart'}
          </button>
          <button
            onClick={fetchTopicTrends}
            className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Chart */}
      <div style={{ height: '600px', flexShrink: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' ? (
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 20, bottom: 100 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis 
                dataKey="topic" 
                angle={-45}
                textAnchor="end"
                height={120}
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                label={{ value: 'Percentage of Conversations (%)', angle: -90, position: 'insideLeft' }}
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
                  padding: '12px',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)'
                }}
                formatter={(value, name) => {
                  if (name === 'percentage') {
                    const item = chartData.find(d => d.percentage === value);
                    return [
                      `${value.toFixed(2)}% (${item?.count || 0} conversations)`,
                      'Percentage'
                    ];
                  }
                  return [value, name];
                }}
              />
              <Legend 
                wrapperStyle={{ 
                  paddingTop: '10px',
                  paddingBottom: '5px'
                }}
                iconType="rect"
                iconSize={14}
              />
              <Bar
                dataKey="percentage"
                fill={colors[0]}
                name="Percentage"
              />
            </BarChart>
          ) : (
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                outerRadius={200}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '12px',
                  padding: '12px',
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)'
                }}
                formatter={(value, name, props) => {
                  const item = chartData.find(d => d.topic === props.payload.name);
                  return [
                    `${value.toFixed(2)}% (${item?.count || 0} conversations)`,
                    'Percentage'
                  ];
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
                  return value.length > 40 ? value.substring(0, 37) + '...' : value;
                }}
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Summary Table */}
      <div className="mt-8 pt-8 border-t border-gray-200 flex-shrink-0">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Topic Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Topic
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Percentage
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {chartData.map((item, index) => (
                <tr key={item.topic} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div 
                        className="w-4 h-4 rounded mr-2"
                        style={{ backgroundColor: colors[index % colors.length] }}
                      />
                      <span className="text-sm text-gray-900">{item.topic}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.count.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {item.percentage.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ConversationTrendsChart;

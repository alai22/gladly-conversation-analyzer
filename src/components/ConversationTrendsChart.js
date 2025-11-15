import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { RefreshCw, AlertCircle, Info, CheckCircle } from 'lucide-react';
import axios from 'axios';

const ConversationTrendsChart = () => {
  const [data, setData] = useState([]);
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [date, setDate] = useState('2025-10-20');
  const [chartType, setChartType] = useState('bar'); // 'bar' or 'pie'
  const [extractionStatus, setExtractionStatus] = useState({});
  const [statusLoading, setStatusLoading] = useState(true);
  
  // Sentiment data state (for single date - kept for backward compatibility)
  const [sentimentBreakdown, setSentimentBreakdown] = useState({});
  const [customerSentimentBreakdown, setCustomerSentimentBreakdown] = useState({});
  const [topKeyPhrases, setTopKeyPhrases] = useState({});
  const [collarFirmwareVersions, setCollarFirmwareVersions] = useState({});
  const [collarModels, setCollarModels] = useState({});
  const [mobileAppVersions, setMobileAppVersions] = useState({});
  
  // Sentiment time-series chart state
  const [sentimentTimeSeriesData, setSentimentTimeSeriesData] = useState([]);
  const [sentimentTimeSeriesSentiments, setSentimentTimeSeriesSentiments] = useState([]);
  const [sentimentTimeSeriesLoading, setSentimentTimeSeriesLoading] = useState(false);
  const [sentimentTimeSeriesError, setSentimentTimeSeriesError] = useState(null);
  const [sentimentTimeSeriesStartDate, setSentimentTimeSeriesStartDate] = useState('');
  const [sentimentTimeSeriesEndDate, setSentimentTimeSeriesEndDate] = useState('');
  const [sentimentTimeSeriesMode, setSentimentTimeSeriesMode] = useState('percentage'); // 'count' or 'percentage'
  
  // Customer sentiment time-series chart state
  const [customerSentimentTimeSeriesData, setCustomerSentimentTimeSeriesData] = useState([]);
  const [customerSentimentTimeSeriesSentiments, setCustomerSentimentTimeSeriesSentiments] = useState([]);
  const [customerSentimentTimeSeriesLoading, setCustomerSentimentTimeSeriesLoading] = useState(false);
  const [customerSentimentTimeSeriesError, setCustomerSentimentTimeSeriesError] = useState(null);
  const [customerSentimentTimeSeriesStartDate, setCustomerSentimentTimeSeriesStartDate] = useState('');
  const [customerSentimentTimeSeriesEndDate, setCustomerSentimentTimeSeriesEndDate] = useState('');
  const [customerSentimentTimeSeriesMode, setCustomerSentimentTimeSeriesMode] = useState('percentage'); // 'count' or 'percentage'
  
  // Time-series chart state (for topics)
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [timeSeriesTopics, setTimeSeriesTopics] = useState([]);
  const [timeSeriesLoading, setTimeSeriesLoading] = useState(false);
  const [timeSeriesError, setTimeSeriesError] = useState(null);
  const [timeSeriesStartDate, setTimeSeriesStartDate] = useState('2025-10-20');
  const [timeSeriesEndDate, setTimeSeriesEndDate] = useState('2025-10-25');
  const [timeSeriesMode, setTimeSeriesMode] = useState('percentage'); // 'count' or 'percentage'

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

  const fetchExtractionStatus = async () => {
    setStatusLoading(true);
    try {
      const response = await axios.get('/api/conversations/topic-extraction-status');
      if (response.data.success) {
        setExtractionStatus(response.data.status || {});
      }
    } catch (err) {
      console.error('Error fetching extraction status:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  const fetchTopicTrends = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`/api/conversations/topic-trends?date=${date}`);
      if (response.data.success) {
        setData(response.data.data);
        setTopics(response.data.topics);
        setTotal(response.data.total || 0);
        // Extract sentiment breakdowns and metadata if available
        setSentimentBreakdown(response.data.sentiment_breakdown || {});
        setCustomerSentimentBreakdown(response.data.customer_sentiment_breakdown || {});
        setTopKeyPhrases(response.data.top_key_phrases || {});
        setCollarFirmwareVersions(response.data.collar_firmware_versions || {});
        setCollarModels(response.data.collar_models || {});
        setMobileAppVersions(response.data.mobile_app_versions || {});
      } else {
        // No topics extracted for this date
        setData([]);
        setTopics([]);
        setTotal(0);
        setSentimentBreakdown({});
        setCustomerSentimentBreakdown({});
        setTopKeyPhrases({});
        setCollarFirmwareVersions({});
        setCollarModels({});
        setMobileAppVersions({});
        setError(response.data.message || 'No topics extracted for this date');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load topic trends');
      console.error('Error fetching topic trends:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExtractionStatus();
  }, []);

  // Set default date range when extraction status is loaded
  useEffect(() => {
    const statusEntries = Object.keys(extractionStatus).sort();
    if (statusEntries.length > 0) {
      const firstDate = statusEntries[0];
      const lastDate = statusEntries[statusEntries.length - 1];
      
      // Set topics time-series default dates
      if (timeSeriesStartDate === '2025-10-20' && timeSeriesEndDate === '2025-10-25') {
        setTimeSeriesStartDate(firstDate);
        setTimeSeriesEndDate(lastDate);
      }
      
      // Set sentiment time-series default dates
      if (!sentimentTimeSeriesStartDate || !sentimentTimeSeriesEndDate) {
        setSentimentTimeSeriesStartDate(firstDate);
        setSentimentTimeSeriesEndDate(lastDate);
      }
      
      // Set customer sentiment time-series default dates
      if (!customerSentimentTimeSeriesStartDate || !customerSentimentTimeSeriesEndDate) {
        setCustomerSentimentTimeSeriesStartDate(firstDate);
        setCustomerSentimentTimeSeriesEndDate(lastDate);
      }
      
      // Also set the single date picker to the first available date
      if (date === '2025-10-20') {
        setDate(firstDate);
      }
    }
  }, [extractionStatus]);

  useEffect(() => {
    fetchTopicTrends();
  }, [date]);

  const fetchTopicTrendsOverTime = async () => {
    setTimeSeriesLoading(true);
    setTimeSeriesError(null);
    try {
      const response = await axios.get(`/api/conversations/topic-trends-over-time?start_date=${timeSeriesStartDate}&end_date=${timeSeriesEndDate}`);
      if (response.data.success) {
        let chartData = response.data.data || [];
        const topics = response.data.topics || [];
        
        // Calculate total column (aggregate across all dates) and order topics by total count
        if (chartData.length > 0) {
          const totalData = { date: 'Total' };
          let grandTotal = 0;
          const topicTotals = {};
          
          // Sum up all topics across all dates
          topics.forEach(topic => {
            let topicTotal = 0;
            chartData.forEach(day => {
              topicTotal += day[topic] || 0;
            });
            topicTotals[topic] = topicTotal;
            totalData[topic] = topicTotal;
            grandTotal += topicTotal;
          });
          
          // Calculate percentages for total
          topics.forEach(topic => {
            const count = totalData[topic] || 0;
            const percentage = grandTotal > 0 ? (count / grandTotal * 100) : 0;
            totalData[`${topic}_percentage`] = Math.round(percentage * 100) / 100;
          });
          
          totalData.total = grandTotal;
          chartData = [...chartData, totalData];
          
          // Order topics by total count (descending) - most common at bottom of stack
          const sortedTopics = [...topics].sort((a, b) => {
            const totalA = topicTotals[a] || 0;
            const totalB = topicTotals[b] || 0;
            return totalB - totalA; // Descending order
          });
          
          setTimeSeriesTopics(sortedTopics);
        } else {
          setTimeSeriesTopics(topics);
        }
        
        setTimeSeriesData(chartData);
      } else {
        setTimeSeriesData([]);
        setTimeSeriesTopics([]);
        setTimeSeriesError(response.data.message || 'No topics found for date range');
      }
    } catch (err) {
      setTimeSeriesError(err.response?.data?.error || err.message || 'Failed to load topic trends over time');
      console.error('Error fetching topic trends over time:', err);
    } finally {
      setTimeSeriesLoading(false);
    }
  };

  useEffect(() => {
    if (timeSeriesStartDate && timeSeriesEndDate && timeSeriesStartDate <= timeSeriesEndDate) {
      fetchTopicTrendsOverTime();
    }
  }, [timeSeriesStartDate, timeSeriesEndDate]);

  const fetchSentimentTrendsOverTime = async () => {
    setSentimentTimeSeriesLoading(true);
    setSentimentTimeSeriesError(null);
    setCustomerSentimentTimeSeriesLoading(true);
    setCustomerSentimentTimeSeriesError(null);
    
    try {
      const response = await axios.get(`/api/conversations/sentiment-trends-over-time?start_date=${sentimentTimeSeriesStartDate}&end_date=${sentimentTimeSeriesEndDate}`);
      if (response.data.success) {
        setSentimentTimeSeriesData(response.data.sentiment_data || []);
        setSentimentTimeSeriesSentiments(response.data.sentiments || []);
        setCustomerSentimentTimeSeriesData(response.data.customer_sentiment_data || []);
        setCustomerSentimentTimeSeriesSentiments(response.data.customer_sentiments || []);
      } else {
        setSentimentTimeSeriesData([]);
        setSentimentTimeSeriesSentiments([]);
        setCustomerSentimentTimeSeriesData([]);
        setCustomerSentimentTimeSeriesSentiments([]);
        setSentimentTimeSeriesError(response.data.message || 'No sentiment data found for date range');
      }
    } catch (err) {
      setSentimentTimeSeriesError(err.response?.data?.error || err.message || 'Failed to load sentiment trends over time');
      setCustomerSentimentTimeSeriesError(err.response?.data?.error || err.message || 'Failed to load sentiment trends over time');
      console.error('Error fetching sentiment trends over time:', err);
    } finally {
      setSentimentTimeSeriesLoading(false);
      setCustomerSentimentTimeSeriesLoading(false);
    }
  };

  useEffect(() => {
    if (sentimentTimeSeriesStartDate && sentimentTimeSeriesEndDate && sentimentTimeSeriesStartDate <= sentimentTimeSeriesEndDate) {
      fetchSentimentTrendsOverTime();
    }
  }, [sentimentTimeSeriesStartDate, sentimentTimeSeriesEndDate]);
  
  // Sync customer sentiment dates with overall sentiment dates
  useEffect(() => {
    setCustomerSentimentTimeSeriesStartDate(sentimentTimeSeriesStartDate);
    setCustomerSentimentTimeSeriesEndDate(sentimentTimeSeriesEndDate);
  }, [sentimentTimeSeriesStartDate, sentimentTimeSeriesEndDate]);
  
  // Prepare sentiment chart data based on mode (count or percentage)
  const prepareSentimentChartData = (data, sentiments, mode) => {
    if (mode === 'percentage') {
      return data.map(day => {
        const newDay = { ...day };
        sentiments.forEach(sentiment => {
          // Use percentage instead of count
          const percentage = day[`${sentiment}_percentage`] || 0;
          newDay[sentiment] = percentage;
        });
        return newDay;
      });
    }
    return data;
  };

  const formatDate = (dateStr) => {
    try {
      if (dateStr === 'Total') return 'Total';
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };
  
  // Prepare chart data based on mode (count or percentage)
  const prepareChartData = () => {
    if (timeSeriesMode === 'percentage') {
      return timeSeriesData.map(day => {
        const newDay = { ...day };
        timeSeriesTopics.forEach(topic => {
          // Use percentage instead of count
          const percentage = day[`${topic}_percentage`] || 0;
          newDay[topic] = percentage;
        });
        // Keep total for reference but don't use it in the chart
        return newDay;
      });
    }
    return timeSeriesData;
  };

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading extraction status...</p>
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

  // Format extraction status for display
  const statusEntries = Object.entries(extractionStatus).sort((a, b) => b[0].localeCompare(a[0]));
  const hasTopicsForDate = extractionStatus[date] && extractionStatus[date].conversation_count > 0;

  if (data.length === 0 && !error) {
    return (
      <div className="flex flex-col p-4 bg-white" style={{ minHeight: '100vh' }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Conversation Topic Trends</h2>
            <p className="text-sm text-gray-600 mt-1">
              View topic distribution for conversations with extracted topics
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
              onClick={() => {
                fetchExtractionStatus();
                fetchTopicTrends();
              }}
              className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Extraction Status */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900 mb-2">Topic Extraction Status</h3>
              {statusEntries.length === 0 ? (
                <p className="text-sm text-blue-800">
                  No topics have been extracted yet. Go to Settings → Admin Tools → Extract Conversation Topics to get started.
                </p>
              ) : (
                <div>
                  <p className="text-sm text-blue-800 mb-3">
                    Topics have been extracted for the following dates:
                  </p>
                  <div className="space-y-2">
                    {statusEntries.map(([statusDate, status]) => (
                      <div key={statusDate} className="flex items-center justify-between p-2 bg-white rounded border border-blue-100">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm font-medium text-gray-900">{formatDate(statusDate)}</span>
                        </div>
                        <span className="text-sm text-gray-600">
                          {status.conversation_count.toLocaleString()} conversations, {status.unique_topics} topics
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* No Data Message */}
        <div className="flex items-center justify-center p-8 border border-gray-200 rounded-lg bg-gray-50">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 font-medium">No topics extracted for {formatDate(date)}</p>
            <p className="text-gray-500 text-sm mt-2">
              {hasTopicsForDate 
                ? 'Topics are being processed. Please try again in a moment.'
                : 'Please extract topics for this date in Settings → Admin Tools → Extract Conversation Topics.'}
            </p>
          </div>
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
            onClick={() => {
              fetchExtractionStatus();
              fetchTopicTrends();
            }}
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
                domain={[0, 'auto']}
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
                      ''
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

      {/* Extraction Status Summary */}
      {statusEntries.length > 0 && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <h3 className="text-sm font-medium text-gray-900 mb-3">Extraction Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {statusEntries.map(([statusDate, status]) => (
              <div key={statusDate} className={`p-3 rounded border ${
                statusDate === date 
                  ? 'bg-blue-50 border-blue-300' 
                  : 'bg-white border-gray-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">{formatDate(statusDate)}</span>
                  {statusDate === date && (
                    <span className="text-xs text-blue-600 font-medium">Current</span>
                  )}
                </div>
                <div className="mt-1 text-xs text-gray-600">
                  {status.conversation_count.toLocaleString()} conversations
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sentiment Charts Section - Time Series */}
      {(sentimentTimeSeriesData.length > 0 || customerSentimentTimeSeriesData.length > 0) && (
        <div className="mt-12 pt-12 border-t border-gray-300 flex-shrink-0">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">Sentiment Analysis Over Time</h3>
          
          <div className="grid grid-cols-1 gap-12 mb-8">
            {/* Overall Sentiment Over Time Chart */}
            {sentimentTimeSeriesData.length > 0 && (
              <div>
                <div className="mb-4">
                  <h4 className="text-lg font-medium text-gray-800 mb-4">Overall Sentiment</h4>
                  <div className="flex items-center space-x-4 mb-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
                      <input
                        type="date"
                        value={sentimentTimeSeriesStartDate}
                        onChange={(e) => setSentimentTimeSeriesStartDate(e.target.value)}
                        className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">End Date</label>
                      <input
                        type="date"
                        value={sentimentTimeSeriesEndDate}
                        onChange={(e) => setSentimentTimeSeriesEndDate(e.target.value)}
                        className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="flex items-end space-x-2">
                      <button
                        onClick={() => setSentimentTimeSeriesMode(sentimentTimeSeriesMode === 'count' ? 'percentage' : 'count')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          sentimentTimeSeriesMode === 'percentage'
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {sentimentTimeSeriesMode === 'percentage' ? 'Percentage' : 'Count'}
                      </button>
                      <button
                        onClick={fetchSentimentTrendsOverTime}
                        disabled={sentimentTimeSeriesLoading}
                        className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className={`h-4 w-4 ${sentimentTimeSeriesLoading ? 'animate-spin' : ''}`} />
                        <span>Refresh</span>
                      </button>
                    </div>
                  </div>
                </div>
                
                {sentimentTimeSeriesLoading ? (
                  <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="text-center">
                      <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
                      <p className="text-gray-600">Loading sentiment data...</p>
                    </div>
                  </div>
                ) : sentimentTimeSeriesError ? (
                  <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="text-center max-w-md">
                      <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
                      <p className="text-red-600 mb-2 font-semibold">Error loading data</p>
                      <p className="text-gray-600 text-sm mb-4">{sentimentTimeSeriesError}</p>
                      <button
                        onClick={fetchSentimentTrendsOverTime}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Retry
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ height: '500px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={prepareSentimentChartData(sentimentTimeSeriesData, sentimentTimeSeriesSentiments, sentimentTimeSeriesMode)}
                        margin={{ top: 10, right: 30, left: 20, bottom: 100 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          angle={-45}
                          textAnchor="end"
                          height={120}
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => formatDate(value)}
                        />
                        <YAxis 
                          label={{ 
                            value: sentimentTimeSeriesMode === 'count' ? 'Number of Conversations' : 'Percentage (%)', 
                            angle: -90, 
                            position: 'insideLeft' 
                          }}
                          tick={{ fontSize: 12 }}
                          domain={sentimentTimeSeriesMode === 'percentage' ? [0, 100] : [0, 'auto']}
                          tickFormatter={sentimentTimeSeriesMode === 'percentage' ? (value) => `${value}%` : undefined}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: '12px',
                            padding: '12px',
                            boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)'
                          }}
                          formatter={(value, name, props) => {
                            if (name === 'total') {
                              const dataPoint = props.payload;
                              if (dataPoint.date === 'Total') {
                                return [value, 'Grand Total'];
                              }
                              return [value, 'Total'];
                            }
                            const dataPoint = props.payload;
                            if (sentimentTimeSeriesMode === 'percentage') {
                              const originalData = sentimentTimeSeriesData.find(d => d.date === dataPoint.date);
                              const count = originalData?.[name] || 0;
                              return [`${value.toFixed(1)}% (${count} conversations)`, name];
                            } else {
                              const percentage = dataPoint?.[`${name}_percentage`] || 0;
                              return [`${value} conversations (${percentage.toFixed(1)}%)`, name];
                            }
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
                        {sentimentTimeSeriesSentiments.map((sentiment, index) => {
                          const sentimentColors = {
                            'Positive': '#34A853',  // Green
                            'Negative': '#EA4335',  // Red
                            'Neutral': '#9AA0A6'    // Gray
                          };
                          return (
                            <Bar
                              key={sentiment}
                              dataKey={sentiment}
                              stackId="sentiment"
                              fill={sentimentColors[sentiment] || colors[index % colors.length]}
                              name={sentiment}
                            />
                          );
                        })}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Customer Sentiment Over Time Chart */}
            {customerSentimentTimeSeriesData.length > 0 && (
              <div>
                <div className="mb-4">
                  <h4 className="text-lg font-medium text-gray-800 mb-4">Customer Sentiment</h4>
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="flex items-end space-x-2">
                      <button
                        onClick={() => setCustomerSentimentTimeSeriesMode(customerSentimentTimeSeriesMode === 'count' ? 'percentage' : 'count')}
                        className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                          customerSentimentTimeSeriesMode === 'percentage'
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {customerSentimentTimeSeriesMode === 'percentage' ? 'Percentage' : 'Count'}
                      </button>
                    </div>
                  </div>
                </div>
                
                {customerSentimentTimeSeriesLoading ? (
                  <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="text-center">
                      <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
                      <p className="text-gray-600">Loading customer sentiment data...</p>
                    </div>
                  </div>
                ) : customerSentimentTimeSeriesError ? (
                  <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="text-center max-w-md">
                      <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
                      <p className="text-red-600 mb-2 font-semibold">Error loading data</p>
                      <p className="text-gray-600 text-sm mb-4">{customerSentimentTimeSeriesError}</p>
                      <button
                        onClick={fetchSentimentTrendsOverTime}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Retry
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ height: '500px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={prepareSentimentChartData(customerSentimentTimeSeriesData, customerSentimentTimeSeriesSentiments, customerSentimentTimeSeriesMode)}
                        margin={{ top: 10, right: 30, left: 20, bottom: 100 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="date" 
                          angle={-45}
                          textAnchor="end"
                          height={120}
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => formatDate(value)}
                        />
                        <YAxis 
                          label={{ 
                            value: customerSentimentTimeSeriesMode === 'count' ? 'Number of Conversations' : 'Percentage (%)', 
                            angle: -90, 
                            position: 'insideLeft' 
                          }}
                          tick={{ fontSize: 12 }}
                          domain={customerSentimentTimeSeriesMode === 'percentage' ? [0, 100] : [0, 'auto']}
                          tickFormatter={customerSentimentTimeSeriesMode === 'percentage' ? (value) => `${value}%` : undefined}
                        />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: '12px',
                            padding: '12px',
                            boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)'
                          }}
                          formatter={(value, name, props) => {
                            if (name === 'total') {
                              const dataPoint = props.payload;
                              if (dataPoint.date === 'Total') {
                                return [value, 'Grand Total'];
                              }
                              return [value, 'Total'];
                            }
                            const dataPoint = props.payload;
                            if (customerSentimentTimeSeriesMode === 'percentage') {
                              const originalData = customerSentimentTimeSeriesData.find(d => d.date === dataPoint.date);
                              const count = originalData?.[name] || 0;
                              return [`${value.toFixed(1)}% (${count} conversations)`, name];
                            } else {
                              const percentage = dataPoint?.[`${name}_percentage`] || 0;
                              return [`${value} conversations (${percentage.toFixed(1)}%)`, name];
                            }
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
                            return value.length > 30 ? value.substring(0, 27) + '...' : value;
                          }}
                        />
                        {customerSentimentTimeSeriesSentiments.map((sentiment, index) => (
                          <Bar
                            key={sentiment}
                            dataKey={sentiment}
                            stackId="customer_sentiment"
                            fill={colors[index % colors.length]}
                            name={sentiment}
                          />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Key Phrases and Version Information Section */}
      {(Object.keys(topKeyPhrases).length > 0 || Object.keys(collarFirmwareVersions).length > 0 || 
        Object.keys(collarModels).length > 0 || Object.keys(mobileAppVersions).length > 0) && (
        <div className="mt-12 pt-12 border-t border-gray-300 flex-shrink-0">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">Key Insights</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Top Key Phrases Chart */}
            {Object.keys(topKeyPhrases).length > 0 && (
              <div>
                <h4 className="text-lg font-medium text-gray-800 mb-4">Top Key Phrases</h4>
                <div style={{ height: '400px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(topKeyPhrases)
                        .map(([name, value]) => ({ name, value }))
                        .sort((a, b) => b.value - a.value)
                        .slice(0, 15)} // Show top 15
                      margin={{ top: 10, right: 30, left: 20, bottom: 100 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="name" 
                        angle={-45}
                        textAnchor="end"
                        height={120}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis 
                        label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }}
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
                        formatter={(value) => [`${value} conversations`, 'Frequency']}
                      />
                      <Bar 
                        dataKey="value" 
                        fill="#9334E6"
                        name="Frequency"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {/* Key phrases table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Key Phrase</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(topKeyPhrases)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 10)
                        .map(([phrase, count]) => (
                          <tr key={phrase}>
                            <td className="px-4 py-2 text-sm text-gray-900 capitalize">{phrase}</td>
                            <td className="px-4 py-2 text-sm text-gray-900">{count.toLocaleString()}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Collar Firmware Versions Chart */}
            {Object.keys(collarFirmwareVersions).length > 0 && (
              <div>
                <h4 className="text-lg font-medium text-gray-800 mb-4">Collar Firmware Versions</h4>
                <div style={{ height: '400px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(collarFirmwareVersions)
                        .map(([name, value]) => ({ name, value }))
                        .sort((a, b) => b.value - a.value)}
                      margin={{ top: 10, right: 30, left: 20, bottom: 60 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="name" 
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        tick={{ fontSize: 12 }}
                      />
                      <YAxis 
                        label={{ value: 'Number of Conversations', angle: -90, position: 'insideLeft' }}
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
                        formatter={(value, name, props) => {
                          const total = Object.values(collarFirmwareVersions).reduce((a, b) => a + b, 0);
                          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                          return [`${value} conversations (${percentage}%)`, 'Count'];
                        }}
                      />
                      <Bar 
                        dataKey="value" 
                        fill="#00ACC1"
                        name="Conversations"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {/* Firmware versions table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Firmware Version</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Percentage</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(collarFirmwareVersions)
                        .sort((a, b) => b[1] - a[1])
                        .map(([version, count]) => {
                          const total = Object.values(collarFirmwareVersions).reduce((a, b) => a + b, 0);
                          const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                          return (
                            <tr key={version}>
                              <td className="px-4 py-2 text-sm text-gray-900">{version}</td>
                              <td className="px-4 py-2 text-sm text-gray-900">{count.toLocaleString()}</td>
                              <td className="px-4 py-2 text-sm text-gray-900">{percentage}%</td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Additional Version Information Row */}
          {(Object.keys(collarModels).length > 0 || Object.keys(mobileAppVersions).length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
              {/* Collar Models Chart */}
              {Object.keys(collarModels).length > 0 && (
                <div>
                  <h4 className="text-lg font-medium text-gray-800 mb-4">Collar Models</h4>
                  <div style={{ height: '400px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={Object.entries(collarModels)
                          .map(([name, value]) => ({ name, value }))
                          .sort((a, b) => b.value - a.value)}
                        margin={{ top: 10, right: 30, left: 20, bottom: 60 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="name" 
                          angle={-45}
                          textAnchor="end"
                          height={80}
                          tick={{ fontSize: 12 }}
                        />
                        <YAxis 
                          label={{ value: 'Number of Conversations', angle: -90, position: 'insideLeft' }}
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
                          formatter={(value, name, props) => {
                            const total = Object.values(collarModels).reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return [`${value} conversations (${percentage}%)`, 'Count'];
                          }}
                        />
                        <Bar 
                          dataKey="value" 
                          fill="#34A853"
                          name="Conversations"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  {/* Collar models table */}
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Collar Model</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Percentage</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(collarModels)
                          .sort((a, b) => b[1] - a[1])
                          .map(([model, count]) => {
                            const total = Object.values(collarModels).reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                            return (
                              <tr key={model}>
                                <td className="px-4 py-2 text-sm text-gray-900">{model}</td>
                                <td className="px-4 py-2 text-sm text-gray-900">{count.toLocaleString()}</td>
                                <td className="px-4 py-2 text-sm text-gray-900">{percentage}%</td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Mobile App Versions Chart */}
              {Object.keys(mobileAppVersions).length > 0 && (
                <div>
                  <h4 className="text-lg font-medium text-gray-800 mb-4">Mobile App Versions</h4>
                  <div style={{ height: '400px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={Object.entries(mobileAppVersions)
                          .map(([name, value]) => ({ name, value }))
                          .sort((a, b) => b.value - a.value)}
                        margin={{ top: 10, right: 30, left: 20, bottom: 60 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis 
                          dataKey="name" 
                          angle={-45}
                          textAnchor="end"
                          height={80}
                          tick={{ fontSize: 12 }}
                        />
                        <YAxis 
                          label={{ value: 'Number of Conversations', angle: -90, position: 'insideLeft' }}
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
                          formatter={(value, name, props) => {
                            const total = Object.values(mobileAppVersions).reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return [`${value} conversations (${percentage}%)`, 'Count'];
                          }}
                        />
                        <Bar 
                          dataKey="value" 
                          fill="#FBBC04"
                          name="Conversations"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  {/* Mobile app versions table */}
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">App Version</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Percentage</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(mobileAppVersions)
                          .sort((a, b) => b[1] - a[1])
                          .map(([version, count]) => {
                            const total = Object.values(mobileAppVersions).reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                            return (
                              <tr key={version}>
                                <td className="px-4 py-2 text-sm text-gray-900">{version}</td>
                                <td className="px-4 py-2 text-sm text-gray-900">{count.toLocaleString()}</td>
                                <td className="px-4 py-2 text-sm text-gray-900">{percentage}%</td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

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

      {/* Time-Series Chart: Topics Over Time */}
      <div className="mt-12 pt-12 border-t border-gray-300 flex-shrink-0">
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Topics Over Time</h3>
          <p className="text-sm text-gray-600 mb-4">
            View how conversation topics change over a date range
          </p>
          <div className="flex items-center space-x-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={timeSeriesStartDate}
                onChange={(e) => setTimeSeriesStartDate(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={timeSeriesEndDate}
                onChange={(e) => setTimeSeriesEndDate(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end space-x-2">
              <button
                onClick={() => setTimeSeriesMode(timeSeriesMode === 'count' ? 'percentage' : 'count')}
                className={`px-4 py-2 text-sm rounded-lg transition-colors ${
                  timeSeriesMode === 'percentage'
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {timeSeriesMode === 'percentage' ? 'Percentage' : 'Count'}
              </button>
              <button
                onClick={fetchTopicTrendsOverTime}
                disabled={timeSeriesLoading}
                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`h-4 w-4 ${timeSeriesLoading ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {timeSeriesLoading ? (
          <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Loading time-series data...</p>
            </div>
          </div>
        ) : timeSeriesError ? (
          <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
            <div className="text-center max-w-md">
              <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 mb-2 font-semibold">Error loading data</p>
              <p className="text-gray-600 text-sm mb-4">{timeSeriesError}</p>
              <button
                onClick={fetchTopicTrendsOverTime}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        ) : timeSeriesData.length === 0 ? (
          <div className="flex items-center justify-center h-96 border border-gray-200 rounded-lg bg-gray-50">
            <div className="text-center">
              <AlertCircle className="h-8 w-8 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 font-medium">No topics found for date range</p>
              <p className="text-gray-500 text-sm mt-2">
                Please extract topics for dates in this range in Settings → Admin Tools
              </p>
            </div>
          </div>
        ) : (
          <div style={{ height: '600px', flexShrink: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={prepareChartData()}
                margin={{ top: 10, right: 30, left: 20, bottom: 100 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="date" 
                  angle={-45}
                  textAnchor="end"
                  height={120}
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => formatDate(value)}
                />
                <YAxis 
                  label={{ 
                    value: timeSeriesMode === 'count' ? 'Number of Conversations' : 'Percentage (%)', 
                    angle: -90, 
                    position: 'insideLeft' 
                  }}
                  tick={{ fontSize: 12 }}
                  domain={timeSeriesMode === 'percentage' ? [0, 100] : [0, 'auto']}
                  tickFormatter={timeSeriesMode === 'percentage' ? (value) => `${value}%` : undefined}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#ffffff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '12px',
                    padding: '12px',
                    boxShadow: '0 8px 16px rgba(0, 0, 0, 0.12)'
                  }}
                  formatter={(value, name, props) => {
                    if (name === 'total') {
                      const dataPoint = props.payload;
                      if (dataPoint.date === 'Total') {
                        return [value, 'Grand Total'];
                      }
                      return [value, 'Total'];
                    }
                    const dataPoint = props.payload;
                    if (timeSeriesMode === 'percentage') {
                      // In percentage mode, show percentage and count
                      const originalData = timeSeriesData.find(d => d.date === dataPoint.date);
                      const count = originalData?.[name] || 0;
                      return [`${value.toFixed(1)}% (${count} conversations)`, name];
                    } else {
                      // In count mode, show count and percentage
                      const percentage = dataPoint?.[`${name}_percentage`] || 0;
                      return [`${value} conversations (${percentage.toFixed(1)}%)`, name];
                    }
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
                    return value.length > 30 ? value.substring(0, 27) + '...' : value;
                  }}
                />
                {timeSeriesTopics.map((topic, index) => (
                  <Bar
                    key={topic}
                    dataKey={topic}
                    stackId="topics"
                    fill={colors[index % colors.length]}
                    name={topic}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationTrendsChart;

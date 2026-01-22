import React, { useState, useEffect } from 'react';
import { Paper, Typography, Box, CircularProgress } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import axios from 'axios';

/**
 * Sentiment analysis line chart
 * Based on zilbers/dark-web-scraper LineChart
 */
export default function SentimentChart({ data, type = 'score', title = 'Sentiment Analysis' }) {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!data || data.length === 0) {
      setChartData([]);
      return;
    }

    const analyzeSentiment = async () => {
      setLoading(true);
      try {
        const { data: results } = await axios.post('/api/analytics/_sentiment', data);

        const formattedData = results.map((result, index) => ({
          index,
          score: result.score || 0,
          comparative: result.comparative || 0,
          words: result.words?.length || 0
        }));

        setChartData(formattedData);
      } catch (error) {
        console.error('Sentiment analysis error:', error);
        setChartData([]);
      } finally {
        setLoading(false);
      }
    };

    analyzeSentiment();
  }, [data]);

  const dataKey = type === 'score' ? 'score' : 'comparative';
  const lineColor = type === 'score' ? '#ff0055' : '#00ff88';

  // Calculate average
  const average = chartData.length > 0
    ? chartData.reduce((sum, d) => sum + d[dataKey], 0) / chartData.length
    : 0;

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper', height: 350 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 250 }}>
          <CircularProgress />
        </Box>
      ) : chartData.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 250 }}>
          <Typography color="text.secondary">No data available</Typography>
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4e" />
            <XAxis
              dataKey="index"
              stroke="#a0a0a0"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              stroke="#a0a0a0"
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a2e',
                border: '1px solid #2a2a4e',
                borderRadius: 4
              }}
              labelStyle={{ color: '#e0e0e0' }}
            />
            <ReferenceLine
              y={0}
              stroke="#666"
              strokeDasharray="3 3"
            />
            <ReferenceLine
              y={average}
              stroke="#ffaa00"
              strokeDasharray="5 5"
              label={{
                value: `Avg: ${average.toFixed(2)}`,
                fill: '#ffaa00',
                fontSize: 10
              }}
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: lineColor }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* Legend */}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3, mt: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 12, height: 12, bgcolor: lineColor, borderRadius: '50%' }} />
          <Typography variant="caption">{type === 'score' ? 'Threat Score' : 'Comparative'}</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 12, height: 2, bgcolor: '#ffaa00' }} />
          <Typography variant="caption">Average</Typography>
        </Box>
      </Box>
    </Paper>
  );
}

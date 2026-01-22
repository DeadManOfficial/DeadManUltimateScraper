import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  TextField,
  IconButton,
  CircularProgress
} from '@mui/material';
import { Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import axios from 'axios';

// Color palette
const COLORS = ['#00ff88', '#ff0055', '#00ccff', '#ffaa00', '#aa00ff', '#ff6600'];

/**
 * Keyword frequency pie chart
 * Based on zilbers/dark-web-scraper PieChart
 */
export default function KeywordPieChart({ initialWords = [], title = 'Keyword Distribution' }) {
  const [words, setWords] = useState(initialWords);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newWord, setNewWord] = useState('');

  // Fetch keyword counts
  useEffect(() => {
    if (words.length === 0) {
      setChartData([]);
      return;
    }

    const fetchCounts = async () => {
      setLoading(true);
      try {
        const promises = words.map(word =>
          axios.get(`/api/data/_label?q=${encodeURIComponent(word)}`)
        );

        const results = await Promise.all(promises);
        const data = results.map(r => ({
          name: r.data.label,
          value: r.data.value || 0
        }));

        setChartData(data.filter(d => d.value > 0));
      } catch (error) {
        console.error('Keyword count error:', error);
        setChartData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchCounts();
  }, [words]);

  // Add new word
  const handleAddWord = () => {
    if (newWord.trim() && !words.includes(newWord.trim().toLowerCase())) {
      setWords([...words, newWord.trim().toLowerCase()]);
      setNewWord('');
    }
  };

  // Remove word
  const handleRemoveWord = (word) => {
    setWords(words.filter(w => w !== word));
  };

  // Handle enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAddWord();
    }
  };

  // Custom label
  const renderLabel = ({ name, percent }) => {
    return `${name} (${(percent * 100).toFixed(0)}%)`;
  };

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper', height: 400 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>

      {/* Word input */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          size="small"
          placeholder="Add keyword..."
          value={newWord}
          onChange={(e) => setNewWord(e.target.value)}
          onKeyPress={handleKeyPress}
          sx={{ flexGrow: 1 }}
        />
        <IconButton onClick={handleAddWord} color="primary" size="small">
          <AddIcon />
        </IconButton>
      </Box>

      {/* Word chips */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2, maxHeight: 60, overflow: 'auto' }}>
        {words.map((word, index) => (
          <Chip
            key={word}
            label={word}
            size="small"
            onDelete={() => handleRemoveWord(word)}
            deleteIcon={<CloseIcon />}
            sx={{
              bgcolor: COLORS[index % COLORS.length] + '33',
              borderColor: COLORS[index % COLORS.length],
              borderWidth: 1,
              borderStyle: 'solid'
            }}
          />
        ))}
      </Box>

      {/* Chart */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <CircularProgress />
        </Box>
      ) : chartData.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Typography color="text.secondary">
            {words.length === 0 ? 'Add keywords to track' : 'No matches found'}
          </Typography>
        </Box>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              outerRadius={80}
              innerRadius={40}
              paddingAngle={2}
              dataKey="value"
              label={renderLabel}
              labelLine={{ stroke: '#a0a0a0' }}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                  stroke="none"
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a2e',
                border: '1px solid #2a2a4e',
                borderRadius: 4
              }}
              formatter={(value, name) => [value, name]}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </Paper>
  );
}

import React, { useState, useRef, useCallback, useContext } from 'react';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  FormControlLabel,
  Checkbox,
  Box,
  Typography,
  Chip,
  CircularProgress
} from '@mui/material';
import axios from 'axios';
import { UserContext } from '../context/UserContext';
import useInfiniteScroll from '../hooks/useInfiniteScroll';

const columns = [
  { id: 'title', label: 'Title', minWidth: 200 },
  { id: 'content', label: 'Content', minWidth: 300 },
  { id: 'domain', label: 'Domain', minWidth: 120 },
  { id: 'scraped_at', label: 'Date', minWidth: 150 },
];

/**
 * Data table with infinite scroll
 * Based on zilbers/dark-web-scraper Bins component
 */
export default function DataTable({ hiding, setHiding, data }) {
  const { userId } = useContext(UserContext);
  const [pageNumber, setPageNumber] = useState(0);
  const [search, setSearch] = useState('');
  const [showAll, setShowAll] = useState(false);

  const { logs, hasMore, loading, error } = useInfiniteScroll(
    pageNumber,
    search,
    userId
  );

  const observer = useRef();

  // Intersection observer for infinite scroll
  const lastLogElementRef = useCallback((node) => {
    if (loading) return;

    if (observer.current) observer.current.disconnect();

    observer.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore) {
        setPageNumber(prev => prev + 1);
      }
    });

    if (node) observer.current.observe(node);
  }, [loading, hasMore]);

  // Hide item
  const handleHide = async (id) => {
    const newHiding = [...hiding, id];
    setHiding(newHiding);

    try {
      await axios.put(`/api/user/_alerts?id=${userId}`, newHiding);
    } catch (error) {
      console.error('Failed to hide item:', error);
    }
  };

  // Handle search change
  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPageNumber(0);
  };

  // Filter logs
  const visibleLogs = showAll
    ? logs
    : logs.filter(item => !hiding.includes(item.id));

  // Truncate text
  const truncate = (text, max = 100) => {
    if (!text) return '';
    return text.length > max ? `${text.substring(0, max)}...` : text;
  };

  return (
    <Paper sx={{ bgcolor: 'background.paper', p: 2 }}>
      {/* Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <TextField
          size="small"
          label="Filter"
          value={search}
          onChange={handleSearchChange}
          sx={{ minWidth: 200 }}
        />

        <FormControlLabel
          control={
            <Checkbox
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
              size="small"
            />
          }
          label="Show All"
        />
      </Box>

      {/* Table */}
      <TableContainer sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  sx={{
                    minWidth: column.minWidth,
                    bgcolor: 'background.default',
                    fontWeight: 600
                  }}
                >
                  {column.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {visibleLogs.map((row, index) => {
              const isLast = visibleLogs.length === index + 1;

              return (
                <TableRow
                  ref={isLast ? lastLogElementRef : null}
                  key={row.id || index}
                  hover
                  onClick={() => !showAll && handleHide(row.id)}
                  sx={{
                    cursor: showAll ? 'default' : 'pointer',
                    '&:hover': {
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {row.is_onion && (
                        <Chip label="ONION" size="small" color="secondary" />
                      )}
                      <Typography variant="body2">
                        {truncate(row.title || row.url, 50)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {truncate(row.content, 150)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={row.domain || 'Unknown'}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {row.scraped_at ? new Date(row.scraped_at).toLocaleString() : '-'}
                    </Typography>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Loading indicator */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {/* Error message */}
      {error && (
        <Typography color="error" align="center" sx={{ py: 2 }}>
          Failed to load data
        </Typography>
      )}

      {/* No more data */}
      {!hasMore && visibleLogs.length > 0 && (
        <Typography color="text.secondary" align="center" sx={{ py: 1 }}>
          No more data
        </Typography>
      )}
    </Paper>
  );
}

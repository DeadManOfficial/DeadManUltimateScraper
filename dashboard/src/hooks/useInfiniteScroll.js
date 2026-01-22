import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

/**
 * Custom hook for infinite scroll pagination
 * Based on zilbers/dark-web-scraper patterns
 */
export default function useInfiniteScroll(pageNumber, search, userId) {
  const [logs, setLogs] = useState([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Reset when search changes
  useEffect(() => {
    setLogs([]);
    setHasMore(true);
  }, [search]);

  // Fetch data
  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      setLoading(true);
      setError(false);

      try {
        const params = new URLSearchParams({
          size: '10',
          ...(search && { q: search }),
          ...(userId && { id: userId })
        });

        const { data } = await axios.get(`/api/data/_bins/${pageNumber}?${params}`, {
          signal: controller.signal
        });

        setLogs(prev => {
          // Avoid duplicates
          const existingIds = new Set(prev.map(item => item.id));
          const newItems = data.filter(item => !existingIds.has(item.id));
          return [...prev, ...newItems];
        });

        setHasMore(data.length === 10);
      } catch (err) {
        if (err.name !== 'CanceledError') {
          setError(true);
          console.error('Infinite scroll error:', err);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    return () => controller.abort();
  }, [pageNumber, search, userId]);

  const reset = useCallback(() => {
    setLogs([]);
    setHasMore(true);
  }, []);

  return { logs, hasMore, loading, error, reset };
}

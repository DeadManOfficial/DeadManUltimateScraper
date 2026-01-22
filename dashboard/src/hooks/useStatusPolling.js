import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

/**
 * Custom hook for scraper status polling
 * Based on zilbers/dark-web-scraper patterns
 */
export default function useStatusPolling(interval = 15000) {
  const [status, setStatus] = useState({
    active: false,
    message: 'Idle',
    checked: false,
    last_run: null
  });
  const [loading, setLoading] = useState(true);

  // Fetch status
  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/status');
      setStatus(data);
    } catch (error) {
      console.error('Status fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Mark as checked
  const markChecked = useCallback(async () => {
    try {
      const { data } = await axios.get('/api/status/_check');
      setStatus(data);
    } catch (error) {
      console.error('Mark checked error:', error);
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus();

    const pollInterval = setInterval(fetchStatus, interval);

    return () => clearInterval(pollInterval);
  }, [fetchStatus, interval]);

  // Determine status color
  const getStatusColor = () => {
    if (status.active) return 'success';
    if (status.message?.includes('cooldown')) return 'warning';
    if (status.message?.includes('error')) return 'error';
    return 'default';
  };

  // Check if on cooldown
  const isOnCooldown = () => {
    return /On [0-9]+ minutes cooldown!/g.test(status.message);
  };

  return {
    status,
    loading,
    fetchStatus,
    markChecked,
    getStatusColor,
    isOnCooldown
  };
}

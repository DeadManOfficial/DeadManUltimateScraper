import { useState, useCallback } from 'react';
import AwesomeDebouncePromise from 'awesome-debounce-promise';

/**
 * Custom hook for debounced search
 * Based on zilbers/dark-web-scraper patterns
 */
export default function useDebouncedSearch(searchFunction, delay = 300) {
  const [inputText, setInputText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  // Create debounced search function
  const debouncedSearch = useCallback(
    AwesomeDebouncePromise(searchFunction, delay),
    [searchFunction, delay]
  );

  // Handle input change
  const handleInputChange = async (text) => {
    setInputText(text);

    if (text.length === 0) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const results = await debouncedSearch(text);
      setSearchResults(results || []);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  return {
    inputText,
    setInputText: handleInputChange,
    searchResults,
    loading
  };
}

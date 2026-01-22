import React, { useEffect, useState, useContext } from 'react';
import { Box, Container, Grid } from '@mui/material';
import axios from 'axios';
import TopBar from './components/TopBar';
import DataTable from './components/DataTable';
import SentimentChart from './components/SentimentChart';
import KeywordPieChart from './components/KeywordPieChart';
import SettingsModal from './components/SettingsModal';
import { UserContext } from './context/UserContext';
import useDebouncedSearch from './hooks/useDebouncedSearch';

// Search function
async function searchInDb(query) {
  if (!query) return [];
  const { data: results } = await axios.get(`/api/data/_search?q=${query}`);
  return results;
}

const useSearchInDb = () => useDebouncedSearch((text) => searchInDb(text));

function App() {
  const { userId } = useContext(UserContext);
  const [data, setData] = useState([]);
  const [hiding, setHiding] = useState([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { inputText, setInputText, searchResults } = useSearchInDb();

  // Fetch all data
  const getData = async () => {
    try {
      const { data: results } = await axios.get('/api/data');
      setData(results);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  // Fetch hidden items
  const getHiding = async () => {
    try {
      const { data: results } = await axios.get(`/api/user/_alerts?id=${userId}`);
      setHiding(results.hiding || []);
    } catch (error) {
      console.error('Failed to fetch hiding:', error);
    }
  };

  useEffect(() => {
    getData();
    if (userId) {
      getHiding();
    }
  }, [userId]);

  // Visible data (filtered by hidden items)
  const visibleData = searchResults.length > 0
    ? searchResults
    : data.filter(item => !hiding.includes(item.id));

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <TopBar
        length={data.length - hiding.length}
        deleted={hiding.length}
        inputText={inputText}
        setInputText={setInputText}
        setHiding={setHiding}
        getData={getData}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Grid container spacing={3}>
          {/* Data Table */}
          <Grid item xs={12}>
            <DataTable
              hiding={hiding}
              setHiding={setHiding}
              data={data}
            />
          </Grid>

          {/* Charts Row */}
          <Grid item xs={12} md={6}>
            <SentimentChart
              data={visibleData}
              type="score"
              title="Threat Score"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <SentimentChart
              data={visibleData}
              type="comparative"
              title="Comparative Analysis"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <KeywordPieChart
              initialWords={['bitcoin', 'weapons', 'stolen', 'credit', 'passwords']}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <KeywordPieChart
              initialWords={['ransomware', 'leaked', 'hacked', 'exploit', 'malware']}
              title="Threat Keywords"
            />
          </Grid>
        </Grid>
      </Container>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </Box>
  );
}

export default App;

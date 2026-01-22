import React, { useState, useEffect, useContext } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Slider,
  Typography,
  Box,
  Chip,
  IconButton,
  Divider,
  Alert
} from '@mui/material';
import { Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import axios from 'axios';
import { UserContext } from '../context/UserContext';

/**
 * Settings modal for scraper configuration
 * Based on zilbers/dark-web-scraper Modal
 */
export default function SettingsModal({ open, onClose }) {
  const { userId } = useContext(UserContext);
  const [keywords, setKeywords] = useState([]);
  const [newKeyword, setNewKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  const { control, handleSubmit, reset, setValue } = useForm({
    defaultValues: {
      cooldown_minutes: 5,
      use_tor: true,
      use_llm: false,
      darkweb_enabled: true,
      extract_strategy: 'auto'
    }
  });

  // Load config
  useEffect(() => {
    if (!open || !userId) return;

    const loadConfig = async () => {
      try {
        const { data } = await axios.get(`/api/user/_config?id=${userId}`);

        reset({
          cooldown_minutes: data.cooldown_minutes || 5,
          use_tor: data.use_tor ?? true,
          use_llm: data.use_llm ?? false,
          darkweb_enabled: data.darkweb_enabled ?? true,
          extract_strategy: data.extract_strategy || 'auto'
        });

        setKeywords(data.keywords || []);
      } catch (error) {
        console.error('Failed to load config:', error);
      }
    };

    loadConfig();
  }, [open, userId, reset]);

  // Save config
  const onSubmit = async (formData) => {
    setLoading(true);
    setSaved(false);

    try {
      await axios.put(`/api/user/_config?id=${userId}`, {
        ...formData,
        keywords
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setLoading(false);
    }
  };

  // Add keyword
  const handleAddKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()]);
      setNewKeyword('');
    }
  };

  // Remove keyword
  const handleRemoveKeyword = (keyword) => {
    setKeywords(keywords.filter(k => k !== keyword));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ bgcolor: 'background.paper' }}>
        Scraper Configuration
      </DialogTitle>

      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent sx={{ bgcolor: 'background.default' }}>
          {saved && (
            <Alert severity="success" sx={{ mb: 2 }}>
              Configuration saved successfully!
            </Alert>
          )}

          {/* Cooldown Slider */}
          <Box sx={{ mb: 3 }}>
            <Typography gutterBottom>
              Cooldown Period (minutes)
            </Typography>
            <Controller
              name="cooldown_minutes"
              control={control}
              render={({ field }) => (
                <Slider
                  {...field}
                  min={1}
                  max={60}
                  marks={[
                    { value: 1, label: '1' },
                    { value: 15, label: '15' },
                    { value: 30, label: '30' },
                    { value: 60, label: '60' }
                  ]}
                  valueLabelDisplay="auto"
                />
              )}
            />
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Toggles */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
            <Controller
              name="use_tor"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Switch {...field} checked={field.value} />}
                  label="Use TOR Proxy"
                />
              )}
            />

            <Controller
              name="darkweb_enabled"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Switch {...field} checked={field.value} />}
                  label="Enable Darkweb Scraping"
                />
              )}
            />

            <Controller
              name="use_llm"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Switch {...field} checked={field.value} />}
                  label="Enable LLM Analysis"
                />
              )}
            />
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Keywords */}
          <Box>
            <Typography gutterBottom>
              Search Keywords
            </Typography>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                size="small"
                placeholder="Add keyword..."
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKeyword())}
                fullWidth
              />
              <IconButton onClick={handleAddKeyword} color="primary">
                <AddIcon />
              </IconButton>
            </Box>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxHeight: 150, overflow: 'auto' }}>
              {keywords.map((keyword) => (
                <Chip
                  key={keyword}
                  label={keyword}
                  size="small"
                  onDelete={() => handleRemoveKeyword(keyword)}
                  deleteIcon={<CloseIcon />}
                />
              ))}
            </Box>
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Extract Strategy */}
          <Controller
            name="extract_strategy"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                select
                label="Extraction Strategy"
                fullWidth
                SelectProps={{ native: true }}
              >
                <option value="auto">Auto Detect</option>
                <option value="text">Text Only</option>
                <option value="json">JSON Extract</option>
                <option value="links">Links Only</option>
                <option value="selector">CSS Selector</option>
              </TextField>
            )}
          />
        </DialogContent>

        <DialogActions sx={{ bgcolor: 'background.paper', px: 3, py: 2 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Configuration'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

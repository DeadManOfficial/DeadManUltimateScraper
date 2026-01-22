import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  TextField,
  Badge,
  IconButton,
  Chip,
  Box,
  Button,
  InputAdornment
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon
} from '@mui/icons-material';
import useStatusPolling from '../hooks/useStatusPolling';

/**
 * Top navigation bar with status, search, and controls
 * Based on zilbers/dark-web-scraper AppBar
 */
export default function TopBar({
  length,
  deleted,
  inputText,
  setInputText,
  setHiding,
  getData,
  onSettingsClick
}) {
  const { status, getStatusColor, isOnCooldown } = useStatusPolling();

  // Reset hidden items
  const handleResetBins = () => {
    setHiding([]);
  };

  // Get status chip color
  const getChipColor = () => {
    if (status.active) return 'success';
    if (isOnCooldown()) return 'warning';
    return 'default';
  };

  return (
    <AppBar position="static" sx={{ bgcolor: 'background.paper' }}>
      <Toolbar sx={{ gap: 2, flexWrap: 'wrap', py: 1 }}>
        {/* Logo */}
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            background: 'linear-gradient(45deg, #00ff88, #00ccff)',
            backgroundClip: 'text',
            textFillColor: 'transparent',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          DEADMAN SCRAPER
        </Typography>

        {/* Status Chip */}
        <Chip
          label={status.message || 'Idle'}
          color={getChipColor()}
          size="small"
          sx={{
            fontWeight: 500,
            animation: status.active ? 'pulse 2s infinite' : 'none',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1 },
              '50%': { opacity: 0.7 }
            }
          }}
        />

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Search Field */}
        <TextField
          size="small"
          placeholder="Search..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
          }}
          sx={{
            width: 250,
            '& .MuiOutlinedInput-root': {
              bgcolor: 'background.default',
            }
          }}
        />

        {/* Badges */}
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Badge badgeContent={length} color="primary" max={9999}>
            <Chip
              icon={<VisibilityIcon />}
              label="Visible"
              size="small"
              variant="outlined"
            />
          </Badge>

          <Badge badgeContent={deleted} color="error" max={9999}>
            <Chip
              icon={<VisibilityOffIcon />}
              label="Hidden"
              size="small"
              variant="outlined"
              onClick={handleResetBins}
              sx={{ cursor: 'pointer' }}
            />
          </Badge>
        </Box>

        {/* Actions */}
        <Button
          size="small"
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={getData}
        >
          Refresh
        </Button>

        <IconButton
          onClick={onSettingsClick}
          sx={{ color: 'text.primary' }}
        >
          <SettingsIcon />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}

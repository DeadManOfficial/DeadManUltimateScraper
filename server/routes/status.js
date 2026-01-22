/**
 * Status routes - Scraper status and control
 * Based on zilbers/dark-web-scraper patterns
 */

const { Router } = require('express');

const router = Router();

// In-memory status (can be moved to Redis for persistence)
let scraperStatus = {
  active: false,
  message: 'Idle',
  checked: false,
  last_run: null,
  updated_at: new Date().toISOString()
};

// Get scraper status
router.get('/', async (req, res) => {
  try {
    res.json(scraperStatus);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Mark status as checked (user has seen it)
router.get('/_check', async (req, res) => {
  try {
    scraperStatus.checked = true;
    res.json(scraperStatus);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update scraper status
router.post('/', async (req, res) => {
  try {
    const { active, message } = req.body;

    scraperStatus = {
      active: Boolean(active),
      message: message || (active ? 'Scraping!' : 'Idle'),
      checked: false,
      last_run: active ? new Date().toISOString() : scraperStatus.last_run,
      updated_at: new Date().toISOString()
    };

    // Emit real-time status update
    const io = req.app.get('io');
    if (io) {
      io.to('status-updates').emit('status:changed', scraperStatus);
    }

    res.json({ success: true, status: scraperStatus });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start scraper
router.post('/_start', async (req, res) => {
  try {
    scraperStatus = {
      active: true,
      message: 'Scraping!',
      checked: false,
      last_run: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    const io = req.app.get('io');
    if (io) {
      io.to('status-updates').emit('status:changed', scraperStatus);
    }

    res.json({ success: true, status: scraperStatus });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Stop scraper
router.post('/_stop', async (req, res) => {
  try {
    scraperStatus = {
      active: false,
      message: 'Stopped',
      checked: false,
      last_run: scraperStatus.last_run,
      updated_at: new Date().toISOString()
    };

    const io = req.app.get('io');
    if (io) {
      io.to('status-updates').emit('status:changed', scraperStatus);
    }

    res.json({ success: true, status: scraperStatus });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Set cooldown
router.post('/_cooldown', async (req, res) => {
  try {
    const { minutes } = req.body;

    scraperStatus = {
      active: false,
      message: `On ${minutes} minutes cooldown!`,
      checked: false,
      last_run: scraperStatus.last_run,
      updated_at: new Date().toISOString()
    };

    const io = req.app.get('io');
    if (io) {
      io.to('status-updates').emit('status:changed', scraperStatus);
    }

    res.json({ success: true, status: scraperStatus });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;

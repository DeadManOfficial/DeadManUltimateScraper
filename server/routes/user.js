/**
 * User routes - Configuration and preferences
 * Based on zilbers/dark-web-scraper patterns
 *
 * Security fixes applied:
 * - Sanitized error responses
 * - Input validation
 */

const { Router } = require('express');
const User = require('../models/User');

const router = Router();

// Sanitize error for client response
function sanitizeError(error) {
  const isProduction = process.env.NODE_ENV === 'production';
  return isProduction ? 'User operation failed' : error.message;
}

// Get all users
router.get('/_all', async (req, res) => {
  try {
    const users = await User.find({ deletedAt: { $exists: false } })
      .select('-password')
      .lean();

    res.json(users.map(u => ({ ...u, id: u._id.toString() })));
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Get user alerts (hidden items)
router.get('/_alerts', async (req, res) => {
  try {
    const { id } = req.query;

    if (!id) {
      return res.status(400).json({ error: 'User ID required' });
    }

    const user = await User.findById(id).select('alerts').lean();

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ hiding: user.alerts || [] });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Update user alerts
router.put('/_alerts', async (req, res) => {
  try {
    const { id } = req.query;
    const alerts = req.body;

    if (!id) {
      return res.status(400).json({ error: 'User ID required' });
    }

    const user = await User.findByIdAndUpdate(
      id,
      { alerts: Array.isArray(alerts) ? alerts : [] },
      { new: true }
    ).select('alerts');

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ hiding: user.alerts });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Get user config
router.get('/_config', async (req, res) => {
  try {
    const { id } = req.query;

    if (!id) {
      // Return default user config
      const defaultUser = await User.ensureDefaultUser();
      return res.json(defaultUser.config);
    }

    const user = await User.findById(id).select('config').lean();

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user.config);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Update user config
router.put('/_config', async (req, res) => {
  try {
    const { id } = req.query;
    const config = req.body;

    if (!id) {
      return res.status(400).json({ error: 'User ID required' });
    }

    const user = await User.findByIdAndUpdate(
      id,
      { config },
      { new: true }
    ).select('config');

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Emit config update event
    const io = req.app.get('io');
    if (io) {
      io.to('status-updates').emit('config:updated', {
        userId: id,
        timestamp: new Date().toISOString()
      });
    }

    res.json(user.config);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Create new user
router.post('/_new', async (req, res) => {
  try {
    const { email, name, password } = req.body;

    if (!email || !name) {
      return res.status(400).json({ error: 'Email and name required' });
    }

    const user = await User.create({ email, name, password });

    res.status(201).json({
      id: user._id.toString(),
      email: user.email,
      name: user.name,
      config: user.config
    });
  } catch (error) {
    if (error.code === 11000) {
      res.status(409).json({ error: 'Email already exists' });
    } else {
      res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
    }
  }
});

// Get user by ID
router.get('/:id', async (req, res) => {
  try {
    const user = await User.findById(req.params.id)
      .select('-password')
      .lean();

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ ...user, id: user._id.toString() });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Update user
router.put('/:id', async (req, res) => {
  try {
    const updates = req.body;
    delete updates.password;  // Don't allow password update via this endpoint

    const user = await User.findByIdAndUpdate(
      req.params.id,
      updates,
      { new: true }
    ).select('-password');

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ ...user.toObject(), id: user._id.toString() });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

// Delete user (soft delete)
router.delete('/:id', async (req, res) => {
  try {
    const user = await User.findByIdAndUpdate(
      req.params.id,
      { deletedAt: new Date() },
      { new: true }
    );

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ deleted: true });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'USER_ERROR' });
  }
});

module.exports = router;

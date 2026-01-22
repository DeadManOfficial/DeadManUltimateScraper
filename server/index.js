/**
 * DEADMAN ULTIMATE SCRAPER - API Server
 * ======================================
 * Express.js REST API for dashboard and scraper coordination.
 *
 * Endpoints:
 * - /api/data: Scraped data CRUD and search
 * - /api/user: User configuration and preferences
 * - /api/status: Scraper status and control
 * - /api/analytics: Sentiment and keyword analytics
 *
 * Based on zilbers/dark-web-scraper patterns, enhanced for DeadMan.
 */

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { auth } = require('express-oauth2-jwt-bearer');
const { createServer } = require('http');
const { Server } = require('socket.io');

// Import routes
const dataRoutes = require('./routes/data');
const userRoutes = require('./routes/user');
const statusRoutes = require('./routes/status');
const analyticsRoutes = require('./routes/analytics');

// Import database connections
const { connectElasticsearch } = require('./db/elasticsearch');
const { connectMongoDB } = require('./db/mongodb');

const app = express();
const httpServer = createServer(app);

// Socket.IO for real-time updates
const io = new Server(httpServer, {
  cors: {
    origin: process.env.CORS_ORIGIN || '*',
    methods: ['GET', 'POST']
  }
});

// Make io accessible to routes
app.set('io', io);

// ============================================
// SECURITY: Auth0 JWT Validation
// ============================================

const checkJwt = auth({
  audience: process.env.AUTH0_AUDIENCE || 'https://officialdeadman.us.auth0.com/api/v2/',
  issuerBaseURL: process.env.AUTH0_ISSUER || 'https://officialdeadman.us.auth0.com/',
  tokenSigningAlg: 'RS256'
});

// Optional auth - allows unauthenticated for health/status, required for data
const optionalAuth = (req, res, next) => {
  // Skip auth for health checks and status polling
  if (req.path === '/api/health' || req.path === '/api/status') {
    return next();
  }
  // Skip auth in development mode if AUTH0_DISABLED is set
  if (process.env.AUTH0_DISABLED === 'true') {
    return next();
  }
  return checkJwt(req, res, next);
};

// ============================================
// SECURITY: Rate Limiting
// ============================================

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per window per IP
  message: { error: 'Too many requests, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => req.path === '/api/health' // Skip health checks
});

const searchLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 30, // 30 searches per minute
  message: { error: 'Search rate limit exceeded.' }
});

const bulkLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 10, // 10 bulk inserts per minute
  message: { error: 'Bulk insert rate limit exceeded.' }
});

// ============================================
// MIDDLEWARE
// ============================================

app.use(helmet({
  contentSecurityPolicy: false  // Disable for dashboard
}));
app.use(compression());

// CORS with restricted origins in production
const corsOptions = {
  origin: process.env.NODE_ENV === 'production'
    ? (process.env.CORS_ORIGIN || 'http://localhost:3000').split(',')
    : '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
};
app.use(cors(corsOptions));

app.use(morgan('combined'));
app.use(express.json({ limit: '1mb' })); // Reduced from 10mb
app.use(express.urlencoded({ extended: true }));

// Apply rate limiting to all API routes
app.use('/api', apiLimiter);

// Serve static dashboard build
app.use(express.static('build'));

// ============================================
// ROUTES (with authentication and rate limiting)
// ============================================

// Data routes - require auth, apply search/bulk limiters
app.use('/api/data/_search', searchLimiter);
app.use('/api/data/_label', searchLimiter);
app.use('/api/data/_bins', searchLimiter);
app.use('/api/data', optionalAuth, dataRoutes);

// User routes - require auth
app.use('/api/user', optionalAuth, userRoutes);

// Status routes - public (for dashboard polling)
app.use('/api/status', statusRoutes);

// Analytics routes - require auth
app.use('/api/analytics', optionalAuth, analyticsRoutes);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    services: {
      elasticsearch: app.get('esConnected') || false,
      mongodb: app.get('mongoConnected') || false
    }
  });
});

// Catch-all for SPA routing
app.get('*', (req, res) => {
  res.sendFile('index.html', { root: 'build' });
});

// Error handling middleware - sanitized for production
app.use((err, req, res, next) => {
  // Log full error internally
  console.error('Error:', err.stack || err.message);

  // Handle Auth0 errors
  if (err.name === 'UnauthorizedError' || err.status === 401) {
    return res.status(401).json({
      error: 'Unauthorized',
      code: 'AUTH_REQUIRED',
      timestamp: new Date().toISOString()
    });
  }

  // Sanitize error response for production
  const isProduction = process.env.NODE_ENV === 'production';
  res.status(err.status || 500).json({
    error: isProduction ? 'Internal server error' : err.message,
    code: err.code || 'INTERNAL_ERROR',
    timestamp: new Date().toISOString()
  });
});

// ============================================
// SOCKET.IO EVENTS
// ============================================

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('subscribe:status', () => {
    socket.join('status-updates');
  });

  socket.on('subscribe:data', () => {
    socket.join('data-updates');
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// ============================================
// SERVER STARTUP
// ============================================

const PORT = process.env.PORT || 8080;

async function startServer() {
  try {
    // Connect to databases
    const esClient = await connectElasticsearch();
    app.set('esClient', esClient);
    app.set('esConnected', true);
    console.log('✓ Elasticsearch connected');

    const mongoose = await connectMongoDB();
    app.set('mongoConnected', true);
    console.log('✓ MongoDB connected');

    // Start server
    httpServer.listen(PORT, () => {
      console.log(`
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   DEADMAN ULTIMATE SCRAPER - API Server              ║
║                                                      ║
║   Port: ${PORT}                                          ║
║   Mode: ${process.env.NODE_ENV || 'development'}                              ║
║                                                      ║
║   Endpoints:                                         ║
║   • /api/data      - Scraped data                    ║
║   • /api/user      - User configuration              ║
║   • /api/status    - Scraper status                  ║
║   • /api/analytics - Sentiment analysis              ║
║   • /api/health    - Health check                    ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
      `);
    });

  } catch (error) {
    console.error('Failed to start server:', error.message);
    process.exit(1);
  }
}

startServer();

module.exports = { app, io };

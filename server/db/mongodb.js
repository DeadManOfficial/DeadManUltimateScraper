/**
 * MongoDB connection
 */

const mongoose = require('mongoose');

async function connectMongoDB() {
  const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/deadman_scraper';

  await mongoose.connect(uri);

  mongoose.connection.on('error', (err) => {
    console.error('MongoDB connection error:', err);
  });

  mongoose.connection.on('disconnected', () => {
    console.warn('MongoDB disconnected');
  });

  return mongoose;
}

module.exports = { connectMongoDB };

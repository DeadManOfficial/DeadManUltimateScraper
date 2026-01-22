/**
 * User model for MongoDB
 */

const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  name: {
    type: String,
    required: true,
    trim: true
  },
  password: {
    type: String,
    required: false  // Optional for default user
  },
  config: {
    target_urls: { type: [String], default: [] },
    keywords: {
      type: [String],
      default: ['DDOS', 'exploits', 'credit cards', 'bitcoin', 'passwords',
                'hacked', 'ransomware', 'stolen', 'leaked', 'fullz']
    },
    cooldown_minutes: { type: Number, default: 5, min: 1, max: 60 },
    use_tor: { type: Boolean, default: true },
    use_llm: { type: Boolean, default: false },
    extract_strategy: { type: String, default: 'auto' },
    notifications_enabled: { type: Boolean, default: true },
    darkweb_enabled: { type: Boolean, default: true }
  },
  alerts: {
    type: [String],  // Hidden item IDs
    default: []
  },
  last_login: {
    type: Date,
    default: null
  }
}, {
  timestamps: true
});

// Ensure default user exists
userSchema.statics.ensureDefaultUser = async function() {
  const defaultEmail = 'default@deadman.local';
  let user = await this.findOne({ email: defaultEmail });

  if (!user) {
    user = await this.create({
      email: defaultEmail,
      name: 'DeadMan'
    });
  }

  return user;
};

const User = mongoose.model('User', userSchema);

module.exports = User;

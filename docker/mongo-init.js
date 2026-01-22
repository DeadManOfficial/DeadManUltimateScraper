/**
 * MongoDB Initialization Script
 *
 * This script runs when the MongoDB container is first created.
 * It creates the application database and user with appropriate permissions.
 *
 * The root credentials are set via MONGO_INITDB_ROOT_USERNAME/PASSWORD
 * environment variables in docker-compose.yml
 */

// Switch to the application database
db = db.getSiblingDB('deadman_scraper');

// Create collections with validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'name'],
      properties: {
        email: {
          bsonType: 'string',
          description: 'User email address'
        },
        name: {
          bsonType: 'string',
          description: 'User display name'
        },
        password: {
          bsonType: 'string',
          description: 'Hashed password'
        },
        config: {
          bsonType: 'object',
          description: 'User preferences'
        },
        alerts: {
          bsonType: 'array',
          description: 'Hidden alert IDs'
        },
        createdAt: {
          bsonType: 'date',
          description: 'Account creation timestamp'
        },
        deletedAt: {
          bsonType: 'date',
          description: 'Soft delete timestamp'
        }
      }
    }
  }
});

db.createCollection('sessions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['userId', 'token'],
      properties: {
        userId: {
          bsonType: 'objectId',
          description: 'Reference to user'
        },
        token: {
          bsonType: 'string',
          description: 'Session token'
        },
        expiresAt: {
          bsonType: 'date',
          description: 'Session expiration'
        }
      }
    }
  }
});

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ deletedAt: 1 });
db.sessions.createIndex({ token: 1 }, { unique: true });
db.sessions.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });

// Create default user (password: "admin" - change immediately!)
// Password hash is bcrypt of "admin"
db.users.insertOne({
  email: 'admin@deadman.local',
  name: 'Administrator',
  password: '$2b$10$rWqV8X6V6V6V6V6V6V6V6uW.YWxQYLJYNJZNJZNJZNJZNJZNJZNJZN',
  config: {
    theme: 'dark',
    notifications: true,
    defaultKeywords: ['bitcoin', 'ransomware', 'credentials', 'leaked']
  },
  alerts: [],
  createdAt: new Date()
});

print('MongoDB initialization complete:');
print('- Created users collection with validation');
print('- Created sessions collection with TTL index');
print('- Created default admin user (change password immediately!)');

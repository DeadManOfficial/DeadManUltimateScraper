/**
 * Elasticsearch connection and utilities
 *
 * Security: Supports X-Pack authentication via environment variables.
 */

const { Client } = require('@elastic/elasticsearch');

const INDEX_NAME = process.env.ELASTICSEARCH_INDEX || 'deadman_scrapes';

// Index mappings
const DATA_MAPPINGS = {
  properties: {
    url: { type: 'keyword' },
    title: {
      type: 'text',
      fields: { keyword: { type: 'keyword', ignore_above: 256 } }
    },
    content: {
      type: 'text',
      fields: { keyword: { type: 'keyword', ignore_above: 256 } }
    },
    author: {
      type: 'text',
      fields: { keyword: { type: 'keyword', ignore_above: 256 } }
    },
    source: { type: 'keyword' },
    domain: { type: 'keyword' },
    scraped_at: { type: 'date', format: 'yyyy-MM-dd HH:mm:ss||epoch_millis' },
    is_onion: { type: 'boolean' },
    fetch_layer: { type: 'keyword' },
    status_code: { type: 'integer' },
    sentiment_score: { type: 'float' },
    sentiment_comparative: { type: 'float' },
    keywords_found: { type: 'keyword' }
  }
};

let client = null;

async function connectElasticsearch() {
  const host = process.env.ELASTICSEARCH_HOST || 'http://localhost:9200';
  const username = process.env.ELASTIC_USERNAME;
  const password = process.env.ELASTIC_PASSWORD;

  // Build client config
  const clientConfig = {
    node: host,
    maxRetries: 5,
    requestTimeout: 60000
  };

  // Add authentication if credentials provided
  if (username && password) {
    clientConfig.auth = {
      username,
      password
    };
    console.log('Elasticsearch: Using authenticated connection');
  } else {
    console.log('Elasticsearch: Using unauthenticated connection (not recommended for production)');
  }

  client = new Client(clientConfig);

  // Test connection
  await client.ping();

  // Ensure index exists
  const exists = await client.indices.exists({ index: INDEX_NAME });
  if (!exists) {
    await client.indices.create({
      index: INDEX_NAME,
      body: {
        settings: {
          number_of_shards: 1,
          number_of_replicas: 0
        },
        mappings: DATA_MAPPINGS
      }
    });
    console.log(`Created index: ${INDEX_NAME}`);
  }

  return client;
}

function getClient() {
  return client;
}

function getIndexName() {
  return INDEX_NAME;
}

module.exports = {
  connectElasticsearch,
  getClient,
  getIndexName,
  DATA_MAPPINGS
};

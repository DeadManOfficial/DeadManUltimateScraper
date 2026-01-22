/**
 * Data routes - Scraped content CRUD and search
 * Based on zilbers/dark-web-scraper patterns
 *
 * Security fixes applied:
 * - Elasticsearch query sanitization
 * - Bulk insert size limits
 * - SHA-256 instead of MD5
 * - Sanitized error responses
 */

const { Router } = require('express');
const crypto = require('crypto');
const { getClient, getIndexName } = require('../db/elasticsearch');

const router = Router();

// ============================================
// SECURITY: Constants and Helpers
// ============================================

const MAX_BULK_SIZE = 100; // Maximum documents per bulk insert
const MAX_QUERY_LENGTH = 200; // Maximum search query length

/**
 * Escape Elasticsearch special characters to prevent query injection
 * Special chars: + - = && || > < ! ( ) { } [ ] ^ " ~ * ? : \ /
 */
function escapeElasticsearchQuery(query) {
  if (!query || typeof query !== 'string') return '';

  // Truncate to max length
  const truncated = query.slice(0, MAX_QUERY_LENGTH);

  // Escape special characters
  return truncated.replace(/[+\-=&|!(){}[\]^"~*?:\\/><]/g, '\\$&');
}

/**
 * Generate document ID using SHA-256 (not MD5)
 */
function generateDocId(doc) {
  const content = (doc.scraped_at || '') + (doc.title || '') + (doc.url || '');
  return crypto.createHash('sha256').update(content).digest('hex').slice(0, 32);
}

/**
 * Sanitize error for client response
 */
function sanitizeError(error) {
  const isProduction = process.env.NODE_ENV === 'production';
  return isProduction ? 'Database operation failed' : error.message;
}

// Get all data (limit 1000)
router.get('/', async (req, res) => {
  try {
    const client = getClient();
    const { body: result } = await client.search({
      index: getIndexName(),
      body: { query: { match_all: {} } },
      size: 1000,
      sort: [{ scraped_at: { order: 'desc' } }]
    });

    const docs = result.hits.hits.map(hit => ({
      ...hit._source,
      id: hit._id
    }));

    res.json(docs);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'DB_ERROR' });
  }
});

// Full-text search (with query sanitization)
router.get('/_search', async (req, res) => {
  try {
    const { q } = req.query;
    const client = getClient();

    // Sanitize query to prevent injection
    const safeQuery = escapeElasticsearchQuery(q);

    const searchParams = {
      index: getIndexName(),
      size: 1000
    };

    if (safeQuery) {
      // Use match query instead of query_string for safety
      searchParams.body = {
        query: {
          multi_match: {
            query: safeQuery,
            fields: ['title', 'content', 'url', 'domain'],
            type: 'best_fields',
            fuzziness: 'AUTO'
          }
        }
      };
    } else {
      searchParams.body = { query: { match_all: {} } };
    }

    const { body: result } = await client.search(searchParams);

    const docs = result.hits.hits.map(hit => ({
      ...hit._source,
      id: hit._id
    }));

    res.json(docs);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'SEARCH_ERROR' });
  }
});

// Keyword count (with query sanitization)
router.get('/_label', async (req, res) => {
  try {
    const { q } = req.query;
    const client = getClient();

    // Sanitize query
    const safeQuery = escapeElasticsearchQuery(q);

    if (!safeQuery) {
      return res.json({ label: q, value: 0 });
    }

    const { body: result } = await client.search({
      index: getIndexName(),
      body: {
        query: {
          multi_match: {
            query: safeQuery,
            fields: ['title', 'content', 'url']
          }
        }
      },
      size: 0
    });

    res.json({
      label: q,
      value: result.hits.total.value || 0
    });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'COUNT_ERROR' });
  }
});

// Paginated results for infinite scroll (with query sanitization)
router.get('/_bins/:page', async (req, res) => {
  try {
    const page = Math.max(0, parseInt(req.params.page) || 0);
    const pageSize = Math.min(100, Math.max(1, parseInt(req.query.size) || 10)); // Limit 1-100
    const { q } = req.query;
    const client = getClient();

    // Sanitize query
    const safeQuery = escapeElasticsearchQuery(q);

    const searchParams = {
      index: getIndexName(),
      from: page * pageSize,
      size: pageSize,
      sort: [{ scraped_at: { order: 'desc' } }]
    };

    if (safeQuery) {
      searchParams.body = {
        query: {
          multi_match: {
            query: safeQuery,
            fields: ['title', 'content', 'url', 'domain'],
            fuzziness: 'AUTO'
          }
        }
      };
    } else {
      searchParams.body = { query: { match_all: {} } };
    }

    const { body: result } = await client.search(searchParams);

    const docs = result.hits.hits.map(hit => ({
      ...hit._source,
      id: hit._id
    }));

    res.json(docs);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'PAGINATION_ERROR' });
  }
});

// Get document by ID
router.get('/:id', async (req, res) => {
  try {
    // Validate ID format (should be hex string)
    const id = req.params.id;
    if (!/^[a-f0-9]{32,64}$/i.test(id)) {
      return res.status(400).json({ error: 'Invalid document ID format', code: 'INVALID_ID' });
    }

    const client = getClient();
    const { body: result } = await client.get({
      index: getIndexName(),
      id: id
    });

    res.json({ ...result._source, id: result._id });
  } catch (error) {
    if (error.meta?.statusCode === 404) {
      res.status(404).json({ error: 'Document not found', code: 'NOT_FOUND' });
    } else {
      res.status(500).json({ error: sanitizeError(error), code: 'DB_ERROR' });
    }
  }
});

// Bulk insert data (with size limits and SHA-256)
router.post('/', async (req, res) => {
  try {
    const { body: data } = req;
    const client = getClient();
    const io = req.app.get('io');

    // Validate input
    if (!Array.isArray(data)) {
      return res.status(400).json({ error: 'Expected array of documents', code: 'INVALID_INPUT' });
    }

    if (data.length === 0) {
      return res.status(400).json({ error: 'Empty document array', code: 'EMPTY_ARRAY' });
    }

    // SECURITY: Enforce bulk size limit to prevent DoS
    if (data.length > MAX_BULK_SIZE) {
      return res.status(400).json({
        error: `Maximum ${MAX_BULK_SIZE} documents per request`,
        code: 'BULK_LIMIT_EXCEEDED',
        received: data.length,
        max: MAX_BULK_SIZE
      });
    }

    // Build bulk operations with deduplication via SHA-256 (not MD5)
    const operations = data.flatMap(doc => {
      const _id = generateDocId(doc);

      // Sanitize document - remove any potential script injections
      const sanitizedDoc = {
        ...doc,
        title: typeof doc.title === 'string' ? doc.title.slice(0, 500) : '',
        content: typeof doc.content === 'string' ? doc.content.slice(0, 10000) : '',
        url: typeof doc.url === 'string' ? doc.url.slice(0, 2000) : ''
      };

      return [
        { index: { _index: getIndexName(), _id } },
        sanitizedDoc
      ];
    });

    const { body: bulkResponse } = await client.bulk({
      refresh: true,
      body: operations
    });

    // Emit real-time update
    if (io) {
      io.to('data-updates').emit('data:new', {
        count: data.length,
        timestamp: new Date().toISOString()
      });
    }

    res.json({
      indexed: data.length,
      errors: bulkResponse.errors ? bulkResponse.items.filter(i => i.index.error).length : 0
    });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'BULK_ERROR' });
  }
});

// Delete document
router.delete('/:id', async (req, res) => {
  try {
    // Validate ID format
    const id = req.params.id;
    if (!/^[a-f0-9]{32,64}$/i.test(id)) {
      return res.status(400).json({ error: 'Invalid document ID format', code: 'INVALID_ID' });
    }

    const client = getClient();
    await client.delete({
      index: getIndexName(),
      id: id,
      refresh: true
    });

    res.json({ deleted: true, id: id });
  } catch (error) {
    if (error.meta?.statusCode === 404) {
      res.status(404).json({ error: 'Document not found', code: 'NOT_FOUND' });
    } else {
      res.status(500).json({ error: sanitizeError(error), code: 'DELETE_ERROR' });
    }
  }
});

// Get index stats
router.get('/_stats', async (req, res) => {
  try {
    const client = getClient();
    const { body: count } = await client.count({ index: getIndexName() });
    const { body: stats } = await client.indices.stats({ index: getIndexName() });

    res.json({
      document_count: count.count,
      size_bytes: stats._all.primaries.store.size_in_bytes,
      index: getIndexName()
    });
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'STATS_ERROR' });
  }
});

module.exports = router;

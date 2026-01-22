/**
 * Analytics routes - Sentiment analysis and visualizations
 * Based on zilbers/dark-web-scraper patterns
 *
 * Security fixes applied:
 * - Query sanitization for keyword searches
 * - Sanitized error responses
 */

const { Router } = require('express');
const Sentiment = require('sentiment');
const { getClient, getIndexName } = require('../db/elasticsearch');

const router = Router();

// Sanitize error for client response
function sanitizeError(error) {
  const isProduction = process.env.NODE_ENV === 'production';
  return isProduction ? 'Analytics operation failed' : error.message;
}

// Escape Elasticsearch special characters
function escapeQuery(query) {
  if (!query || typeof query !== 'string') return '';
  return query.slice(0, 100).replace(/[+\-=&|!(){}[\]^"~*?:\\/><]/g, '\\$&');
}

// Dark web focused keywords with weights
const DARK_WEB_KEYWORDS = {
  'DDOS': -3,
  'exploits': -4,
  'attack': -3,
  'money': -2,
  'bitcoin': -2,
  'passwords': -5,
  'information': -2,
  'explosives': -5,
  'weapons': -5,
  'hacked': -4,
  'password': -5,
  'ransomware': -4,
  'stolen': -5,
  'username': -5,
  'account': -3,
  'leaked': -5,
  'fullz': -3,
  'dump data': -3,
  'credit cards': -5,
  'malware': -4,
  'trojan': -4,
  'botnet': -4,
  'phishing': -4,
  'credentials': -5,
  'breach': -5,
  'zero-day': -5,
  'vulnerability': -3
};

// Convert to sentiment extras format
const sentimentExtras = Object.entries(DARK_WEB_KEYWORDS).map(([word, score]) => ({
  [word]: score
}));

const sentiment = new Sentiment();

// Analyze sentiment for documents
router.post('/_sentiment', async (req, res) => {
  try {
    const documents = req.body;

    if (!Array.isArray(documents)) {
      return res.status(400).json({ error: 'Expected array of documents' });
    }

    const results = documents.map(doc => {
      let totalScore = 0;
      let totalComparative = 0;
      const words = [];

      // Analyze each text field
      for (const [key, value] of Object.entries(doc)) {
        if (typeof value === 'string' && value.trim()) {
          const analysis = sentiment.analyze(value, { extras: sentimentExtras });

          if (Number.isFinite(analysis.score)) {
            totalScore += analysis.score;
            totalComparative += analysis.comparative;
          }

          if (analysis.words && analysis.words.length > 0) {
            words.push(...analysis.words);
          }
        }
      }

      return {
        score: totalScore,
        comparative: totalComparative,
        words: [...new Set(words)]
      };
    });

    res.json(results);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'SENTIMENT_ERROR' });
  }
});

// Get keyword frequency for pie chart (with query sanitization)
router.get('/_keywords', async (req, res) => {
  try {
    const rawKeywords = req.query.words
      ? req.query.words.split(',').slice(0, 20) // Limit to 20 keywords
      : ['bitcoin', 'weapons', 'stolen', 'credit', 'passwords'];

    const client = getClient();
    const results = [];

    for (const keyword of rawKeywords) {
      // Sanitize keyword to prevent query injection
      const safeKeyword = escapeQuery(keyword.trim());
      if (!safeKeyword) continue;

      const { body: result } = await client.count({
        index: getIndexName(),
        body: {
          query: {
            multi_match: {
              query: safeKeyword,
              fields: ['title', 'content']
            }
          }
        }
      });

      results.push({
        label: keyword.trim(),
        value: result.count
      });
    }

    res.json(results);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'KEYWORD_ERROR' });
  }
});

// Get domain distribution
router.get('/_domains', async (req, res) => {
  try {
    const client = getClient();
    const { body: result } = await client.search({
      index: getIndexName(),
      body: {
        size: 0,
        aggs: {
          domains: {
            terms: {
              field: 'domain',
              size: 50
            }
          }
        }
      }
    });

    const domains = result.aggregations.domains.buckets.map(b => ({
      domain: b.key,
      count: b.doc_count
    }));

    res.json(domains);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'ANALYTICS_ERROR' });
  }
});

// Get onion vs clearnet ratio
router.get('/_onion-ratio', async (req, res) => {
  try {
    const client = getClient();
    const { body: result } = await client.search({
      index: getIndexName(),
      body: {
        size: 0,
        aggs: {
          onion_ratio: {
            terms: {
              field: 'is_onion'
            }
          }
        }
      }
    });

    const ratio = { onion: 0, clearnet: 0 };
    for (const bucket of result.aggregations.onion_ratio.buckets) {
      if (bucket.key_as_string === 'true' || bucket.key === true) {
        ratio.onion = bucket.doc_count;
      } else {
        ratio.clearnet = bucket.doc_count;
      }
    }

    res.json(ratio);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'ANALYTICS_ERROR' });
  }
});

// Get time series data for line charts
router.get('/_timeline', async (req, res) => {
  try {
    const { interval = 'day', days = 30 } = req.query;
    const client = getClient();

    const { body: result } = await client.search({
      index: getIndexName(),
      body: {
        size: 0,
        query: {
          range: {
            scraped_at: {
              gte: `now-${days}d/d`,
              lte: 'now/d'
            }
          }
        },
        aggs: {
          timeline: {
            date_histogram: {
              field: 'scraped_at',
              calendar_interval: interval
            },
            aggs: {
              avg_sentiment: {
                avg: { field: 'sentiment_score' }
              }
            }
          }
        }
      }
    });

    const timeline = result.aggregations.timeline.buckets.map(b => ({
      date: b.key_as_string,
      count: b.doc_count,
      avg_sentiment: b.avg_sentiment.value || 0
    }));

    res.json(timeline);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'ANALYTICS_ERROR' });
  }
});

// Get threat level distribution
router.get('/_threats', async (req, res) => {
  try {
    const client = getClient();
    const { body: result } = await client.search({
      index: getIndexName(),
      body: {
        size: 0,
        aggs: {
          threat_levels: {
            range: {
              field: 'sentiment_score',
              ranges: [
                { key: 'critical', to: -50 },
                { key: 'high', from: -50, to: -25 },
                { key: 'medium', from: -25, to: -10 },
                { key: 'low', from: -10, to: 0 },
                { key: 'neutral', from: 0 }
              ]
            }
          }
        }
      }
    });

    const threats = result.aggregations.threat_levels.buckets.map(b => ({
      level: b.key,
      count: b.doc_count
    }));

    res.json(threats);
  } catch (error) {
    res.status(500).json({ error: sanitizeError(error), code: 'ANALYTICS_ERROR' });
  }
});

module.exports = router;

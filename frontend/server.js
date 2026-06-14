import compression from 'compression';
import express from 'express';
import { createServer } from 'http';

const app = express();

// Enable gzip/brotli compression for all responses
app.use(compression({
    level: 6, // Balanced compression level
    threshold: 1024, // Only compress responses > 1KB
    filter: (req, res) => {
        if (req.headers['x-no-compression']) {
            return false;
        }
        return compression.filter(req, res);
    }
}));

// Security headers
app.use((req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('X-XSS-Protection', '1; mode=block');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    next();
});

// Cache control for static assets
app.use('/assets', express.static('build/assets', {
    maxAge: '1y',
    immutable: true,
    setHeaders: (res, path) => {
        if (path.endsWith('.html')) {
            res.setHeader('Cache-Control', 'no-cache');
        }
    }
}));

// Serve index.html with no-cache
app.use(express.static('build', {
    maxAge: 0,
    setHeaders: (res, path) => {
        if (path.endsWith('.html')) {
            res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        }
    }
}));

// SPA fallback
app.get('*', (req, res) => {
    res.sendFile('index.html', { root: 'build' });
});

const PORT = process.env.PORT || 3000;
const server = createServer(app);

server.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`📦 Serving optimized build with compression enabled`);
});

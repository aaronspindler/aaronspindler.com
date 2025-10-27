#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const brotli = require('brotli');

// JavaScript files to compress
const jsFiles = [
    'static/js/base-optimized.min.js',
    'static/js/knowledge_graph.min.js',
    'static/js/search-autocomplete.min.js'
];

// Compression function
function compressFile(filePath) {
    const fullPath = path.join(__dirname, '..', filePath);

    // Check if file exists
    if (!fs.existsSync(fullPath)) {
        console.warn(`Warning: ${filePath} not found, skipping...`);
        return;
    }

    const content = fs.readFileSync(fullPath);
    const fileName = path.basename(fullPath);
    const dirName = path.dirname(fullPath);

    // Gzip compression
    const gzipped = zlib.gzipSync(content, { level: 9 });
    const gzipPath = path.join(dirName, `${fileName}.gz`);
    fs.writeFileSync(gzipPath, gzipped);

    // Brotli compression
    const brotliCompressed = Buffer.from(brotli.compress(content, {
        mode: 1, // text mode
        quality: 11, // max quality
        lgwin: 22
    }));
    const brotliPath = path.join(dirName, `${fileName}.br`);
    fs.writeFileSync(brotliPath, brotliCompressed);

    // Report sizes
    const originalSize = content.length;
    const gzipSize = gzipped.length;
    const brotliSize = brotliCompressed.length;

    console.log(`✓ ${fileName}:`);
    console.log(`  Original: ${(originalSize / 1024).toFixed(2)} KB`);
    console.log(`  Gzip: ${(gzipSize / 1024).toFixed(2)} KB (${((1 - gzipSize/originalSize) * 100).toFixed(1)}% reduction)`);
    console.log(`  Brotli: ${(brotliSize / 1024).toFixed(2)} KB (${((1 - brotliSize/originalSize) * 100).toFixed(1)}% reduction)`);
}

// Process all JS files
console.log('Compressing JavaScript files...\n');
jsFiles.forEach(compressFile);
console.log('\n✅ JavaScript compression complete!');

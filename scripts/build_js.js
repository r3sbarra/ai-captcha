#!/usr/bin/env node
// Build step: obfuscate scripts/src/challenge.js -> static/js/challenge.js
// Run: node scripts/build_js.js
const fs = require('fs');
const path = require('path');
const JavaScriptObfuscator = require('javascript-obfuscator');

const root = path.resolve(__dirname, '..');
const src = path.join(root, 'scripts', 'src', 'challenge.js');
const out = path.join(root, 'ai_captcha', 'static', 'js', 'challenge.js');

const code = fs.readFileSync(src, 'utf8');

const result = JavaScriptObfuscator.obfuscate(code, {
    compact: true,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.75,
    deadCodeInjection: true,
    deadCodeInjectionThreshold: 0.3,
    identifierNamesGenerator: 'hexadecimal',
    numbersToExpressions: true,
    renameGlobals: true,          // rename internal fns; window.AICAPTCHA_BASE (property) stays intact
    selfDefending: true,
    simplify: true,
    splitStrings: true,
    splitStringsChunkLength: 8,
    stringArray: true,
    stringArrayEncoding: ['base64'],
    stringArrayThreshold: 0.8,
    transformObjectKeys: true,
    unicodeEscapeSequence: false,
});

fs.writeFileSync(out, result.getObfuscatedCode());
console.log(`Obfuscated ${src} -> ${out} (${result.getObfuscatedCode().length} bytes)`);

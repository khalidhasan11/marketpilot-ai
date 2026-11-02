'use strict';
/* Unit tests for the 1-Second Live Mode bar aggregation core
 * (frontend/live1s.js). Run: node tests/live1s.test.js
 * Feeds synthetic trades and asserts forming-bar OHLCV + bucket rollover. */
const assert = require('assert');
const { tfSecondsFor, bucketStartMs, createBar, applyTrade } = require('../frontend/live1s.js');

let passed = 0;
function ok(name, fn) { fn(); passed++; console.log('ok -', name); }

const T0 = 1700000100000; // fixed epoch ms, inside a 5s bucket boundary check

ok('tfSecondsFor maps all timeframes', () => {
  assert.strictEqual(tfSecondsFor('1s'), 1);
  assert.strictEqual(tfSecondsFor('5s'), 5);
  assert.strictEqual(tfSecondsFor('15s'), 15);
  assert.strictEqual(tfSecondsFor('30s'), 30);
  assert.strictEqual(tfSecondsFor('1m'), 60);
  assert.strictEqual(tfSecondsFor('5m'), 300);
  assert.strictEqual(tfSecondsFor('1w'), 604800);
  assert.strictEqual(tfSecondsFor('bogus'), 300); // safe default
});

ok('bucketStartMs aligns to UTC bucket boundaries', () => {
  assert.strictEqual(bucketStartMs(T0, 5), Math.floor(T0 / 5000) * 5000);
  assert.strictEqual(bucketStartMs(T0, 1), T0 - (T0 % 1000));
  assert.strictEqual(bucketStartMs(0, 300), 0);
});

ok('first trade creates the forming bar (open=high=low=close)', () => {
  const r = applyTrade(null, 100, 2, T0, 5);
  assert.strictEqual(r.rolled, false);
  assert.strictEqual(r.closedBar, null);
  assert.deepStrictEqual(
    { o: r.bar.open, h: r.bar.high, l: r.bar.low, c: r.bar.close, v: r.bar.volume },
    { o: 100, h: 100, l: 100, c: 100, v: 2 });
  assert.strictEqual(r.bar.time, bucketStartMs(T0, 5) / 1000);
});

ok('trades inside the bucket expand high/low, move close, accumulate volume', () => {
  let bar = createBar(bucketStartMs(T0, 5), 100, 1);
  let r = applyTrade(bar, 105, 3, T0 + 1000, 5); bar = r.bar;
  assert.strictEqual(bar.high, 105); assert.strictEqual(bar.close, 105);
  r = applyTrade(bar, 97, 2, T0 + 2000, 5); bar = r.bar;
  assert.strictEqual(bar.low, 97); assert.strictEqual(bar.close, 97);
  assert.strictEqual(bar.open, 100);            // open never moves inside a bar
  assert.strictEqual(bar.volume, 1 + 3 + 2);    // real quantities summed
  assert.strictEqual(r.rolled, false);
});

ok('trade in the next bucket rolls over: old bar closed, new bar opens at trade price', () => {
  const tf = 5;
  let bar = createBar(bucketStartMs(T0, tf), 100, 1);
  bar = applyTrade(bar, 110, 1, T0 + 1000, tf).bar;
  const nextBucket = bucketStartMs(T0, tf) + tf * 1000;
  const r = applyTrade(bar, 90, 4, nextBucket + 500, tf);
  assert.strictEqual(r.rolled, true);
  assert.strictEqual(r.closedBar.close, 110);          // previous bar preserved as closed
  assert.strictEqual(r.bar.time, nextBucket / 1000);   // new bar at the trade's bucket
  assert.deepStrictEqual(
    { o: r.bar.open, h: r.bar.high, l: r.bar.low, c: r.bar.close, v: r.bar.volume },
    { o: 90, h: 90, l: 90, c: 90, v: 4 });
});

ok('a trade several buckets later starts at its own bucket (gap left as a gap)', () => {
  const tf = 5;
  const bar = createBar(bucketStartMs(T0, tf), 100, 1);
  const later = bucketStartMs(T0, tf) + 3 * tf * 1000 + 100;
  const r = applyTrade(bar, 50, 1, later, tf);
  assert.strictEqual(r.rolled, true);
  assert.strictEqual(r.bar.time, bucketStartMs(later, tf) / 1000);
});

ok('late/out-of-order trade from an older bucket is ignored', () => {
  const tf = 5;
  let bar = createBar(bucketStartMs(T0, tf) + tf * 1000, 100, 1);
  const r = applyTrade(bar, 999, 5, T0 + 100, tf); // belongs to previous bucket
  assert.strictEqual(r.rolled, false);
  assert.strictEqual(r.bar.close, 100);
  assert.strictEqual(r.bar.volume, 1);
});

ok('1s timeframe: every second is its own bucket', () => {
  let bar = createBar(bucketStartMs(T0, 1), 10, 1);
  const r = applyTrade(bar, 11, 1, T0 + 1000, 1);
  assert.strictEqual(r.rolled, true);
  assert.strictEqual(r.bar.time - bar.time, 1);
});

console.log(`\n${passed} tests passed`);

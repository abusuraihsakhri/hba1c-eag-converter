const test = require('node:test');
const assert = require('node:assert/strict');
const { convert } = require('../web/converter.js');

test('standard ADAG reference points', () => {
  assert.deepEqual(convert(7, 'hba1c_percent'), {
    hba1c_percent: 7, eag_mgdl: 154.2, eag_mmol: 8.6, ifcc_mmol_mol: 53.0
  });
  assert.equal(convert(10, 'hba1c_percent').eag_mgdl, 240.3);
});
test('bidirectional inputs', () => {
  assert.equal(convert(154.2, 'eag_mgdl').hba1c_percent, 7);
  assert.equal(convert(53, 'ifcc_mmol').hba1c_percent, 7);
  assert.equal(convert(8.6, 'eag_mmol').hba1c_percent, 7.03);
});
test('invalid input handling', () => {
  for (const bad of [NaN, Infinity, -Infinity, null, '7']) {
    assert.throws(() => convert(bad, 'hba1c_percent'), RangeError);
  }
  assert.throws(() => convert(0, 'hba1c_percent'), RangeError);
  assert.throws(() => convert(30, 'hba1c_percent'), RangeError);
  assert.throws(() => convert(7, '__proto__'), RangeError);
});
test('boundaries are inclusive', () => {
  assert.equal(convert(2, 'hba1c_percent').hba1c_percent, 2);
  assert.equal(convert(25, 'hba1c_percent').hba1c_percent, 25);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
import { readFileSync } from 'node:fs';
const source = readFileSync(new URL('../src/app/shared/time.ts', import.meta.url), 'utf8');
const compiled = ts.transpile(source, { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 });
const { timeLabel } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));
test('long recordings keep hours and minute boundaries', () => { assert.equal(timeLabel(7200.5), '02:00:00'); assert.equal(timeLabel(59.99), '00:00:59'); assert.equal(timeLabel(60), '00:01:00'); });
test('invalid player times are safe', () => { assert.equal(timeLabel(NaN), '00:00:00'); assert.equal(timeLabel(-1), '00:00:00'); });

import test from 'node:test';
import assert from 'node:assert/strict';
import {entryMode} from './entryMode.js';
test('first visitor starts with sign-up; explicit member links open login',()=>{
 assert.equal(entryMode(''),'signup');
 assert.equal(entryMode('?entry=signup'),'signup');
 assert.equal(entryMode('?entry=login'),'login');
 assert.equal(entryMode('?entry=admin'),'signup');
});

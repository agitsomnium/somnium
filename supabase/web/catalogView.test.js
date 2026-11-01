import test from "node:test";
import assert from "node:assert/strict";
import { catalogPlan, catalogSignature } from "./catalogView.js";

const rows = () => [{ id: "a", title: "A" }, { id: "b", title: "B" }];
const first = catalogPlan({ prev: "", userId: "u1", rows: rows(), canLearn: true, rendered: false });

test("first load renders", () => assert.equal(first.action, "render"));

test("normal background refresh with equal rows in new objects keeps the view", () => {
  const plan = catalogPlan({ prev: first.signature, userId: "u1", rows: rows(), canLearn: true, rendered: true });
  assert.equal(plan.action, "keep");
});

test("same signature but nothing rendered yet still renders", () => {
  assert.equal(catalogPlan({ prev: first.signature, userId: "u1", rows: rows(), canLearn: true, rendered: false }).action, "render");
});

test("changed rows rebuild", () => {
  const next = rows(); next[1].title = "B2";
  assert.equal(catalogPlan({ prev: first.signature, userId: "u1", rows: next, canLearn: true, rendered: true }).action, "render");
  assert.equal(catalogPlan({ prev: first.signature, userId: "u1", rows: rows().slice(0, 1), canLearn: true, rendered: true }).action, "render");
});

test("a different user never reuses the previous view", () => {
  assert.equal(catalogPlan({ prev: first.signature, userId: "u2", rows: rows(), canLearn: true, rendered: true }).action, "render");
});

test("revoked permission or sign-out clears immediately, even if rows are unchanged", () => {
  assert.equal(catalogPlan({ prev: first.signature, userId: "u1", rows: rows(), canLearn: false, rendered: true }).action, "clear");
  assert.equal(catalogPlan({ prev: first.signature, userId: "", rows: rows(), canLearn: true, rendered: true }).action, "clear");
  assert.equal(catalogPlan({ prev: first.signature, userId: null, rows: [], canLearn: false, rendered: true }).signature, "");
});

test("signature depends on user and rows", () => {
  assert.notEqual(catalogSignature("u1", rows()), catalogSignature("u2", rows()));
  assert.equal(catalogSignature("u1", rows()), catalogSignature("u1", rows()));
});

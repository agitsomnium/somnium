import test from "node:test";
import assert from "node:assert/strict";
import { profileCall } from "./profile.js";

const form = (values) => (key) => values[key];

test("minimal: name only sends null phone/supporter and no birth key", () => {
  const call = profileCall("minimal", form({ name: " 김솜 ", consent: "on", birth: "2000-01-01" }));
  assert.equal(call.rpc, "complete_profile_minimal");
  assert.deepEqual(call.args, { p_name: "김솜", p_phone: null, p_supporter_name: null, p_consent: true });
  assert.ok(!("p_birth" in call.args));
});

test("minimal: optional phone is normalised and supporter name kept", () => {
  const call = profileCall("minimal", form({ name: "김솜", phone: "010-1234 5678", supporter: " 한빛 후원자 ", consent: "on" }));
  assert.equal(call.args.p_phone, "01012345678");
  assert.equal(call.args.p_supporter_name, "한빛 후원자");
});

test("minimal: unchecked consent is sent as false", () => {
  assert.equal(profileCall("minimal", form({ name: "김솜" })).args.p_consent, false);
});

test("current form keeps the deployed contract", () => {
  const call = profileCall("current", form({ name: "김솜", birth: "2000-01-01", phone: "01012345678", consent: "on" }));
  assert.equal(call.rpc, "complete_profile");
  assert.deepEqual(call.args, { p_name: "김솜", p_birth: "2000-01-01", p_phone: "01012345678", p_consent: true });
});

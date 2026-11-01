// Arguments for the sign-up RPC. 'current' = deployed form (name, birth, phone). 'minimal' = unapplied draft:
// name required, phone optional, supporter name optional, birth date never collected.
export function profileCall(mode, read) {
  const name = String(read("name") ?? "").trim();
  const consent = read("consent") === "on";
  const phone = String(read("phone") ?? "").replace(/[-\s]/g, "");
  if (mode === "minimal") {
    return { rpc: "complete_profile_minimal", args: { p_name: name, p_phone: phone || null, p_supporter_name: String(read("supporter") ?? "").trim() || null, p_consent: consent } };
  }
  return { rpc: "complete_profile", args: { p_name: name, p_birth: read("birth"), p_phone: phone, p_consent: consent } };
}

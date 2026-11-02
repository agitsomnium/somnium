export function entryMode(search) {
  return new URLSearchParams(search).get("entry") === "login" ? "login" : "signup";
}

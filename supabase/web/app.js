import { accounting } from "./accounting.js";
import { mergeCatalog, localCover } from "./publicCatalog.js";
import { passwordAuth, authMessage } from "./passwordAuth.js";
import { entryMode } from "./entryMode.js";
import { createClient } from "@supabase/supabase-js";
import { newestFirst } from "./order.js";
import { seriesGroups } from "./series.js";
import { profileCall, supporterNameLine } from "./profile.js";
import { downloadMaterial } from "./materialDownload.js";
import { catalogPlan } from "./catalogView.js";
const openSeries = new Set();
const openMaterials = new Set();
let catalogSig = "";
let requestedLessonShown = false;
const $ = (id) => document.getElementById(id);
const config = await fetch("/runtime-config.json", { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new Error("설정을 읽지 못했습니다.");
  return r.json();
});
const db = createClient(config.url, config.publishableKey, { auth: { storage: sessionStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
const credentials = passwordAuth(db.auth);
let settingPassword = sessionStorage.getItem("somnium-password-pending") === "yes";
let me = null, user = null, lessons = [], signup = false, targetEmail = "", lastSend = 0, activeLesson = "", refreshGeneration = 0, privateEpoch = 0, managedLessons = [];
const reportUI = accounting(db, {access:()=>({userId:user?.id,epoch:privateEpoch,member:!!me && !me.suspended,admin:!!me?.admin}),rpc,notice});
const stateNames = { not_requested: "일반회원 · 후원 확인 전", pending: "후원 확인 대기", qualified: "후원회원 · 강의 이용 가능", held: "후원 확인 보류", withdrawn: "후원 자격 종료" };
function notice(t) {
  $("notice").textContent = t;
}
function show(id, on) {
  $(id).hidden = !on;
  if (id === "entry") $("paths").hidden = !on;
}
function text(tag, t, parent) {
  const e = document.createElement(tag);
  e.textContent = t;
  parent?.append(e);
  return e;
}
function action(label, parent, fn) {
  const b = text("button", label, parent);
  b.type = "button";
  b.onclick = () => run(b, fn);
  return b;
}
async function run(button, fn) {
  button.disabled = true;
  try {
    await fn();
  } catch (e) {
    notice(e.message);
  } finally {
    button.disabled = false;
  }
}
function safeError(error) {
  if (authMessage(error)) return authMessage(error);
  if (error.code === "otp_expired") return "인증번호가 올바르지 않거나 만료됐습니다.";
  if (error.status === 429) return "잠시 기다린 뒤 다시 시도해 주세요.";
  if (error.code === "user_not_found" || error.code === "signup_disabled") return "가입 정보가 없거나 로그인이 제한되었습니다. 회원가입을 확인해 주세요.";
  if (error.code === "42501") return "현재 이용 권한이 없습니다. 상태를 새로고침해 주세요.";
  return "처리하지 못했습니다. 입력과 연결 상태를 확인한 뒤 다시 시도해 주세요.";
}
async function rpc(name, args = {}) {
  const { data, error } = await db.rpc("somnium_" + name, args);
  if (error) throw new Error(safeError(error));
  return data;
}
function clearPrivate() {
  reportUI.clear();
  privateEpoch++;
  openMaterials.clear();
  catalogSig = "";
  lessons = [];
  managedLessons = [];
  activeLesson = "";
  $("issued-code-value").value = "";
  show("issued-code", false);
  for (const id of ["catalog", "player-region", "members", "admin-lessons", "directors", "audit", "series-codes", "series-entitlements", "admin-materials"]) $(id).replaceChildren();
}
function mode(value) {
  signup = value;
  $("login-tab").setAttribute("aria-pressed", String(!value));
  $("signup-tab").setAttribute("aria-pressed", String(value));
  $("login-form").querySelector("button").textContent = value ? "가입 인증번호 받기" : "로그인";
  $("entry-heading").textContent = value ? "이메일로 회원가입" : "이메일·비밀번호로 로그인";
  $("entry-help").textContent = value ? "처음 한 번 이메일 인증 → 비밀번호 설정 → 이름 입력 순서입니다. 가입만으로 후원금이 결제되지는 않습니다." : "가입한 이메일과 비밀번호로 로그인하세요. 기존 회원의 비밀번호 설정과 비밀번호 찾기는 아래 버튼을 이용해 주세요.";
  show("login-password-field", !value);
  $("login-password").disabled = value;
  $("login-password").required = !value;
  $("login-password").value = "";
  show("password-help", !value);
  $("otp-form").querySelector("button").textContent = "인증하고 비밀번호 설정";
  notice(value ? "처음 한 번 이메일 인증 후 비밀번호와 이름을 입력하면 가입할 수 있습니다." : "가입한 이메일로 로그인합니다.");
}
{
  const minimal = config.profileMode === "minimal";
  for (const e of document.querySelectorAll("[data-profile]")) {
    const on = e.dataset.profile === (minimal ? "minimal" : "current");
    e.hidden = !on;
    for (const input of e.querySelectorAll("input")) input.disabled = !on;
  }
}
$("login-tab").onclick = () => mode(false);
$("path-new").onclick = () => {
  mode(true);
  $("entry").scrollIntoView({ behavior: "auto", block: "start" });
  $("login-form").elements.email.focus();
};
$("path-member").onclick = () => {
  mode(false);
  $("login-form").elements.email.focus();
};
$("path-code").onclick = () => {
  mode(false);
  notice("수강 코드는 로그인한 뒤 등록합니다. 처음이면 ‘처음 회원가입’으로 가입해 주세요.");
  $("login-form").elements.email.focus();
};
$("signup-tab").onclick = () => mode(true);
function form(id, fn) {
  $(id).onsubmit = (e) => {
    e.preventDefault();
    run(e.submitter, () => fn(new FormData(e.target)));
  };
}
// Review hosts restrict the UI to listed e-mails; the public build sets openSignup and lets any e-mail sign up (Auth/RLS still decide access).
const emailAllowed = (email) => config.openSignup === true || config.testEmails.includes(email);
async function send() {
  const email = targetEmail;
  if (!emailAllowed(email)) throw new Error("현재는 지정된 검토 이메일만 이용할 수 있습니다.");
  if (Date.now() - lastSend < 6e4) throw new Error("인증번호 요청 후 1분을 기다려 주세요.");
  const { error } = await credentials.requestCode(email, signup);
  if (error) {
    if (!signup && error.code === "otp_disabled") throw new Error("처음 이용하시는 경우 ‘처음 회원가입’을 선택해 주세요. 가입한 이메일도 확인해 주세요.");
    throw new Error(safeError(error));
  }
  lastSend = Date.now();
  show("entry", false);
  show("otp-panel", true);
  $("otp-to").textContent = email + "로 인증번호를 보냈습니다. 받은편지함과 스팸함을 확인해 주세요.";
  notice("인증번호는 이 화면에 직접 입력해 주세요.");
  $("otp-form").reset();
  $("otp-form").elements.token.focus();
}
form("login-form", async (f) => {
  targetEmail = String(f.get("email")).trim().toLowerCase();
  if (signup) { await send(); return; }
  const password = String(f.get("password") || "");
  $("login-password").value = "";
  if (!emailAllowed(targetEmail)) throw new Error("현재는 지정된 검토 이메일만 이용할 수 있습니다.");
  const { error } = await credentials.login(targetEmail, password);
  if (error) throw new Error(safeError(error));
  show("otp-panel", false);
  await refresh();
  notice("로그인했습니다.");
});
$("password-help").onclick = () => run($("password-help"), async () => {
  const emailField = $("login-form").elements.email;
  if (!emailField.reportValidity()) return;
  signup = false;
  targetEmail = emailField.value.trim().toLowerCase();
  $("login-password").value = "";
  await send();
});
$("existing-otp").onclick = () => {
  targetEmail = String($("login-form").elements.email.value).trim().toLowerCase();
  if (!emailAllowed(targetEmail)) {
    notice("검토 이메일을 입력해 주세요.");
    return;
  }
  show("entry", false);
  show("otp-panel", true);
  $("otp-to").textContent = targetEmail + "로 이미 받은 인증번호를 입력해 주세요.";
  notice("새 메일을 발송하지 않았습니다.");
  $("otp-form").elements.token.focus();
};
form("otp-form", async (f) => {
  const { error } = await credentials.verifyCode(targetEmail, String(f.get("token")).trim());
  $("otp-form").reset();
  if (error) throw new Error(safeError(error));
  show("otp-panel", false);
  settingPassword = true;
  sessionStorage.setItem("somnium-password-pending", "yes");
  await refresh();
  notice("이메일이 확인됐습니다. 다음부터 사용할 비밀번호를 정해 주세요.");
});
form("password-form", async (f) => {
  const password = String(f.get("password") || ""), confirmation = String(f.get("confirmation") || "");
  $("password-form").reset();
  const { error } = await credentials.setPassword(user?.email || targetEmail, password, confirmation);
  if (error) throw new Error(safeError(error));
  settingPassword = false;
  sessionStorage.removeItem("somnium-password-pending");
  show("password-panel", false);
  await refresh();
  notice(me ? "비밀번호를 저장했습니다. 다음부터 이메일과 비밀번호로 로그인하세요." : "비밀번호를 저장했습니다. 이름을 입력하면 가입이 끝납니다.");
});
$("password-cancel").onclick = () => run($("password-cancel"), async () => {
  const { error } = await db.auth.signOut({ scope: "local" });
  if (error) throw new Error(safeError(error));
  await refresh();
});
$("resend").onclick = () => run($("resend"), send);
setInterval(() => {
  $("resend").disabled = Date.now() - lastSend < 6e4;
}, 1e3);
$("cancel").onclick = () => {
  show("otp-panel", false);
  show("entry", !user);
  $("otp-form").reset();
};
form("profile-form", async (f) => {
  const call = profileCall(config.profileMode === "minimal" ? "minimal" : "current", (key) => f.get(key));
  await rpc(call.rpc, call.args);
  $("profile-form").reset();
  await refresh();
  notice("일반회원 가입을 마쳤습니다. 후원을 신청하셨다면 아래에서 후원 신청 완료를 알려 주세요.");
});
$("supporter-request").onclick = () => run($("supporter-request"), async () => {
  await rpc("request_supporter");
  await refresh();
  notice("강의 이용을 승인했습니다. 후원 내역은 월별 회계 정리 때 확인합니다.");
  db.functions.invoke("supporter-notice").catch(() => {});
});
$("refresh").onclick = () => run($("refresh"), refresh);
$("logout").onclick = () => run($("logout"), async () => {
  refreshGeneration++;
  clearPrivate();
  show("admin-panel", false);
  show("catalog-panel", false);
  const { error } = await db.auth.signOut({ scope: "local" });
  if (error) throw new Error(safeError(error));
  await refresh();
  notice("로그아웃했습니다.");
});
function makeCover(l, parent) {
  const cover = text("div", "", parent);
  cover.className = "lesson-cover";
  cover.setAttribute("aria-hidden", "true");
  text("span", l.series_title || "솜니움 회원 강의", cover);
  text("strong", l.title, cover);
  if (localCover(l.thumbnail_url) || typeof l.thumbnail_url === "string" && /^https:\/\/i\.ytimg\.com\/vi\/[A-Za-z0-9_-]{11}\/mqdefault\.jpg$/.test(l.thumbnail_url)) {
    const image = document.createElement("img");
    image.alt = "";
    image.loading = "lazy";
    image.decoding = "async";
    image.referrerPolicy = "no-referrer";
    image.width = 320;
    image.height = 180;
    const fallback = () => { image.remove(); cover.classList.remove("has-thumbnail"); };
    image.onerror = fallback;
    image.onload = () => { if (image.naturalWidth <= 120) fallback(); };
    cover.classList.add("has-thumbnail");
    cover.append(image);
    image.src = l.thumbnail_url;
  }
  return cover;
}
function lessonRow(l, parent) {
  const row = text("article", "", parent);
  row.className = "catalog-row";
  makeCover(l, row);
  const info = text("div", "", row);
  text("h3", l.title, info);
  text("p", l.description, info).className = "lesson-description";
  row.id = "lecture-" + l.id;
  if (!l.available) {
    action(user ? "후원회원으로 강의 보기" : "로그인하고 강의 보기", row, () => {
      if (!user) { mode(false); show("entry", true); $("entry").scrollIntoView({block:"start"}); }
      else {
        notice(me?.suspended ? "계정 이용 상태를 관리자에게 확인해 주세요." : "가입만으로는 시청할 수 없습니다. 후원 확인 후 강의와 자료가 열립니다.");
        $(me ? "membership" : "profile-panel").scrollIntoView({block:"start"});
      }
    });
    return;
  }
  action("강의 보기", row, () => play(l));
  const materials = text("div", "", row); materials.className = "lesson-materials"; materials.dataset.lessonId = l.id;
  action("강의자료·추가자료", materials, () => renderMaterials(l, materials));
}
function render() {
  const q = $("search").value.trim().toLowerCase(), series = $("series").value;
  const list = lessons.filter(l => (!series || l.series_title === series) && `${l.title} ${l.series_title} ${l.description}`.toLowerCase().includes(q));
  $("catalog").replaceChildren();
  $("count").textContent = `등록 영상 ${lessons.length}개 · 검색 결과 ${list.length}개`;
  for (const group of seriesGroups(list)) {
    if (!group.bundled) { lessonRow(group.lessons[0], $("catalog")); continue; }
    const details = document.createElement("details");
    details.className = "series-group";
    details.dataset.seriesKey = group.key;
    details.open = !!q || !!series || openSeries.has(group.key) || group.lessons.some(l => l.id === new URLSearchParams(window.location.search).get("lesson"));
    const summary = document.createElement("summary");
    makeCover(group.lessons[0], summary);
    const label = text("div", "", summary);
    text("h3", group.name, label);
    text("p", `${group.lessons.length}개 강의 · 눌러서 펼쳐보기`, label).className = "muted";
    details.append(summary);
    const body = text("div", "", details); body.className = "series-lessons";
    for (const l of group.lessons) lessonRow(l, body);
    details.addEventListener("toggle", () => { if (details.open) openSeries.add(group.key); else openSeries.delete(group.key); });
    $("catalog").append(details);
  }
  for (const box of $("catalog").querySelectorAll(".lesson-materials")) {
    const lesson = lessons.find((l) => l.id === box.dataset.lessonId);
    if (lesson && openMaterials.has(lesson.id)) renderMaterials(lesson, box).catch(() => {});
  }
}
$("search").oninput = render;
$("series").onchange = render;
async function play(l) {
  const who = user?.id;
  const generation = refreshGeneration;
  const resource = await rpc("resource", { p_id: l.id });
  if (generation !== refreshGeneration || !who || user?.id !== who || !me?.can_learn || !lessons.some((row) => row.id === l.id)) return;
  let src;
  if (resource.provider === "youtube" && /^[A-Za-z0-9_-]{11}$/.test(resource.video_id)) {
    const u = new URL(`https://www.youtube-nocookie.com/embed/${resource.video_id}`);
    u.searchParams.set("origin", location.origin);
    src = u.href;
  } else if (resource.provider === "vimeo" && /^[0-9]{6,12}$/.test(resource.video_id)) {
    const u = new URL(`https://player.vimeo.com/video/${resource.video_id}`);
    if (resource.video_privacy) u.searchParams.set("h", resource.video_privacy);
    src = u.href;
  } else throw new Error("영상 연결 정보를 확인해 주세요.");
  activeLesson = l.id;
  $("player-region").replaceChildren();
  text("h3", l.title, $("player-region"));
  const frame = document.createElement("iframe");
  frame.className = "member-player";
  frame.src = src;
  frame.title = l.title;
  frame.allow = "encrypted-media; fullscreen; picture-in-picture";
  frame.allowFullscreen = true;
  frame.referrerPolicy = "strict-origin-when-cross-origin";
  $("player-region").append(frame);
  text("p", "회원 강의 링크와 자료를 외부에 공유하지 말아 주세요.", $("player-region")).className = "muted";
  const materialRegion = text("div", "", $("player-region"));
  await renderMaterials(l, materialRegion);
  $("player-region").scrollIntoView({ block: "nearest" });
}
form("director-form", async (f) => {
  await rpc("set_director", { p_email: String(f.get("email")).trim().toLowerCase(), p_enabled: true, p_roster_confirmed: f.get("confirmed") === "on" });
  $("director-form").reset();
  notice("내부 이사 명단에 등록했습니다. 같은 이메일 본인 확인 후 강의 권한이 적용됩니다.");
});
async function admin(generation) {
  const [members, registered, directors, audit, series, materials] = await Promise.all([rpc("admin_members"), rpc("admin_lessons"), rpc("admin_directors"), rpc("admin_audit"), rpc("admin_series"), rpc("admin_materials")]);
  if (generation !== refreshGeneration || !me?.admin) return;
  managedLessons = newestFirst(registered);
  renderManaged();
  renderSeriesAdmin(series);
  renderMaterialAdmin(materials);
  $("directors").replaceChildren();
  for (const d of directors) {
    const row = text("p", d.email + " · " + (d.enabled ? "유효" : "종료"), $("directors"));
    if (d.enabled) action("이사 자격 종료", row, async () => {
      if (!confirm(d.email + " 이사 자격을 종료할까요?")) return;
      await rpc("set_director", { p_email: d.email, p_enabled: false, p_roster_confirmed: false });
      await refresh();
    });
  }
  $("audit").replaceChildren();
  for (const a of audit) text("p", new Date(a.at).toLocaleString("ko-KR") + " · " + a.action, $("audit"));
  $("members").replaceChildren();
  for (const m of members) {
    const row = text("article", "", $("members"));
    row.className = "member";
    text("h3", m.name, row);
    text("p", m.email, row);
    const supporterLine = supporterNameLine(m);
    if (supporterLine) text("p", supporterLine, row);
    text("p", `${m.suspended ? "계정 중지" : stateNames[m.supporter_state] || "일반회원"}`, row);
    if (m.supporter_state === "qualified" && !m.checked_at) {
      text("p", "신청 기준 이용 승인 · 월별 후원 내역 대조 전", row);
      if (m.notice_state && m.notice_state !== "sent") action("신청 알림 다시 보내기", row, async () => {
        const {data, error} = await db.functions.invoke("supporter-notice", {body:{user_id:m.id}});
        if (error) throw new Error("알림을 보내지 못했습니다. 발송 계정 설정을 확인해 주세요.");
        await refresh();
        notice(data?.sent ? "신청 알림을 발송했습니다." : "알림 발송 대기 중입니다. 1분 후 다시 확인해 주세요.");
      });
    }
    const label = text("label", "", row);
    label.className = "check";
    const check = document.createElement("input");
    check.type = "checkbox";
    label.append(check);
    text("span", "한빛누리에서 월 1만 원 이상 후원을 확인했습니다.", label);
    const actions = text("div", "", row);
    actions.className = "actions";
    action(m.supporter_state === "qualified" ? "월별 후원 확인 완료" : "후원 자격 승인", actions, async () => {
      if (!check.checked) throw new Error("후원 내역 확인란을 먼저 체크해 주세요.");
      if (!confirm(`${m.name} 회원의 후원 자격을 승인할까요?`)) return;
      await rpc("review_supporter", { p_user: m.id, p_state: "qualified", p_minimum_confirmed: true });
      await refresh();
    });
    for (const [title, state] of [["후원 보류", "held"], ["후원 종료", "withdrawn"]]) action(title, actions, async () => {
      if (!confirm(`${m.name} · ${title} 처리할까요?`)) return;
      await rpc("review_supporter", { p_user: m.id, p_state: state, p_minimum_confirmed: false });
      await refresh();
    });
    if (m.id !== user.id) action(m.suspended ? "계정 재개" : "계정 중지", actions, async () => {
      if (!confirm(`${m.name} 계정을 ${m.suspended ? "재개" : "중지"}할까요?`)) return;
      await rpc("suspend_member", { p_user: m.id, p_suspended: !m.suspended });
      await refresh();
    });
  }
}
function isQa(title) {
  return /질의\s*응답|질문\s*(?:과|및|&)?\s*(?:답변|응답)|\bq\s*(?:&|and|n|\/)\s*a\b/i.test(title.normalize("NFC"));
}
function sourceFields(raw) {
  const u = new URL(raw);
  if (u.protocol !== "https:") throw new Error("https 영상 주소를 입력해 주세요.");
  let provider = "", id = "", privacy = "";
  if (["youtube.com", "www.youtube.com", "www.youtube-nocookie.com", "youtu.be"].includes(u.hostname)) {
    provider = "youtube";
    id = u.hostname === "youtu.be" ? u.pathname.slice(1) : u.pathname.startsWith("/embed/") ? u.pathname.split("/")[2] : u.searchParams.get("v");
    if (!/^[A-Za-z0-9_-]{11}$/.test(id || "")) throw new Error("유튜브 영상 주소를 확인해 주세요.");
  } else if (["vimeo.com", "www.vimeo.com", "player.vimeo.com"].includes(u.hostname)) {
    provider = "vimeo";
    const parts = u.pathname.split("/").filter(Boolean);
    if (parts[0] === "video") parts.shift();
    id = parts[0] || "";
    privacy = u.searchParams.get("h") || parts[1] || "";
    if (!/^[0-9]{6,12}$/.test(id) || privacy && !/^[A-Za-z0-9]{6,32}$/.test(privacy)) throw new Error("Vimeo 영상 주소를 확인해 주세요.");
  } else throw new Error("YouTube 또는 Vimeo 영상 주소를 입력해 주세요.");
  return { provider, id, privacy };
}
function sourceUrl(l) {
  return l.provider === "youtube" ? `https://www.youtube.com/watch?v=${l.video_id}` : `https://vimeo.com/${l.video_id}${l.video_privacy ? "/" + l.video_privacy : ""}`;
}
function lessonArgs(l) {
  return { p_id: l.id || null, p_title: l.title, p_description: l.description || "", p_series: l.series_title || "", p_position: Number(l.position), p_era: l.era, p_published: l.published, p_provider: l.provider, p_video_id: l.video_id, p_video_privacy: l.video_privacy || "" };
}
function renderManaged() {
  const q = $("admin-search").value.toLowerCase();
  $("admin-lessons").replaceChildren();
  for (const l of managedLessons.filter((l2) => `${l2.title} ${l2.series_title}`.toLowerCase().includes(q))) {
    const row = text("article", "", $("admin-lessons"));
    row.className = "member";
    text("h4", l.title, row);
    text("p", (l.published ? "표시" : "숨김") + " · " + l.series_title, row);
    action("수정", row, () => {
      const f = $("lesson-form");
      for (const [key, value] of Object.entries({ id: l.id, title: l.title, description: l.description, series: l.series_title, position: l.position, era: l.era, video: sourceUrl(l) })) f.elements[key].value = value;
      f.elements.published.checked = l.published;
      f.scrollIntoView({ block: "start" });
    });
    action(l.published ? "강의 숨김" : "강의 표시", row, async () => {
      if (!confirm(`${l.title} 강의를 ${l.published ? "숨길까요?" : "표시할까요?"}`)) return;
      await rpc("save_lesson", lessonArgs({ ...l, published: !l.published }));
      await refresh();
    });
  }
}
$("admin-search").oninput = renderManaged;
$("new-lesson").onclick = () => {
  $("lesson-form").reset();
  $("lesson-form").elements.id.value = "";
};
form("lesson-form", async (f) => {
  if (f.get("published") === "on" && isQa(String(f.get("title")))) throw new Error("질의응답 영상은 회원 목록에 게시하지 않습니다.");
  const source = sourceFields(String(f.get("video")));
  await rpc("save_lesson", lessonArgs({ id: f.get("id"), title: f.get("title"), description: f.get("description"), series_title: f.get("series"), position: f.get("position"), era: f.get("era"), published: f.get("published") === "on", provider: source.provider, video_id: source.id, video_privacy: source.privacy }));
  $("lesson-form").reset();
  $("lesson-form").elements.id.value = "";
  await refresh();
  notice("강의를 저장했습니다.");
});
async function loadCatalog(generation, allowed = []) {
  const publicRows = await rpc("public_catalog");
  if (generation !== refreshGeneration) return;
  const rows = mergeCatalog(publicRows, allowed);
  const plan = catalogPlan({prev:catalogSig, userId:user?.id || "public-visitor", rows, canLearn:true, rendered:$("catalog").childElementCount > 0});
  lessons = newestFirst(rows);
  show("catalog-panel", true);
  $("catalog-help").textContent = me?.full_access ? "강의 보기와 자료 버튼으로 이용하세요." : "강의 목록은 누구나 둘러볼 수 있습니다. 영상과 자료는 후원 신청 완료를 알린 뒤 이용할 수 있습니다.";
  if (plan.action === "render") {
    const scroll = window.scrollY, selected = $("series").value;
    $("series").replaceChildren();
    text("option", "전체 시리즈", $("series")).value = "";
    for (const series of [...new Set(lessons.map(x => x.series_title))].filter(Boolean)) text("option", series, $("series")).value = series;
    $("series").value = selected;
    render(); catalogSig = plan.signature;
    window.scrollTo(0,scroll);
    const requested = new URLSearchParams(window.location.search).get("lesson");
    if (!requestedLessonShown && rows.some(row => row.id === requested)) {
      document.getElementById("lecture-" + requested)?.scrollIntoView({block:"center"});
      requestedLessonShown = true;
    }
  }
}
async function refresh() {
  const generation = ++refreshGeneration;
  const { data, error } = await db.auth.getUser();
  if (generation !== refreshGeneration) return;
  if (error || !data.user) {
    user = null;
    me = null;
    clearPrivate();
    for (const id of ["membership", "profile-panel", "catalog-panel", "admin-panel", "code-panel", "logout", "admin-shortcuts"]) show(id, false);
    settingPassword = false;
    sessionStorage.removeItem("somnium-password-pending");
    show("password-panel", false);
    show("entry", $("otp-panel").hidden);
    notice(signup ? "처음 한 번 이메일 인증 후 비밀번호와 이름을 입력하면 가입할 수 있습니다." : "가입한 이메일과 비밀번호로 로그인하세요.");
    await loadCatalog(generation);
    return;
  }
  if (user?.id !== data.user.id) privateEpoch++;
  user = data.user;
  if (settingPassword) {
    clearPrivate();
    for (const id of ["entry", "otp-panel", "membership", "profile-panel", "catalog-panel", "admin-panel", "code-panel"]) show(id, false);
    show("password-panel", true);
    show("logout", true);
    notice("이메일이 확인됐습니다. 다음부터 사용할 비밀번호를 정해 주세요.");
    return;
  }
  show("password-panel", false);
  try {
    const profile = await rpc("me");
    if (generation !== refreshGeneration) return;
    me = profile;
    show("logout", true);
    show("entry", false);
    show("profile-panel", !me);
    show("membership", !!me);
    show("code-panel", !!me && !me.suspended);
    show("admin-panel", !!me?.admin);
    show("admin-shortcuts", !!me?.admin);
    if (!me || !me.can_learn) clearPrivate();
    if (!me) {
      notice("이메일이확인됐습니다. 가입 정보를 입력해 주세요.");
      await loadCatalog(generation);
      return;
    }
    $("identity").textContent = me.name + " · " + user.email;
    $("membership-state").textContent = me.suspended ? "계정 이용이 중지됐습니다." : me.full_access ? "모든 회원 강의 이용 가능" : me.can_learn ? "등록한 세미나 강의 이용 가능" : stateNames[me.supporter_state] || "일반회원";
    show("supporter-request", !me.suspended && !me.full_access && ["not_requested", "pending"].includes(me.supporter_state));
    show("supporter-guide", !me.suspended && !me.full_access);
    await reportUI.load();
    if (generation !== refreshGeneration) return;
    const allowed = me.can_learn ? await rpc("catalog") : [];
    await loadCatalog(generation, allowed);
    if (generation !== refreshGeneration) return;
    if (me.can_learn) {
      if (activeLesson) {
        const checkingLesson = activeLesson;
        try {
          await rpc("resource", { p_id: checkingLesson });
        } catch {
          if (generation === refreshGeneration && activeLesson === checkingLesson) {
            $("player-region").replaceChildren();
            activeLesson = "";
          }
        }
      }
    }
    if (generation !== refreshGeneration) return;
    if (me.admin) await admin(generation);
    else {
      $("issued-code-value").value = ""; show("issued-code", false);
      managedLessons = [];
      for (const id of ["members", "admin-lessons", "directors", "audit", "series-codes", "series-entitlements", "admin-materials"]) $(id).replaceChildren();
      $("lesson-form").reset();
      $("lesson-form").elements.id.value = "";
    }
    if (generation !== refreshGeneration) return;
    notice(me.suspended ? "계정 이용이 중지됐습니다." : "현재 이용 상태를 확인했습니다.");
  } catch (e) {
    if (generation !== refreshGeneration) return;
    clearPrivate();
    show("admin-panel", false);
    show("admin-shortcuts", false);
    show("catalog-panel", false);
    throw e;
  }
}

async function renderMaterials(lesson, parent) {
  const generation = refreshGeneration, who = user?.id;
  const rows = await rpc("materials", {p_lesson: lesson.id});
  if (generation !== refreshGeneration || !who || who !== user?.id || !parent.isConnected || !lessons.some(l => l.id === lesson.id)) return;
  parent.replaceChildren();
  openMaterials.add(lesson.id);
  for (const [kind, label] of [["lesson", "이 강의 자료"], ["extra", "시리즈 공통 추가자료"]]) {
    const files = rows.filter(m => m.kind === kind);
    text("h4", label, parent);
    if (!files.length) text("p", "등록된 자료가 없습니다.", parent).className = "muted";
    for (const file of files) action(file.title + " · PDF 내려받기", parent, async () => {
      const offered = await downloadMaterial({id:file.id,lessonId:lesson.id,path:file.storage_path,filename:file.filename}, {
        access: () => ({userId:user?.id,epoch:privateEpoch,canLearn:!!me?.can_learn,lessonAvailable:lessons.some(l => l.id === lesson.id)}),
        listMaterials: (id) => rpc("materials", {p_lesson:id}),
        download: async (path) => {
          const {data,error} = await db.storage.from("somnium-materials").download(path, {}, {cache:"no-store"});
          if (error) throw new Error("자료 이용 권한과 연결 상태를 확인해 주세요.");
          return data;
        },
        offer: (blob,filename) => {
          const url = URL.createObjectURL(blob), link = document.createElement("a");
          link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();
          setTimeout(() => URL.revokeObjectURL(url), 60000);
        },
      });
      if (!offered) notice("이용 상태가 바뀌어 내려받기를 중단했습니다. 상태를 확인해 주세요.");
      else notice(file.filename + " 내려받기를 시작했습니다. 파일이 저장되지 않으면 브라우저 주소창의 다운로드 허용 안내를 확인해 주세요.");
    });
  }
}
form("redeem-code-form", async f => {
  const result = await rpc("redeem_code", {p_code: String(f.get("code"))});
  $("redeem-code-form").reset();
  if (!result.ok) throw new Error(result.reason === "wait" ? "입력 횟수가 많습니다. 1분 뒤 다시 시도해 주세요." : "등록할 수 없는 코드입니다. 코드나 현재 이용 상태를 관리자에게 확인해 주세요.");
  await refresh(); notice(result.title + " 이용권을 등록했습니다. 아래에서 강의와 자료를 이용하세요.");
});
form("issue-code-form", async f => {
  const generation = refreshGeneration, who = user?.id;
  const result = await rpc("issue_code", {p_label: String(f.get("label"))});
  if (generation !== refreshGeneration || !who || who !== user?.id || !me?.admin) return;
  $("issued-code-value").value = result.code;
  $("issued-code-value").type = "password"; $("show-issued-code").textContent = "코드 표시";
  show("issued-code", true); await refresh(); notice("수강 코드를 발급했습니다. 참여자에게 직접 전달해 주세요.");
});
$("show-issued-code").onclick = () => {
  const field = $("issued-code-value"); field.type = field.type === "password" ? "text" : "password";
  $("show-issued-code").textContent = field.type === "password" ? "코드 표시" : "코드 가리기";
};
$("copy-issued-code").onclick = () => run($("copy-issued-code"), async () => {
  await navigator.clipboard.writeText($("issued-code-value").value); notice("수강 코드를 복사했습니다.");
});
function renderSeriesAdmin(data) {
  $("series-codes").replaceChildren(); $("series-entitlements").replaceChildren();
  for (const code of data.codes) {
    const row = text("p", `${code.label} · ${code.enabled ? "등록 열림" : "등록 종료"} · ${code.registrations}명`, $("series-codes"));
    action(code.enabled ? "새 등록 종료" : "새 등록 재개", row, async () => {
      await rpc("set_code", {p_id: code.id, p_enabled: !code.enabled}); await refresh();
    });
  }
  for (const e of data.entitlements) {
    const row = text("p", e.email + " · " + (e.enabled ? "이용 가능" : "이용권 중지"), $("series-entitlements"));
    action(e.enabled ? "이용권 중지" : "이용권 재개", row, async () => {
      if (!confirm(e.email + "의 세미나 이용권을 변경할까요?")) return;
      await rpc("set_entitlement", {p_user: e.user_id, p_enabled: !e.enabled}); await refresh();
    });
  }
}
form("material-form", async f => {
  const file = f.get("file");
  if (!(file instanceof File) || !file.size || file.size > 25 * 1024 * 1024 || !file.name.toLowerCase().endsWith(".pdf")) throw new Error("25MB 이하 PDF를 선택해 주세요.");
  const header = await file.slice(0,5).text();
  if (header !== "%PDF-") throw new Error("PDF 파일 형식을 확인해 주세요.");
  const path = crypto.randomUUID() + ".pdf";
  const {error} = await db.storage.from("somnium-materials").upload(path, file, {contentType: "application/pdf", upsert: false, cacheControl: "0"});
  if (error) throw new Error("자료를 올리지 못했습니다. 관리자 권한과 연결 상태를 확인해 주세요.");
  await rpc("save_material", {p_lesson: f.get("lesson") || null, p_title: String(f.get("title")), p_filename: file.name, p_path: path});
  $("material-form").reset(); await refresh(); notice("비공개 자료를 등록했습니다.");
});
function renderMaterialAdmin(rows) {
  const selected = $("material-lesson").value;
  $("material-lesson").replaceChildren();
  text("option", "현대자본주의 세미나 1 · 공통 추가자료", $("material-lesson")).value = "";
  for (const l of managedLessons.filter(l => l.published)) text("option", l.title, $("material-lesson")).value = l.id;
  $("material-lesson").value = selected;
  $("admin-materials").replaceChildren();
  for (const m of rows) {
    const row = text("p", m.title + " · " + (m.enabled ? "표시" : "숨김"), $("admin-materials"));
    action(m.enabled ? "자료 숨김" : "자료 표시", row, async () => {await rpc("set_material", {p_id:m.id,p_enabled:!m.enabled});await refresh();});
  }
}

db.auth.onAuthStateChange((event) => {
  if (event === "SIGNED_OUT") {
    refreshGeneration++;
    settingPassword = false;
    sessionStorage.removeItem("somnium-password-pending");
    $("password-form").reset();
    show("password-panel", false);
    show("otp-panel", false);
    user = null;
    me = null;
    clearPrivate();
    for (const id of ["membership", "admin-panel", "admin-shortcuts", "catalog-panel", "profile-panel", "code-panel"]) show(id, false);
    show("entry", true);
    show("logout", false);
  }
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refresh().catch((e) => notice(e.message));
});
setInterval(() => {
  if (user && document.visibilityState === "visible") refresh().catch((e) => notice(e.message));
}, 3e4);
mode(entryMode(window.location.search) === "signup");
await refresh().catch((e) => notice(e.message));

// Hash targets become visible only after Auth/catalog refresh has finished.
if (window.location.hash === "#entry" && !$("entry").hidden) $("entry").scrollIntoView({block:"start"});
else if (window.location.hash === "#catalog-panel" && !new URLSearchParams(window.location.search).has("lesson") && !$("catalog-panel").hidden) $("catalog-panel").scrollIntoView({block:"start"});
else if (["#members-admin", "#admin-panel"].includes(window.location.hash) && me?.admin) document.getElementById(window.location.hash.slice(1))?.scrollIntoView({block:"start"});

if (window.location.hash === "#accounting-panel") $("accounting-panel").scrollIntoView({block:"start"});
if (window.location.hash === "#report-upload" && me?.admin) $("report-upload").scrollIntoView({block:"start"});

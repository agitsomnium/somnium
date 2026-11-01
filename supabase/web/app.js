import { createClient } from "@supabase/supabase-js";
import { newestFirst } from "./order.js";
import { seriesGroups } from "./series.js";
const openSeries = new Set();
const $ = (id) => document.getElementById(id);
const config = await fetch("/runtime-config.json", { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new Error("설정을 읽지 못했습니다.");
  return r.json();
});
const db = createClient(config.url, config.publishableKey, { auth: { storage: sessionStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
let me = null, user = null, lessons = [], signup = false, targetEmail = "", lastSend = 0, activeLesson = "", refreshGeneration = 0, managedLessons = [];
const stateNames = { not_requested: "일반회원 · 후원 확인 전", pending: "후원 확인 대기", qualified: "후원회원 · 강의 이용 가능", held: "후원 확인 보류", withdrawn: "후원 자격 종료" };
function notice(t) {
  $("notice").textContent = t;
}
function show(id, on) {
  $(id).hidden = !on;
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
  lessons = [];
  managedLessons = [];
  activeLesson = "";
  for (const id of ["catalog", "player-region", "members", "admin-lessons", "directors", "audit"]) $(id).replaceChildren();
}
function mode(value) {
  signup = value;
  $("login-tab").setAttribute("aria-pressed", String(!value));
  $("signup-tab").setAttribute("aria-pressed", String(value));
  $("login-form").querySelector("button").textContent = value ? "가입 인증번호 받기" : "인증번호 받기";
  notice(value ? "이메일 확인 후 가입 정보를 입력합니다." : "가입한 이메일로 로그인합니다.");
}
$("login-tab").onclick = () => mode(false);
$("signup-tab").onclick = () => mode(true);
function form(id, fn) {
  $(id).onsubmit = (e) => {
    e.preventDefault();
    run(e.submitter, () => fn(new FormData(e.target)));
  };
}
async function send() {
  const email = targetEmail;
  if (!config.testEmails.includes(email)) throw new Error("현재는 지정된 검토 이메일만 이용할 수 있습니다.");
  if (Date.now() - lastSend < 6e4) throw new Error("인증번호 요청 후 1분을 기다려 주세요.");
  const { error } = await db.auth.signInWithOtp({ email, options: { shouldCreateUser: signup } });
  if (error) throw new Error(safeError(error));
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
  await send();
});
$("existing-otp").onclick = () => {
  targetEmail = String($("login-form").elements.email.value).trim().toLowerCase();
  if (!config.testEmails.includes(targetEmail)) {
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
  const { error } = await db.auth.verifyOtp({ email: targetEmail, token: String(f.get("token")).trim(), type: "email" });
  $("otp-form").reset();
  if (error) throw new Error(safeError(error));
  show("otp-panel", false);
  await refresh();
  notice(me ? "로그인했습니다." : "이메일이 확인됐습니다. 가상 정보로 가입을 완료해 주세요.");
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
  await rpc("complete_profile", { p_name: String(f.get("name")).trim(), p_birth: f.get("birth"), p_phone: String(f.get("phone")).replace(/[-\s]/g, ""), p_consent: f.get("consent") === "on" });
  $("profile-form").reset();
  await refresh();
  notice("일반회원 가입을 마쳤습니다. 후원 확인 전에는 회원 강의를 이용할 수 없습니다.");
});
$("supporter-request").onclick = () => run($("supporter-request"), async () => {
  await rpc("request_supporter");
  await refresh();
  notice("후원 확인을 요청했습니다. 관리자의 확인을 기다려 주세요.");
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
  if (typeof l.thumbnail_url === "string" && /^https:\/\/i\.ytimg\.com\/vi\/[A-Za-z0-9_-]{11}\/mqdefault\.jpg$/.test(l.thumbnail_url)) {
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
  action("강의 보기", row, () => play(l));
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
    details.open = !!q || !!series || openSeries.has(group.key);
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
  text("p", "회원 강의 링크를 외부에 공유하지 말아 주세요. 강의 자료는 준비 중입니다.", $("player-region")).className = "muted";
  $("player-region").scrollIntoView({ block: "nearest" });
}
form("director-form", async (f) => {
  await rpc("set_director", { p_email: String(f.get("email")).trim().toLowerCase(), p_enabled: true, p_roster_confirmed: f.get("confirmed") === "on" });
  $("director-form").reset();
  notice("내부 이사 명단에 등록했습니다. 같은 이메일 본인 확인 후 강의 권한이 적용됩니다.");
});
async function admin(generation) {
  const [members, registered, directors, audit] = await Promise.all([rpc("admin_members"), rpc("admin_lessons"), rpc("admin_directors"), rpc("admin_audit")]);
  if (generation !== refreshGeneration || !me?.admin) return;
  managedLessons = newestFirst(registered);
  renderManaged();
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
    text("p", `${m.suspended ? "계정 중지" : stateNames[m.supporter_state] || "일반회원"}`, row);
    const label = text("label", "", row);
    label.className = "check";
    const check = document.createElement("input");
    check.type = "checkbox";
    label.append(check);
    text("span", "한빛누리에서 월 1만 원 이상 후원을 확인했습니다.", label);
    const actions = text("div", "", row);
    actions.className = "actions";
    action("후원 자격 승인", actions, async () => {
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
async function refresh() {
  const generation = ++refreshGeneration;
  const { data, error } = await db.auth.getUser();
  if (generation !== refreshGeneration) return;
  if (error || !data.user) {
    user = null;
    me = null;
    clearPrivate();
    for (const id of ["membership", "profile-panel", "catalog-panel", "admin-panel", "logout"]) show(id, false);
    show("entry", $("otp-panel").hidden);
    notice("이메일 인증번호로 로그인해 주세요.");
    return;
  }
  user = data.user;
  try {
    const profile = await rpc("me");
    if (generation !== refreshGeneration) return;
    me = profile;
    show("logout", true);
    show("entry", false);
    show("profile-panel", !me);
    show("membership", !!me);
    show("admin-panel", !!me?.admin);
    show("catalog-panel", !!me?.can_learn);
    if (!me || !me.can_learn) clearPrivate();
    if (!me) {
      notice("이메일이 확인됐습니다. 가입 정보를 입력해 주세요.");
      return;
    }
    $("identity").textContent = me.name + " · " + user.email;
    $("membership-state").textContent = me.suspended ? "계정 이용이 중지됐습니다." : me.can_learn ? "회원 강의 이용 가능" : stateNames[me.supporter_state] || "일반회원";
    show("supporter-request", !me.suspended && !me.can_learn && me.supporter_state !== "pending");
    show("supporter-guide", !me.suspended && !me.can_learn);
    if (me.can_learn) {
      const rows = await rpc("catalog");
      if (generation !== refreshGeneration) return;
      lessons = newestFirst(rows);
      const selected = $("series").value;
      $("series").replaceChildren();
      text("option", "전체 시리즈", $("series")).value = "";
      for (const series of [...new Set(lessons.map((x) => x.series_title))].filter(Boolean)) text("option", series, $("series")).value = series;
      $("series").value = selected;
      render();
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
      managedLessons = [];
      for (const id of ["members", "admin-lessons", "directors", "audit"]) $(id).replaceChildren();
      $("lesson-form").reset();
      $("lesson-form").elements.id.value = "";
    }
    if (generation !== refreshGeneration) return;
    notice(me.suspended ? "계정 이용이 중지됐습니다." : "현재 이용 상태를 확인했습니다.");
  } catch (e) {
    if (generation !== refreshGeneration) return;
    clearPrivate();
    show("admin-panel", false);
    show("catalog-panel", false);
    throw e;
  }
}
db.auth.onAuthStateChange((event) => {
  if (event === "SIGNED_OUT") {
    refreshGeneration++;
    user = null;
    me = null;
    clearPrivate();
    for (const id of ["membership", "admin-panel", "catalog-panel", "profile-panel"]) show(id, false);
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
await refresh().catch((e) => notice(e.message));

// Back navigation always has an explicit home fallback for a directly opened page.
document.addEventListener('click', function (event) {
  const button = event.target.closest && event.target.closest('[data-page-back]');
  if (!button) return;
  if (window.history.length > 1) window.history.back();
  else window.location.assign(button.getAttribute('data-back-home') || '/');
});

// 지난 일정의 직접 링크도 접힌 기록을 펼친 뒤 해당 항목으로 이동한다.
function revealArchivedTarget() {
  if (!window.location.hash) return;
  let id;
  try { id = decodeURIComponent(window.location.hash.slice(1)); }
  catch (_) { return; }
  const target = document.getElementById(id);
  if (!target) return;
  let parent = target.parentElement;
  let opened = false;
  while (parent) {
    if (parent.tagName === 'DETAILS' && !parent.open) {
      parent.open = true;
      opened = true;
    }
    parent = parent.parentElement;
  }
  if (opened) target.scrollIntoView({ block: 'start' });
}
window.addEventListener('hashchange', revealArchivedTarget);
revealArchivedTarget();

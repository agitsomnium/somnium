// Back navigation always has an explicit home fallback for a directly opened page.
document.addEventListener('click', function (event) {
  const button = event.target.closest && event.target.closest('[data-page-back]');
  if (!button) return;
  if (window.history.length > 1) window.history.back();
  else window.location.assign(button.getAttribute('data-back-home') || '/');
});

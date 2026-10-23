document.addEventListener('click', function (ev) {
  var b = ev.target.closest && ev.target.closest('[data-copy]');
  if (!b) return;
  var text = b.getAttribute('data-copy');
  var done = function () { var t = b.textContent; b.textContent = '복사했습니다'; setTimeout(function () { b.textContent = t; }, 1600); };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(done, function () {}); return; }
  } catch (e) {}
  try { var a = document.createElement('textarea'); a.value = text; document.body.appendChild(a); a.select(); document.execCommand('copy'); a.remove(); done(); } catch (e) {}
});

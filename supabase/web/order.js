// Dates in lecture titles refer to the session, not the publication year of a book.
const capitalismDates = [20260917, 20261001, 20261008, 20261015, 20261022, 20261029];
function validDate(year, month, day) {
  const d = new Date(Date.UTC(year, month - 1, day));
  return d.getUTCFullYear() === year && d.getUTCMonth() === month - 1 && d.getUTCDate() === day ? year * 10000 + month * 100 + day : 0;
}
function explicitDate(title) {
  const compact = title.match(/^(\d{2})(\d{2})(\d{2})(?:\D|$)/);
  if (compact) return validDate(2000 + Number(compact[1]), Number(compact[2]), Number(compact[3]));
  for (const m of title.matchAll(/(?:^|[^\d])((?:20)?\d{2})[.\/-](\d{1,2})[.\/-](\d{1,2})(?!\d)/g)) {
    const year = m[1].length === 2 ? 2000 + Number(m[1]) : Number(m[1]);
    const date = validDate(year, Number(m[2]), Number(m[3]));
    if (date) return date;
  }
  return 0;
}
function titleYears(title) {
  const withoutBookYear = title.replace(/『[^』]*』\s*\(\d{4}\)/g, '');
  return [...withoutBookYear.matchAll(/20\d{2}/g)].map(m => Number(m[0]));
}
export function newestFirst(rows) {
  const seriesYears = new Map();
  for (const row of rows) {
    const year = Math.floor(explicitDate(row.title) / 10000);
    if (!year || !row.series_title) continue;
    if (!seriesYears.has(row.series_title)) seriesYears.set(row.series_title, new Set());
    seriesYears.get(row.series_title).add(year);
  }
  function key(row) {
    if (row.era === 'current' && /현대.*자본/.test(row.series_title)) return capitalismDates[Number(row.position) - 1] || 20260000;
    const exact = explicitDate(row.title);
    if (exact) return exact;
    const years = titleYears(row.title);
    const series = titleYears(row.series_title || '');
    const shared = seriesYears.get(row.series_title);
    const year = years.length ? Math.max(...years) : series.length ? Math.max(...series) : shared?.size === 1 ? [...shared][0] : row.era === 'future' ? 2027 : 0;
    const short = row.title.match(/(?:^|[_\s])(\d{1,2})\.(\d{1,2})(?:\D|$)/);
    return short && year ? validDate(year, Number(short[1]), Number(short[2])) || year * 10000 : year * 10000;
  }
  return [...rows].sort((a, b) => key(b) - key(a) ||
    (a.series_title === b.series_title ? (key(a) % 10000 === 0 ? Number(b.position) - Number(a.position) : Number(a.position) - Number(b.position)) : a.series_title.localeCompare(b.series_title, 'ko')) || a.id.localeCompare(b.id));
}

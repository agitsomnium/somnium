// Broad archive labels are categories, not series products.
const archiveCategories = new Set(['이전 솜니움 강좌', '솜니움 이전 강좌 · 2025~2026']);
export function seriesGroups(rows) {
  const groups = [], found = new Map();
  for (const row of rows) {
    const name = row.series_title?.trim() || '';
    const bundled = !!name && !archiveCategories.has(name);
    const modern = bundled && row.era === 'current' && name === '현대 자본주의 이해하기';
    const key = bundled ? modern ? 'modern-capitalism-2026' : JSON.stringify([row.era, name]) : `lesson:${row.id}`;
    let group = found.get(key);
    if (!group) {
      group = {key, bundled, name: modern ? '현대자본주의 세미나' : name, lessons: []};
      found.set(key, group); groups.push(group);
    }
    group.lessons.push(row);
  }
  return groups;
}

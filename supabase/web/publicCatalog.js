// Public metadata alone never grants playback or file access.
export function mergeCatalog(publicRows, allowedRows) {
  const allowed = new Map(allowedRows.map(row => [row.id, row]));
  return publicRows.map(row => ({...row, ...allowed.get(row.id),
    ...(localCover(row.thumbnail_url) ? {thumbnail_url:row.thumbnail_url} : {}),
    available:allowed.has(row.id)}));
}
export const localCover = url => typeof url === 'string' && /^\/assets\/lecture-covers\/[a-f0-9-]{36}\.jpg$/.test(url);


/**
 * Download a classroom material with a race-safe authorization check.
 *
 * Access is captured once at the start. The download is only offered to the
 * user if, at completion time, the same user (non-empty id) is still signed in
 * with the same access epoch and still holds the required permissions.
 *
 * @param {{id:string,lessonId:string,path:string,filename:string}} file
 * @param {object} deps
 * @returns {Promise<boolean>} true if offered, false if suppressed
 */
export async function downloadMaterial(file, deps) {
  const { access, listMaterials, download, offer } = deps;

  const start = { ...access() };
  if (!start || !start.userId || !start.canLearn || !start.lessonAvailable) {
    throw new Error('현재 자료 이용 권한이 없습니다.');
  }

  const materials = await listMaterials(file.lessonId);
  if (!Array.isArray(materials) || !materials.some((m) => m && m.id === file.id)) {
    throw new Error('현재 내려받을 수 없는 자료입니다.');
  }

  const blob = await download(file.path);

  const end = access();
  const stillAuthorized =
    end &&
    end.userId &&
    end.userId === start.userId &&
    end.epoch === start.epoch &&
    end.canLearn === true &&
    end.lessonAvailable === true;

  if (!stillAuthorized) {
    return false;
  }

  offer(blob, file.filename);
  return true;
}



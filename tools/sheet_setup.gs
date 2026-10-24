/**
 * 솜니움 홈페이지 관리 시트 꾸미기 — 지금 시트에 든 내용을 쉬운 한글 꼴로 다시 정리하고 꾸민다.
 * 솜니움 계정 Apps Script 프로젝트 「솜니움 홈페이지 시트 꾸미기」에 들어 있다. 「setup」 실행. 여러 번 실행해도 내용은 그대로 남는다.
 * 홈페이지는 머리글의 괄호 안 설명을 무시하고 읽으므로(scripts/sheet_friendly.py), 머리글 글자는 이 파일에서 고치면 된다.
 */
var SITE = 'https://somniumagit.com/';
var SHEET_ID = '1f_uDJFAEtqDjbTBaKrQGOJmvNzI8vpabdfFzHEK3EQE';
// [탭 이름, 예전 탭 이름, 탭 색, [[내부 칸, 머리글], ...]]
var TABS = [
  ['세미나', '세미나', '#b5482a', [['제목', '제목'], ['부제', '부제 (한 줄)'], ['상태', '상태 (비우면 날짜 보고 자동)'],
    ['시작일', '시작일 (2026-11-05)'], ['종료일', '종료일'], ['장소', '장소'], ['강사진_id', '강사 (강사진 탭 이름)'],
    ['참가비', '참가비'], ['참여방법', '참여 방법'], ['신청_url', '신청 링크 (구글폼 주소)'], ['소개', '소개'],
    ['취소사유', '취소 이유'], ['공개', '홈피에 보이기'], ['정렬', '순서 (작을수록 위)'], ['id', '고유이름 (비워 두면 자동)']]],
  ['회차', '회차', '#b5482a', [['세미나_id', '세미나 (세미나 탭 제목)'], ['회차', '회차 (1, 2, 3…)'], ['제목', '제목'],
    ['날짜', '날짜 (2026-11-05)'], ['시간', '시간 (19:00)'], ['자료_url', '자료 링크'], ['공개', '홈피에 보이기'],
    ['id', '고유이름 (비워 두면 자동)']]],
  ['북클럽', '북클럽', '#b5482a', [['제목', '제목'], ['도서', '책'], ['상태', '상태 (비우면 날짜 보고 자동)'],
    ['날짜', '날짜 (여러 날은 ; 로 이어서)'], ['시간', '시간 (19:00)'], ['장소', '장소'], ['신청_url', '신청 링크 (구글폼 주소)'],
    ['소개', '소개'], ['취소사유', '취소 이유'], ['공개', '홈피에 보이기'], ['정렬', '순서 (작을수록 위)'],
    ['id', '고유이름 (비워 두면 자동)']]],
  ['공지', '공지', '#3d6b8f', [['제목', '제목'], ['본문', '본문'], ['링크_url', '링크'], ['게시일', '올린 날 (2026-11-05)'],
    ['공개', '홈피에 보이기'], ['정렬', '순서 (작을수록 위)'], ['id', '고유이름 (비워 두면 자동)']]],
  ['영상', '영상', '#3d6b8f', [['제목', '제목'], ['youtube_url', '유튜브 링크'], ['세미나_id', '세미나 (세미나 탭 제목)'],
    ['회차_id', '회차 (숫자)'], ['날짜', '날짜 (2026-11-05)'], ['공개', '홈피에 보이기'], ['정렬', '순서 (작을수록 위)'],
    ['id', '고유이름 (비워 두면 자동)']]],
  ['강사진', '강사진', '#3d6b8f', [['이름', '이름'], ['소개', '소개'], ['사진_url', '사진 링크'], ['공개', '홈피에 보이기'],
    ['정렬', '순서 (작을수록 위)'], ['id', '고유이름 (비워 두면 자동)']]],
  ['소개 페이지 글', '페이지글', '#7a7a7a', [['id', '페이지 (바꾸지 마세요)'], ['제목', '제목'], ['본문', '본문'],
    ['공개', '홈피에 보이기']]],
  ['계좌', '계좌', '#7a7a7a', [['용도', '용도'], ['설명', '설명'], ['은행', '은행'], ['번호', '계좌번호'], ['예금주', '예금주'],
    ['안내', '안내'], ['정렬', '순서 (작을수록 위)'], ['공개', '홈피에 보이기']]],
  ['연락처', '연락', '#7a7a7a', [['항목', '항목 (바꾸지 마세요)'], ['값', '내용']]]
];
var ALIAS = { '고유이름': 'id', '홈피에 보이기': '공개', '순서': '정렬', '취소 이유': '취소사유', '신청 링크': '신청_url',
  '자료 링크': '자료_url', '사진 링크': '사진_url', '유튜브 링크': 'youtube_url', '올린 날': '게시일', '링크': '링크_url',
  '강사': '강사진_id', '책': '도서', '계좌번호': '번호', '내용': '값', '페이지': 'id', '참여 방법': '참여방법' };
var PAGE_KO = { about: '연구소 소개', history: '걸어온 길', people: '함께한 사람들', archive: '지난 프로그램',
  participate: '참여 안내', visit: '오시는 길', lectures: '기획강좌·특강', agit: '아지트솜니움', board: '이사회' };
var MUST = ['제목', '이름', '세미나', '회차', '유튜브 링크'];
var TIPS = {
  '제목': '꼭 채우는 칸입니다.',
  '이름': '꼭 채우는 칸입니다.',
  '상태': '목록에서 고르세요. 비워 두면 날짜를 보고 예고·모집중·진행중·종료가 저절로 정해집니다.',
  '시작일': '칸을 두 번 누르면 달력이 나옵니다. 비워 두면 회차 탭 날짜로 채워집니다.',
  '날짜': '칸을 두 번 누르면 달력이 나옵니다. 북클럽처럼 여러 날이면 2026-11-12;2026-11-19 로 이어 적습니다.',
  '올린 날': '칸을 두 번 누르면 달력이 나옵니다.',
  '강사': '강사진 탭에 있는 이름을 고르세요. 여럿이면 쉼표로 이어 적습니다.',
  '세미나': '세미나 탭의 제목을 목록에서 고르세요.',
  '홈피에 보이기': '체크하면 홈페이지에 보이고, 끄면 숨깁니다. 줄을 지우지 않아도 됩니다.',
  '순서': '작은 숫자가 위에 나옵니다. 비워도 됩니다.',
  '고유이름': '홈페이지 주소에 쓰이는 이름입니다. 비워 두면 저절로 정해집니다. 한번 정해지면 바꾸지 마세요.',
  '페이지': '어느 페이지의 글인지입니다. 바꾸지 마세요.',
  '항목': '바꾸지 마세요. 오른쪽 내용만 고칩니다.',
  '본문': '홈페이지에 보일 글입니다. 칸을 누르면 위쪽 입력줄에서 전체를 볼 수 있습니다.'
};
var ROWS = 200;

function key_(h) { return String(h).replace(/\s*\(.*\)\s*/g, '').trim(); }

function readOld_(sh) {
  var v = sh.getDataRange().getDisplayValues();
  if (!v.length) return [];
  var head = v[0].map(function (h) { var k = key_(h); return ALIAS[k] || k; });
  return v.slice(1).filter(function (r) { return r.join('').replace(/TRUE|FALSE|예|아니오/g, '').trim(); })
    .map(function (r) { var o = {}; head.forEach(function (h, i) { o[h] = r[i]; }); return o; });
}

function normDate_(s) {
  return String(s || '').split(';').map(function (p) {
    var m = p.trim().match(/^(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})/);
    return m ? m[1] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[3]).slice(-2) : p.trim();
  }).filter(String).join(';');
}

function setup() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  ss.setSpreadsheetLocale('ko_KR');
  var old = {};
  TABS.forEach(function (t) {
    var sh = ss.getSheetByName(t[0]) || ss.getSheetByName(t[1]);
    old[t[0]] = sh ? readOld_(sh) : [];
  });
  var fac = {}, sem = {}, ses = {};
  old['강사진'].forEach(function (r) { fac[r.id] = r['이름']; });
  old['세미나'].forEach(function (r) { sem[r.id] = r['제목']; });
  old['회차'].forEach(function (r) { ses[r.id] = r['회차']; });

  var guide = buildGuide_(ss);
  TABS.forEach(function (t, i) {
    var sh = ss.getSheetByName(t[0]) || ss.getSheetByName(t[1]) || ss.insertSheet(t[0]);
    sh.setName(t[0]);
    var lay = t[3];
    var rows = old[t[0]].map(function (r) {
      return lay.map(function (c) {
        var v = r[c[0]] == null ? '' : String(r[c[0]]);
        if (c[0] === '강사진_id') v = v.split(';').filter(String).map(function (x) { return fac[x] || x; }).join(', ');
        if (c[0] === '세미나_id') v = sem[v] || v;
        if (c[0] === '회차_id') v = ses[v] || v;
        if (t[0] === '소개 페이지 글' && c[0] === 'id') v = PAGE_KO[v] || v;
        if (c[0] === '공개') v = (v === 'FALSE' || v === '아니오') ? '아니오' : '예';
        if (['시작일', '종료일', '날짜', '게시일'].indexOf(c[0]) >= 0) v = normDate_(v);
        if (v.charAt(0) === "'") v = "'" + v;  // 맨 앞 작은따옴표가 사라지지 않게
        return v;
      });
    });
    fillTab_(ss, sh, lay.map(function (c) { return c[1]; }), rows);
    sh.setTabColor(t[2]);
    ss.setActiveSheet(sh);
    ss.moveActiveSheet(i + 2);
  });
  ['읽어주세요'].forEach(function (n) { var s = ss.getSheetByName(n); if (s && s.getSheetId() !== guide.getSheetId()) ss.deleteSheet(s); });
  ss.setActiveSheet(guide);
  ss.moveActiveSheet(1);
  SpreadsheetApp.flush();
  Logger.log('다 됐습니다. 「안내」 탭부터 보시면 됩니다.');
}

function fillTab_(ss, sh, head, values) {
  var n = head.length;
  sh.getBandings().forEach(function (b) { b.remove(); });
  sh.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) { p.remove(); });
  sh.clear();
  sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns()).clearDataValidations();
  if (sh.getMaxRows() < ROWS + 1) sh.insertRowsAfter(sh.getMaxRows(), ROWS + 1 - sh.getMaxRows());
  if (sh.getMaxColumns() < n) sh.insertColumnsAfter(sh.getMaxColumns(), n - sh.getMaxColumns());
  if (sh.getMaxColumns() > n) sh.deleteColumns(n + 1, sh.getMaxColumns() - n);
  sh.getRange(2, 1, ROWS, n).setNumberFormat('@').setVerticalAlignment('top')
    .setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP).setFontSize(10);

  var dateCols = [], timeCols = [];
  head.forEach(function (h, c) {
    var k = key_(h), col = sh.getRange(2, c + 1, ROWS, 1), w = 140;
    if (k === '시작일' || k === '종료일' || k === '올린 날' || (k === '날짜' && h.indexOf(';') < 0)) {
      dateCols.push(c); w = 110;
    } else if (k === '시간') {
      timeCols.push(c); w = 80;
    } else if (k === '상태') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInList(['예고', '모집중', '진행중', '종료', '취소'], true).setAllowInvalid(false).build());
      w = 120;
    } else if (k === '강사') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInRange(ss.getRange("'강사진'!A2:A"), true).setAllowInvalid(true).build());
    } else if (k === '세미나') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInRange(ss.getRange("'세미나'!A2:A"), true).setAllowInvalid(false)
        .setHelpText('세미나 탭의 제목 중에서 고르세요.').build());
      w = 200;
    } else if (k === '소개' || k === '본문') { w = 360;
    } else if (k === '부제') { w = 240;
    } else if (k.indexOf('링크') >= 0) { w = 220;
    } else if (k === '제목' || k === '이름') { w = 240;
    } else if (k === '홈피에 보이기') { w = 100;
    } else if (k === '고유이름') { col.setFontColor('#9a9a9a'); w = 150;
    } else if (k === '회차' || k === '순서') { w = 80; }
    sh.setColumnWidth(c + 1, w);
  });
  dateCols.concat(timeCols).forEach(function (c) { sh.getRange(2, c + 1, ROWS, 1).setNumberFormat('General'); });

  var vis = head.map(key_).indexOf('홈피에 보이기');
  if (values.length) sh.getRange(2, 1, values.length, n).setValues(values);
  dateCols.forEach(function (c) {
    sh.getRange(2, c + 1, ROWS, 1).setNumberFormat('yyyy-mm-dd').setHorizontalAlignment('left')
      .setDataValidation(SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(false)
        .setHelpText('날짜를 넣어 주세요. 칸을 두 번 누르면 달력이 나옵니다.').build());
  });
  timeCols.forEach(function (c) { sh.getRange(2, c + 1, ROWS, 1).setNumberFormat('HH:mm').setHorizontalAlignment('left'); });
  if (vis >= 0) {
    var vr = sh.getRange(2, vis + 1, ROWS, 1);
    var cur = [];
    for (var i = 0; i < ROWS; i++) cur.push([i < values.length ? values[i][vis] !== '아니오' : false]);
    vr.setNumberFormat('General').insertCheckboxes().setValues(cur).setHorizontalAlignment('center');
  }

  var hr = sh.getRange(1, 1, 1, n);
  hr.setValues([head]);
  sh.getRange(1, 1, ROWS + 1, n).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, true, false);
  hr.setFontWeight('bold').setFontColor('#ffffff').setBackground('#1f3a5f').setVerticalAlignment('middle').setWrap(true);
  head.forEach(function (h, c) {
    var k = key_(h), cell = sh.getRange(1, c + 1);
    if (MUST.indexOf(k) >= 0 && !(k === '회차' && sh.getName() === '영상')) cell.setBackground('#b5482a');
    var tip = TIPS[k] || (k.indexOf('링크') >= 0 ? 'https:// 로 시작하는 주소 전체를 붙여 넣으세요.' : '');
    if (tip) cell.setNote(tip);
  });
  sh.setRowHeight(1, 42);
  sh.setFrozenRows(1);
  sh.setFrozenColumns(1);
  hr.protect().setDescription('머리글 — 바꾸면 홈페이지가 칸을 못 알아봅니다').setWarningOnly(true);
}

function buildGuide_(ss) {
  var sh = ss.getSheetByName('안내') || ss.insertSheet('안내');
  sh.clear();
  var lines = [
    ['솜니움 홈페이지 관리 시트'],
    ['여기를 고치면 3시간 안에 홈페이지가 저절로 바뀝니다.   ' + SITE],
    [''],
    ['· 새 모임은 해당 탭 맨 아래 빈 줄에 적습니다. 주황색 머리글 칸만 꼭 채우면 됩니다.'],
    ['· 숨기려면 「홈피에 보이기」 체크를 끕니다. 줄은 지우지 않아도 됩니다.'],
    ['· 상태·고유이름은 비워 두면 저절로 정해집니다.'],
    ['· 머리글(맨 윗줄)에 마우스를 올리면 그 칸에 무엇을 쓰는지 나옵니다.'],
    ['· 유튜브 새 영상과 인스타 포스터는 저절로 올라옵니다. 영상 탭에는 따로 걸고 싶은 영상만 적습니다.'],
    [''],
    ['▼ 점검 결과 — 틀린 곳이 있으면 여기에 고칠 것이 나옵니다']
  ];
  sh.getRange(1, 1, lines.length, 1).setValues(lines).setWrap(false).setFontSize(11);
  sh.getRange('A1').setFontSize(18).setFontWeight('bold').setFontColor('#1f3a5f');
  sh.getRange('A2').setFontColor('#b5482a').setFontWeight('bold');
  sh.getRange('A10').setFontWeight('bold').setFontColor('#1f3a5f');
  sh.getRange('A11').setFormula('=IMPORTDATA("' + SITE + 'sheet-check.csv")');
  sh.setColumnWidth(1, 120); sh.setColumnWidth(2, 50); sh.setColumnWidth(3, 260); sh.setColumnWidth(4, 560);
  sh.setTabColor('#1f3a5f');
  sh.setHiddenGridlines(true);
  return sh;
}

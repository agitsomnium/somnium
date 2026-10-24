/**
 * 솜니움 홈페이지 관리 시트 꾸미기 — 한 번만 실행하면 된다(다시 실행하면 씨앗 자료로 처음부터 다시 채운다).
 * 확장 프로그램 → Apps Script 에 붙여 넣고 「setup」 실행.
 * 씨앗 자료: github.com/agitsomnium/somnium 의 data/sheet_seed/easy/*.csv
 */
var RAW = 'https://raw.githubusercontent.com/agitsomnium/somnium/main/data/sheet_seed/easy/';
var SITE = 'https://agitsomnium.github.io/somnium/';
// [시트 탭 이름, 예전 탭 이름, 씨앗 파일, 탭 색]
var TABS = [
  ['세미나', '세미나', 'seminars', '#b5482a'],
  ['회차', '회차', 'sessions', '#b5482a'],
  ['북클럽', '북클럽', 'bookclubs', '#b5482a'],
  ['공지', '공지', 'notices', '#3d6b8f'],
  ['영상', '영상', 'videos', '#3d6b8f'],
  ['강사진', '강사진', 'faculty', '#3d6b8f'],
  ['소개 페이지 글', '페이지글', 'pages', '#7a7a7a'],
  ['계좌', '계좌', 'accounts', '#7a7a7a'],
  ['연락처', '연락', 'contacts', '#7a7a7a']
];
var MUST = ['제목', '이름', '세미나', '회차', '유튜브 링크'];
var TIPS = {
  '제목': '꼭 채우는 칸입니다.',
  '상태': '목록에서 고르세요. 비워 두면 날짜를 보고 예고·모집중·진행중·종료가 저절로 정해집니다.',
  '시작일': '칸을 두 번 누르면 달력이 나옵니다. 비워 두면 회차 탭 날짜로 채워집니다.',
  '날짜': '칸을 두 번 누르면 달력이 나옵니다.',
  '강사': '강사진 탭에 있는 이름을 고르세요. 여럿이면 쉼표로 이어 적습니다.',
  '세미나': '세미나 탭의 제목을 목록에서 고르세요.',
  '신청 링크': '구글폼 주소를 그대로 붙여 넣으세요(https:// 로 시작).',
  '홈피에 보이기': '체크하면 홈페이지에 보이고, 끄면 숨깁니다. 줄을 지우지 않아도 됩니다.',
  '순서': '작은 숫자가 위에 나옵니다. 비워도 됩니다.',
  '고유이름': '홈페이지 주소에 쓰이는 이름입니다. 비워 두면 저절로 정해지고, 한번 정해지면 바꾸지 마세요.',
  '페이지': '어느 페이지의 글인지입니다. 바꾸지 마세요.',
  '항목': '바꾸지 마세요. 오른쪽 내용만 고칩니다.',
  '본문': '홈페이지에 보일 글입니다. 칸을 누르면 위쪽 입력줄에서 전체를 볼 수 있습니다.'
};
var ROWS = 200;

function key_(h) { return String(h).replace(/\s*\(.*\)\s*/g, '').trim(); }

function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetLocale('ko_KR');
  var guide = buildGuide_(ss);
  TABS.forEach(function (t, i) {
    var sh = ss.getSheetByName(t[0]) || ss.getSheetByName(t[1]) || ss.insertSheet(t[0]);
    sh.setName(t[0]);
    fillTab_(ss, sh, t[2]);
    sh.setTabColor(t[3]);
    ss.setActiveSheet(sh);
    ss.moveActiveSheet(i + 2);
  });
  ss.setActiveSheet(guide);
  ss.moveActiveSheet(1);
  SpreadsheetApp.flush();
  SpreadsheetApp.getUi().alert('다 됐습니다. 「안내」 탭부터 보시면 됩니다.');
}

function fillTab_(ss, sh, file) {
  var text = UrlFetchApp.fetch(RAW + file + '.csv').getContentText('UTF-8').replace(/^﻿/, '');
  var rows = Utilities.parseCsv(text);
  var head = rows[0], body = rows.slice(1), n = head.length;
  sh.clear();
  sh.getDataRange().clearDataValidations();
  sh.getProtections(SpreadsheetApp.ProtectionType.RANGE).forEach(function (p) { p.remove(); });
  if (sh.getMaxRows() < ROWS + 1) sh.insertRowsAfter(sh.getMaxRows(), ROWS + 1 - sh.getMaxRows());
  if (sh.getMaxColumns() < n) sh.insertColumnsAfter(sh.getMaxColumns(), n - sh.getMaxColumns());
  if (sh.getMaxColumns() > n) sh.deleteColumns(n + 1, sh.getMaxColumns() - n);
  var all = sh.getRange(2, 1, ROWS, n);
  all.setNumberFormat('@').setVerticalAlignment('top').setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);

  head.forEach(function (h, c) {
    var k = key_(h), col = sh.getRange(2, c + 1, ROWS, 1), w = 140;
    if (k === '시작일' || k === '종료일' || k === '올린 날' || (k === '날짜' && h.indexOf(';') < 0)) {
      col.setNumberFormat('yyyy-mm-dd');
      col.setDataValidation(SpreadsheetApp.newDataValidation().requireDate().setAllowInvalid(false)
        .setHelpText('날짜를 넣어 주세요. 칸을 두 번 누르면 달력이 나옵니다.').build());
      w = 110;
    } else if (k === '시간') {
      col.setNumberFormat('HH:mm'); w = 80;
    } else if (k === '상태') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInList(['예고', '모집중', '진행중', '종료', '취소'], true).setAllowInvalid(false).build());
      w = 110;
    } else if (k === '강사') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInRange(ss.getRange("'강사진'!A2:A"), true).setAllowInvalid(true).build());
    } else if (k === '세미나') {
      col.setDataValidation(SpreadsheetApp.newDataValidation()
        .requireValueInRange(ss.getRange("'세미나'!A2:A"), true).setAllowInvalid(false)
        .setHelpText('세미나 탭의 제목 중에서 고르세요.').build());
      w = 200;
    } else if (k === '소개' || k === '본문' || k === '부제') {
      w = k === '부제' ? 240 : 360;
    } else if (k.indexOf('링크') >= 0) {
      w = 220;
    } else if (k === '제목' || k === '이름') {
      w = 240;
    } else if (k === '홈피에 보이기') {
      w = 100;
    } else if (k === '고유이름') {
      col.setFontColor('#9a9a9a'); w = 150;
    } else if (k === '회차' || k === '순서') {
      w = 80;
    }
    sh.setColumnWidth(c + 1, w);
  });

  // 값 넣기 — 보이기 칸은 체크박스로
  var vis = head.map(key_).indexOf('홈피에 보이기');
  var values = body.map(function (r) {
    var row = r.slice(0, n);
    while (row.length < n) row.push('');
    return row;
  });
  if (values.length) sh.getRange(2, 1, values.length, n).setValues(values);
  if (vis >= 0) {
    var vr = sh.getRange(2, vis + 1, ROWS, 1);
    var cur = vr.getValues().map(function (x, i) {
      return [i < values.length ? String(x[0]) !== '아니오' : false];
    });
    vr.clearDataValidations().setNumberFormat('General').insertCheckboxes().setValues(cur).setHorizontalAlignment('center');
  }

  // 머리글
  var hr = sh.getRange(1, 1, 1, n);
  hr.setValues([head]).setFontWeight('bold').setFontColor('#ffffff').setBackground('#1f3a5f')
    .setVerticalAlignment('middle').setWrap(true);
  head.forEach(function (h, c) {
    var k = key_(h);
    if (MUST.indexOf(k) >= 0) sh.getRange(1, c + 1).setBackground('#b5482a');
    var tip = TIPS[k] || (k.indexOf('링크') >= 0 ? 'https:// 로 시작하는 주소 전체를 붙여 넣으세요.' : '');
    if (tip) sh.getRange(1, c + 1).setNote(tip);
  });
  sh.setRowHeight(1, 42);
  sh.setFrozenRows(1);
  sh.setFrozenColumns(1);
  sh.getRange(2, 1, ROWS, n).setFontSize(10);
  var p = hr.protect().setDescription('머리글 — 바꾸면 홈페이지가 칸을 못 알아봅니다');
  p.setWarningOnly(true);
  sh.getBandings().forEach(function (b) { b.remove(); });
  sh.getRange(1, 1, ROWS + 1, n).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, true, false);
  sh.getRange(1, 1, 1, n).setBackground('#1f3a5f');
  head.forEach(function (h, c) { if (MUST.indexOf(key_(h)) >= 0) sh.getRange(1, c + 1).setBackground('#b5482a'); });
}

function buildGuide_(ss) {
  var sh = ss.getSheetByName('안내') || ss.getSheetByName('읽어주세요') || ss.insertSheet('안내');
  sh.setName('안내');
  sh.clear();
  sh.getBandings().forEach(function (b) { b.remove(); });
  var lines = [
    ['솜니움 홈페이지 관리 시트'],
    ['여기를 고치면 3시간 안에 홈페이지가 저절로 바뀝니다.  홈페이지 → ' + SITE],
    [''],
    ['새 모임은  해당 탭 맨 아래 빈 줄에 적습니다.  주황색 머리글 칸만 꼭 채우면 됩니다.'],
    ['숨기려면  「홈피에 보이기」 체크를 끕니다.  줄은 지우지 않아도 됩니다.'],
    ['상태·고유이름은  비워 두면 저절로 정해집니다.'],
    ['머리글(맨 윗줄)에 마우스를 올리면  그 칸에 무엇을 쓰는지 나옵니다.'],
    ['유튜브 새 영상과 인스타 포스터는  저절로 홈페이지에 올라옵니다.  영상 탭에는 따로 걸고 싶은 영상만 적습니다.'],
    [''],
    ['▼ 점검 결과  (틀린 곳이 있으면 여기에 고칠 것이 나옵니다)']
  ];
  sh.getRange(1, 1, lines.length, 1).setValues(lines);
  sh.getRange('A1').setFontSize(16).setFontWeight('bold').setFontColor('#1f3a5f');
  sh.getRange('A2').setFontColor('#b5482a').setFontWeight('bold');
  sh.getRange('A10').setFontWeight('bold').setFontColor('#1f3a5f');
  sh.getRange('A11').setFormula('=IMPORTDATA("' + SITE + 'sheet-check.csv")');
  sh.setColumnWidth(1, 160); sh.setColumnWidth(2, 60); sh.setColumnWidth(3, 260); sh.setColumnWidth(4, 520);
  sh.getRange('A1:A9').setWrap(false);
  sh.setTabColor('#1f3a5f');
  sh.setHiddenGridlines(true);
  return sh;
}

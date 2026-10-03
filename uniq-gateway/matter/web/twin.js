/* ==========================================================================
   UNIQ Digital Twin — building / floor / room operations view
   - Real interactive 3D (Three.js, served locally from /vendor/three.min.js)
   - Live data from the Hub (rawDevices + roomsData) or simulated Mock data
   - Bilingual (EN / AR) and Light / Dark aware
   Depends on globals defined by index.html: I18N, t(), currentLang, rawDevices,
   roomsData, getDeviceGroupKey(), getDeviceDisplayTitle(), toggleChannelState(),
   saveRoomsToBackend().
   ========================================================================== */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); };
  var lerp = function (a, b, k) { return a + (b - a) * k; };
  var lang = function () { return (typeof currentLang !== 'undefined' && currentLang) || 'en'; };
  var nm = function (o) { return (o && typeof o === 'object') ? (o[lang()] || o.en || '') : (o == null ? '' : String(o)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]; }); };
  var L = function (en, ar) { return { en: en, ar: ar }; };
  var LS_MODE = 'uniq_twin_mode';

  // ------------------------------------------------------------------------
  // i18n
  // ------------------------------------------------------------------------
  var STR = {
    en: {
      tabTwin: 'Digital Twin', twBuilding: 'Building', twPlan: 'Plan', tw3d: '3D', twLive: 'Live', twMock: 'Mock',
      twManage: 'Building setup', twMockBadge: 'MOCK DATA', twTotalCons: 'Total consumption', twSolar: 'Solar production',
      twGrid: 'Grid import', twBattery: 'Battery charge', twActiveLoads: 'Active loads', twAvgTemp: 'Avg temperature',
      twRooms: 'Rooms', twLighting: 'Lighting', twAC: 'AC / HVAC', twSockets: 'Sockets', twSummary: 'Summary',
      twEnergy: 'Energy consumption', twWaterUsage: 'Water usage', twHvacRuntime: 'HVAC runtime', twLights: 'Lights',
      twAcs: 'AC units', twAlarms: 'Alarms', twNoData: 'No data source connected', twEmptyTitle: 'No live data yet',
      twEmptyDesc: 'No devices were found on this Hub. Pair devices first, or preview the experience with simulated data.',
      twUseMock: 'Preview with mock data', twUnassigned: 'Unassigned devices', twDevices: 'Devices', twAllOn: 'All ON',
      twAllOff: 'All OFF', twFloors: 'Floors', twAddFloor: 'Add floor', twFloorName: 'Floor name',
      twRoomAssign: 'Assign rooms to floors', twSave: 'Save', twClose: 'Close', twSession: 'Live trend',
      twTank: 'Roof tanks', twPump: 'Main pump', twPressure: 'Pressure', twQuality: 'Water quality',
      twBack: 'Back', twSetupHint: 'Define the floors of the building and assign each room to a floor. Devices are assigned to rooms from the Rooms tab.',
      twLoad: 'Load', twGen: 'Generation', twTemp: 'Temperature', twHum: 'Humidity', twNoDevices: 'No devices assigned',
      twLevel: 'Level', twNoRooms: 'No rooms on this floor', twFloorDef: 'Floor', twToday: 'Today', twKwh: 'kWh',
      twSensors: 'Sensors', twOnCount: 'ON', twOffline: 'Offline', twActive: 'Active', twAlarmNone: 'No active alarms',
      twGroundTank: 'Underground tank', twHint: 'Drag to rotate · scroll to zoom · click a floor or room', twFloorCount: 'floors'
    },
    ar: {
      tabTwin: 'التوأم الرقمي', twBuilding: 'المبنى', twPlan: 'مخطط', tw3d: 'ثلاثي الأبعاد', twLive: 'مباشر', twMock: 'تجريبي',
      twManage: 'إعداد المبنى', twMockBadge: 'بيانات تجريبية', twTotalCons: 'إجمالي الاستهلاك', twSolar: 'إنتاج الطاقة الشمسية',
      twGrid: 'الاستيراد من الشبكة', twBattery: 'شحن البطارية', twActiveLoads: 'الأحمال العاملة', twAvgTemp: 'متوسط الحرارة',
      twRooms: 'الغرف', twLighting: 'الإنارة', twAC: 'التكييف', twSockets: 'المقابس', twSummary: 'ملخص',
      twEnergy: 'استهلاك الطاقة', twWaterUsage: 'استهلاك المياه', twHvacRuntime: 'تشغيل التكييف', twLights: 'الإنارة',
      twAcs: 'المكيفات', twAlarms: 'التنبيهات', twNoData: 'لا يوجد مصدر بيانات متصل', twEmptyTitle: 'لا توجد بيانات مباشرة بعد',
      twEmptyDesc: 'لم يتم العثور على أجهزة في هذا الموزع. قم بإقران الأجهزة أولاً، أو جرّب العرض ببيانات تجريبية.',
      twUseMock: 'معاينة ببيانات تجريبية', twUnassigned: 'أجهزة غير موزعة', twDevices: 'الأجهزة', twAllOn: 'تشغيل الكل',
      twAllOff: 'إطفاء الكل', twFloors: 'الطوابق', twAddFloor: 'إضافة طابق', twFloorName: 'اسم الطابق',
      twRoomAssign: 'توزيع الغرف على الطوابق', twSave: 'حفظ', twClose: 'إغلاق', twSession: 'المنحنى المباشر',
      twTank: 'خزانات السطح', twPump: 'المضخة الرئيسية', twPressure: 'الضغط', twQuality: 'جودة المياه',
      twBack: 'رجوع', twSetupHint: 'حدد طوابق المبنى ووزّع كل غرفة على طابق. توزيع الأجهزة على الغرف يتم من تبويب الغرف.',
      twLoad: 'الحمل', twGen: 'الإنتاج', twTemp: 'الحرارة', twHum: 'الرطوبة', twNoDevices: 'لا توجد أجهزة موزعة',
      twLevel: 'المستوى', twNoRooms: 'لا توجد غرف في هذا الطابق', twFloorDef: 'الطابق', twToday: 'اليوم', twKwh: 'ك.و.س',
      twSensors: 'الحساسات', twOnCount: 'يعمل', twOffline: 'غير متصل', twActive: 'نشط', twAlarmNone: 'لا توجد تنبيهات',
      twGroundTank: 'الخزان الأرضي', twHint: 'اسحب للتدوير · مرر للتقريب · انقر على طابق أو غرفة', twFloorCount: 'طوابق'
    }
  };
  try { Object.keys(STR).forEach(function (l) { Object.assign(I18N[l], STR[l]); }); } catch (e) { console.warn('Twin i18n', e); }
  var T = function (k) { try { return t(k); } catch (e) { return STR.en[k] || k; } };

  // ------------------------------------------------------------------------
  // Icons (technical line icons)
  // ------------------------------------------------------------------------
  var ICON = {
    bolt: '<path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z"/>',
    snow: '<path d="M12 2v20M4.9 7l14.2 10M4.9 17 19.1 7M9.5 3.5 12 6l2.5-2.5M9.5 20.5 12 18l2.5 2.5"/>',
    plug: '<path d="M9 2v5M15 2v5M7 7h10v4a5 5 0 0 1-10 0V7zM12 16v6"/>',
    drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    solar: '<path d="M3 15l2.5-9h13L21 15H3zM12 6v9M7.5 6 6 15M16.5 6 18 15M3 15l-1 5M21 15l1 5M2 20h20"/>',
    grid: '<path d="M12 2 8 22M12 2l4 20M7 9h10M6 14h12M9 5.5h6"/>',
    battery: '<rect x="3" y="7" width="16" height="10" rx="2"/><path d="M21 11v2M7 10v4M11 10v4"/>',
    building: '<path d="M5 21V4l7-2 7 2v17M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2M3 21h18"/>',
    left: '<path d="M15 5l-7 7 7 7"/>',
    cube: '<path d="M12 2 3 7v10l9 5 9-5V7l-9-5zM3 7l9 5 9-5M12 12v10"/>',
    map: '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6zM9 3v15M15 6v15"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.3-.9-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-.9a7 7 0 0 0 2 1.2l.4 2.6h4l.4-2.6a7 7 0 0 0 2-1.2l2.3.9 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z"/>',
    alert: '<path d="M12 3 2 21h20L12 3zM12 10v5M12 18h.01"/>',
    temp: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/>',
    sensor: '<path d="M12 3a9 9 0 0 0-9 9M12 7a5 5 0 0 0-5 5M12 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2zM12 15v6"/>',
    pump: '<circle cx="10" cy="12" r="5"/><path d="M15 12h7M10 7V3M10 12l3 2M2 12h3"/>',
    gauge: '<path d="M4 17a8 8 0 1 1 16 0M12 17l4-6"/>',
    flask: '<path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    stairs: '<path d="M4 20h4v-4h4v-4h4V8h4M4 20V4"/>',
    bed: '<path d="M3 18V6M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5M7 11a1.5 1.5 0 1 0 0-.01"/>',
    sofa: '<path d="M5 11V8a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3M3 13a2 2 0 0 1 4 0v2h10v-2a2 2 0 0 1 4 0v5H3v-5zM6 18v2M18 18v2"/>',
    cook: '<path d="M4 11h16v3a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-3zM8 7c0-1 1-1 1-2M12 7c0-1 1-1 1-2M16 7c0-1 1-1 1-2"/>',
    bath: '<path d="M3 12h18v2a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5v-2zM6 12V6a2 2 0 0 1 4 0M7 19l-1 2M17 19l1 2"/>',
    door: '<path d="M6 21V4h12v17M4 21h16M15 12h.01"/>',
    tank: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'
  };
  function ic(name, cls) {
    return '<svg class="tw-ic ' + (cls || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (ICON[name] || '') + '</svg>';
  }
  var CAT_ICON = { light: 'bulb', hvac: 'snow', socket: 'plug', sensor: 'sensor', other: 'chip' };
  var CAT_CLS = { light: 'c-light', hvac: 'c-hvac', socket: 'c-socket', sensor: 'c-energy', other: 'c-muted' };

  // ------------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------------
  var S = {
    inited: false, visible: false,
    mode: localStorage.getItem(LS_MODE) === 'mock' ? 'mock' : 'live',
    view: 'overview', floorIdx: 0, roomId: null, plan: false,
    building: { floors: [] },
    liveBuf: [], sessionKwh: 0, lastT: 0,
    hover: null, tickTimer: null, userMoved: false
  };
  var M = null;       // current normalized model
  var MK = null;      // persistent mock store
  var G = {};         // WebGL state
  var CO = [];        // callout items

  // ------------------------------------------------------------------------
  // Model helpers
  // ------------------------------------------------------------------------
  function catOf(c) {
    if (c === 'lighting' || c === 'switch') return 'light';
    if (c === 'socket') return 'socket';
    if (c === 'climate') return 'hvac';
    if (c === 'sensor') return 'sensor';
    return 'other';
  }
  function fmtPow(kw) {
    kw = +kw || 0;
    if (kw < 1) return Math.round(kw * 1000) + ' W';
    return kw.toFixed(kw >= 100 ? 0 : 1) + ' kW';
  }
  function fmtNum(v, d) { return (+v).toLocaleString(lang() === 'ar' ? 'en-US' : 'en-US', { maximumFractionDigits: d == null ? 0 : d, minimumFractionDigits: d == null ? 0 : d }); }
  function defaultFloorName(i) { return T('twFloorDef') + ' ' + (i + 1); }

  function finalizeRoom(r) {
    r.kwLight = r.kwHvac = r.kwSocket = r.kwOther = 0;
    r.onL = r.totL = r.onH = r.totH = r.onS = r.totS = 0;
    var ts = [], hs = [];
    r.devices.forEach(function (d) {
      d.kw = d.channels.reduce(function (s, c) { return s + (c.kw || 0); }, 0);
      var ctl = d.channels.filter(function (c) { return c.hasOnOff; });
      var on = ctl.filter(function (c) { return c.state === 'ON'; }).length;
      if (d.cat === 'light') { r.kwLight += d.kw; r.onL += on; r.totL += ctl.length; }
      else if (d.cat === 'hvac') { r.kwHvac += d.kw; r.onH += on; r.totH += ctl.length; }
      else if (d.cat === 'socket') { r.kwSocket += d.kw; r.onS += on; r.totS += ctl.length; }
      else r.kwOther += d.kw;
      if (d.temp != null) ts.push(+d.temp);
      if (d.hum != null) hs.push(+d.hum);
    });
    r.kw = r.kwLight + r.kwHvac + r.kwSocket + r.kwOther;
    r.temp = ts.length ? ts.reduce(function (a, b) { return a + b; }, 0) / ts.length : null;
    r.hum = hs.length ? hs.reduce(function (a, b) { return a + b; }, 0) / hs.length : null;
    var st = 'ok';
    if (r.alarm && r.alarm.level) st = r.alarm.level;
    if (r.temp != null) { if (r.temp >= 38) st = 'crit'; else if (r.temp >= 32 && st === 'ok') st = 'warn'; }
    if (!r.devices.length && !r.equip) st = 'off';
    r.status = st;
    return r;
  }

  function aggregate(rooms) {
    var a = { kw: 0, kwLight: 0, kwHvac: 0, kwSocket: 0, onL: 0, totL: 0, onH: 0, totH: 0, onS: 0, totS: 0, alarms: 0, ts: 0, tn: 0, devices: 0, rooms: rooms.length };
    rooms.forEach(function (r) {
      a.kw += r.kw; a.kwLight += r.kwLight; a.kwHvac += r.kwHvac; a.kwSocket += r.kwSocket;
      a.onL += r.onL; a.totL += r.totL; a.onH += r.onH; a.totH += r.totH; a.onS += r.onS; a.totS += r.totS;
      if (r.status === 'warn' || r.status === 'crit') a.alarms++;
      if (r.temp != null) { a.ts += r.temp; a.tn++; }
      a.devices += r.devices.length;
    });
    a.temp = a.tn ? a.ts / a.tn : null;
    return a;
  }

  function floorsDef() {
    var f = (S.building && S.building.floors) || [];
    return f.length ? f : [{ id: 'f1', name: null }];
  }

  function devFromEps(eps) {
    var p = eps[0];
    var channels = eps.map(function (e) {
      return {
        id: e.node_id + '_' + e.endpoint_id,
        name: e.custom_name || e.display_name || e.device_name || ('CH ' + e.endpoint_id),
        state: e.state, hasOnOff: !!e.has_onoff,
        nodeId: e.node_id, endpointId: e.endpoint_id, deviceName: e.device_name,
        kw: (parseFloat(e.power) || 0) / 1000
      };
    });
    var pick = function (k) { for (var i = 0; i < eps.length; i++) { if (eps[i][k] != null) return +eps[i][k]; } return null; };
    var title = '';
    try { title = getDeviceDisplayTitle({ primary: p }); } catch (e) { title = p.custom_name || p.display_name || p.device_name; }
    return {
      id: eps.map(function (e) { return e.node_id + '_' + e.endpoint_id; }).join(','),
      name: title, cat: catOf(p.category), channels: channels,
      temp: pick('temperature'), hum: pick('humidity'), battery: pick('battery')
    };
  }
  function devicesFromEps(eps) {
    var groups = {}; var order = [];
    eps.forEach(function (e) {
      var k; try { k = getDeviceGroupKey(e); } catch (x) { k = 'n' + e.node_id; }
      if (!groups[k]) { groups[k] = []; order.push(k); }
      groups[k].push(e);
    });
    return order.map(function (k) { return devFromEps(groups[k]); });
  }

  function buildLiveModel() {
    var fl = floorsDef();
    var floors = fl.map(function (f, i) {
      return { id: f.id, name: f.name || defaultFloorName(i), level: i, kind: 'floor', rooms: [] };
    });
    var assigned = {};
    (roomsData || []).forEach(function (r) {
      var keys = r.devices || [];
      keys.forEach(function (k) { assigned[k] = true; });
      var fid = floors.some(function (f) { return f.id === r.floor; }) ? r.floor : floors[0].id;
      var eps = rawDevices.filter(function (d) { return keys.indexOf(d.node_id + '_' + d.endpoint_id) >= 0; });
      var room = { id: r.id, name: r.name, icon: r.icon, floorId: fid, devices: devicesFromEps(eps), equip: null, alarm: null };
      floors.filter(function (f) { return f.id === fid; })[0].rooms.push(finalizeRoom(room));
    });
    var rest = rawDevices.filter(function (d) { return !assigned[d.node_id + '_' + d.endpoint_id] && d.category !== 'bridge'; });
    if (rest.length) {
      floors[0].rooms.push(finalizeRoom({ id: '__unassigned', name: T('twUnassigned'), icon: 'chip', floorId: floors[0].id, devices: devicesFromEps(rest), equip: null, alarm: null, unassigned: true }));
    }
    floors.forEach(function (f) { f.agg = aggregate(f.rooms); });
    var all = []; floors.forEach(function (f) { all = all.concat(f.rooms); });
    var agg = aggregate(all);
    // rolling buffers for the live trend
    var now = Date.now();
    if (now - S.lastT > 2500) {
      if (S.lastT) S.sessionKwh += agg.kw * ((now - S.lastT) / 3600000);
      S.lastT = now;
      S.liveBuf.push(agg.kw); if (S.liveBuf.length > 24) S.liveBuf.shift();
    }
    return {
      mock: false, floors: floors, agg: agg,
      site: { cons: agg.kw, water: null, solar: null, grid: null, battery: null },
      series: { cons: S.liveBuf.slice(), energy: S.liveBuf.slice(), water: null, hvac: null },
      deviceCount: rawDevices.length
    };
  }

  // ---------------- Mock data ----------------
  function mulberry32(a) {
    return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function buildMock() {
    var rnd = mulberry32(2026);
    var uid = 0;
    var ch = function (name, nom, on) { return { id: 'mc' + (++uid), name: name, hasOnOff: true, state: on ? 'ON' : 'OFF', nom: nom, kw: on ? nom : 0 }; };
    var fnames = [L('Ground Floor', 'الطابق الأرضي'), L('1st Floor', 'الطابق الأول'), L('2nd Floor', 'الطابق الثاني'), L('3rd Floor', 'الطابق الثالث'), L('4th Floor', 'الطابق الرابع'), L('5th Floor', 'الطابق الخامس'), L('6th Floor', 'الطابق السادس')];
    var tpl = [
      { n: L('Living Room', 'صالة المعيشة'), l: 3, a: 1, s: 3, gang: true, ic: 'sofa' },
      { n: L('Kitchen', 'المطبخ'), l: 3, a: 1, s: 4, ic: 'cook' },
      { n: L('Master Bedroom', 'غرفة النوم الرئيسية'), l: 3, a: 1, s: 3, ic: 'bed' },
      { n: L('Bedroom 1', 'غرفة نوم 1'), l: 2, a: 1, s: 2, ic: 'bed' },
      { n: L('Bedroom 2', 'غرفة نوم 2'), l: 2, a: 1, s: 2, ic: 'bed' },
      { n: L('Bathroom', 'الحمام'), l: 1, a: 0, s: 1, ic: 'bath' },
      { n: L('Corridor', 'الممر'), l: 2, a: 0, s: 0, ic: 'door' },
      { n: L('Staircase / Lift', 'الدرج / المصعد'), l: 1, a: 0, s: 1, ic: 'stairs' }
    ];
    var floors = fnames.map(function (fn, fi) {
      return {
        id: 'mf' + fi, name: fn, level: fi, kind: 'floor',
        rooms: tpl.map(function (tp, ri) {
          var devs = [], k;
          for (k = 0; k < tp.l; k++) devs.push({ id: 'md' + fi + '_' + ri + '_l' + k, name: L('Ceiling light ' + (k + 1), 'إنارة سقف ' + (k + 1)), cat: 'light', channels: [ch(L('Light', 'إنارة'), 0.06 + rnd() * 0.1, rnd() < 0.55)] });
          if (tp.gang) devs.push({ id: 'md' + fi + '_' + ri + '_g', name: L('3-gang wall switch', 'مفتاح حائط 3 قنوات'), cat: 'light', channels: [ch(L('Gang 1', 'قناة 1'), 0.1, rnd() < 0.6), ch(L('Gang 2', 'قناة 2'), 0.1, rnd() < 0.5), ch(L('Gang 3', 'قناة 3'), 0.1, rnd() < 0.4)] });
          for (k = 0; k < tp.a; k++) devs.push({ id: 'md' + fi + '_' + ri + '_a' + k, name: L('AC unit', 'مكيف'), cat: 'hvac', channels: [ch(L('Power', 'تشغيل'), 1.2 + rnd() * 1.6, rnd() < 0.62)] });
          for (k = 0; k < tp.s; k++) devs.push({ id: 'md' + fi + '_' + ri + '_s' + k, name: L('Smart socket ' + (k + 1), 'مقبس ذكي ' + (k + 1)), cat: 'socket', channels: [ch(L('Power', 'تشغيل'), 0.05 + rnd() * 0.35, rnd() < 0.5)] });
          devs.push({ id: 'md' + fi + '_' + ri + '_t', name: L('Temp / humidity sensor', 'حساس حرارة ورطوبة'), cat: 'sensor', channels: [], temp: 22 + rnd() * 4.5, hum: 40 + rnd() * 18 });
          var room = { id: 'mr' + fi + '_' + ri, name: tp.n, icon: tp.ic, floorId: 'mf' + fi, devices: devs, equip: null, alarm: null };
          if (fi === 2 && ri === 1) { devs[devs.length - 1].temp = 33.4; room.alarm = { level: 'warn', msg: L('High temperature', 'درجة حرارة مرتفعة') }; }
          if (fi === 1 && ri === 5) room.alarm = { level: 'crit', msg: L('Water leak detected', 'تم رصد تسرب مياه') };
          return room;
        })
      };
    });
    floors.push({
      id: 'mfroof', name: L('Roof', 'السطح'), level: 7, kind: 'roof',
      rooms: [
        { id: 'mr_solar', name: L('Solar Array', 'ألواح الطاقة الشمسية'), icon: 'solar', floorId: 'mfroof', equip: 'solar', devices: [], alarm: null, gen: 28.6 },
        { id: 'mr_tank1', name: L('Water Tank 1', 'خزان المياه 1'), icon: 'tank', floorId: 'mfroof', equip: 'tank', devices: [], alarm: null, level: 0.92, cap: 10000 },
        { id: 'mr_tank2', name: L('Water Tank 2', 'خزان المياه 2'), icon: 'tank', floorId: 'mfroof', equip: 'tank', devices: [], alarm: null, level: 0.88, cap: 10000 },
        { id: 'mr_plant', name: L('HVAC Plant', 'محطة التكييف'), icon: 'snow', floorId: 'mfroof', equip: 'plant', alarm: null, devices: [{ id: 'md_plant', name: L('Chiller plant', 'مبرد مركزي'), cat: 'hvac', channels: [ch(L('Power', 'تشغيل'), 8.2, true)] }] }
      ]
    });
    var hr = function (arr) { return arr.map(function (v) { return v; }); };
    MK = {
      floors: floors, baseKw: 14.2, t: 0,
      site: { solar: 28.6, battSoc: 78, battKw: 12.5, water: { lpm: 245, todayM3: 5.8, pumpKw: 2.4, pumpOn: true, pressure: 3.2, tds: 220, ph: 7.4, ground: { cap: 50000, level: 0.96 } } },
      series: {
        energy: hr([38, 34, 32, 31, 33, 45, 70, 95, 110, 102, 98, 105, 115, 120, 118, 112, 118, 135, 150, 142, 120, 92, 66, 48]),
        solar: hr([0, 0, 0, 0, 0, 2, 8, 16, 24, 30, 34, 36, 35, 31, 24, 15, 6, 1, 0, 0, 0, 0, 0, 0]),
        grid: hr([38, 34, 32, 31, 33, 43, 62, 79, 86, 72, 64, 69, 80, 89, 94, 97, 112, 134, 150, 142, 120, 92, 66, 48]),
        batt: hr([60, 58, 57, 56, 55, 56, 58, 62, 68, 74, 80, 84, 86, 84, 80, 76, 72, 68, 62, 58, 55, 54, 55, 58]),
        water: hr([2, 1, 1, 1, 2, 6, 14, 18, 15, 11, 9, 10, 12, 11, 9, 9, 11, 16, 20, 17, 12, 8, 5, 3]),
        hvac: hr([22, 20, 19, 19, 20, 24, 32, 40, 46, 50, 52, 55, 58, 58, 57, 56, 55, 54, 52, 48, 42, 36, 30, 25])
      }
    };
  }
  function mockTick() {
    if (!MK) return;
    var r = Math.random;
    var hour = new Date().getHours() + new Date().getMinutes() / 60;
    MK.floors.forEach(function (f) {
      f.rooms.forEach(function (rm) {
        rm.devices.forEach(function (d) {
          if (d.cat === 'sensor') {
            d.temp = clamp(d.temp + (r() - 0.5) * 0.18, 19, 34.5);
            d.hum = clamp(d.hum + (r() - 0.5) * 0.6, 30, 75);
          } else {
            d.channels.forEach(function (c) {
              if (c.state !== 'ON') { c.kw = 0; return; }
              c.kw = (d.cat === 'light') ? c.nom : clamp(c.nom * (0.88 + r() * 0.24), c.nom * 0.7, c.nom * 1.25);
            });
          }
        });
      });
    });
    var s = MK.site;
    s.solar = Math.max(0, Math.sin(Math.PI * (hour - 6) / 12)) * 34 * (0.92 + r() * 0.08);
    if (!(hour > 6 && hour < 18)) s.solar = 0;
    s.water.lpm = clamp(s.water.lpm + (r() - 0.5) * 12, 120, 340);
    s.water.ground.level = clamp(s.water.ground.level + (r() - 0.5) * 0.003, 0.5, 0.99);
    MK.floors[MK.floors.length - 1].rooms.forEach(function (rm) { if (rm.equip === 'tank') rm.level = clamp(rm.level + (r() - 0.5) * 0.004, 0.4, 0.99); });
  }
  function buildMockModel() {
    if (!MK) { buildMock(); mockTick(); }
    var floors = MK.floors;
    var all = [];
    floors.forEach(function (f) {
      f.rooms.forEach(function (rm) { finalizeRoom(rm); });
      f.agg = aggregate(f.rooms);
      all = all.concat(f.rooms);
    });
    var agg = aggregate(all);
    var cons = agg.kw + MK.baseKw;
    var s = MK.site;
    var grid = Math.max(0, cons - s.solar + s.battKw * 0.4);
    var tanks = floors[floors.length - 1].rooms.filter(function (rm) { return rm.equip === 'tank'; });
    var solarRoom = floors[floors.length - 1].rooms.filter(function (rm) { return rm.equip === 'solar'; })[0];
    if (solarRoom) solarRoom.gen = s.solar;
    return {
      mock: true, floors: floors, agg: agg, baseKw: MK.baseKw,
      site: {
        cons: cons, solar: s.solar, grid: grid, battery: { kw: s.battKw, soc: s.battSoc },
        water: { lpm: s.water.lpm, todayM3: s.water.todayM3, pumpKw: s.water.pumpKw, pumpOn: s.water.pumpOn, pressure: s.water.pressure, tds: s.water.tds, ph: s.water.ph, tanks: tanks, ground: s.water.ground }
      },
      series: { cons: MK.series.energy, energy: MK.series.energy, solar: MK.series.solar, grid: MK.series.grid, batt: MK.series.batt, water: MK.series.water, hvac: MK.series.hvac },
      deviceCount: 1
    };
  }

  function structSig(m) {
    return (m.mock ? 'M' : 'L') + '|' + m.floors.map(function (f) {
      return f.id + ':' + f.kind + ':' + f.rooms.map(function (r) { return r.id + '/' + r.equip + '/' + r.devices.length; }).join(',');
    }).join(';');
  }

  // ------------------------------------------------------------------------
  // Palette
  // ------------------------------------------------------------------------
  function palette() {
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    return light ? {
      light: true, edge: 0x0b7285, shell: 0x4a6a8a, slab: 0xb9c6d3, grid: 0x9fb0c2, ground: 0xc9d4df,
      ok: 0x0f9d78, warn: 0xd97706, crit: 0xdc2626, off: 0x8b99ab, lamp: 0xd9a006, hvac: 0x2563eb, socket: 0x0d9488, water: 0x0891b2, solar: 0x365f9c, hl: 0x0b7285
    } : {
      light: false, edge: 0x2dd4bf, shell: 0x7fb7ff, slab: 0x18222e, grid: 0x1a2a3b, ground: 0x0a1119,
      ok: 0x34d399, warn: 0xf59e0b, crit: 0xef4444, off: 0x64748b, lamp: 0xfbbf24, hvac: 0x5aa2ff, socket: 0x2dd4bf, water: 0x22d3ee, solar: 0x2b4f86, hl: 0xbff7ee
    };
  }

  // ------------------------------------------------------------------------
  // WebGL scene
  // ------------------------------------------------------------------------
  var FW = 15, FD = 9.6, FH = 1.18, SL = 0.12;

  function initGL() {
    if (typeof THREE === 'undefined') {
      var ng = $('twinNoGL'); ng.style.display = 'flex'; ng.textContent = '3D engine (three.js) is not loaded.';
      return false;
    }
    var wrap = $('twinCanvasWrap');
    try {
      G.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch (e) {
      var ng2 = $('twinNoGL'); ng2.style.display = 'flex'; ng2.textContent = 'WebGL is not available in this browser.';
      return false;
    }
    G.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    G.renderer.setClearColor(0x000000, 0);
    wrap.appendChild(G.renderer.domElement);
    G.scene = new THREE.Scene();
    G.camera = new THREE.PerspectiveCamera(32, 1, 0.1, 300);
    G.root = new THREE.Group(); G.scene.add(G.root);
    G.infra = new THREE.Group(); G.scene.add(G.infra);
    G.scene.add(new THREE.HemisphereLight(0xdfeaff, 0x101820, 0.95));
    var dl = new THREE.DirectionalLight(0xffffff, 0.85); dl.position.set(10, 18, 12); G.scene.add(dl);
    G.grid = new THREE.GridHelper(90, 90, 0x1a2a3b, 0x1a2a3b);
    G.grid.material.transparent = true; G.grid.material.opacity = 0.55; G.grid.position.y = -0.005;
    G.scene.add(G.grid);
    G.ray = new THREE.Raycaster();
    G.cur = { theta: 0.62, phi: 1.1, radius: 30, tx: 0, ty: 4, tz: 0 };
    G.goal = Object.assign({}, G.cur);
    G.ptrs = new Map(); G.moved = 0; G.pinch = 0;
    G.flows = []; G.floors = []; G.last = 0; G.w = 1; G.h = 1;
    G.pal = palette();
    bindPointer(G.renderer.domElement);
    return true;
  }

  function disposeObj(o) {
    o.traverse(function (c) {
      if (c.geometry) c.geometry.dispose();
      if (c.material) { (Array.isArray(c.material) ? c.material : [c.material]).forEach(function (m) { m.dispose(); }); }
    });
  }

  function floorHeight(f) { return f.kind === 'roof' ? FH * 0.9 : FH; }

  function buildScene() {
    if (!G.root) return;
    G.root.children.slice().forEach(function (c) { G.root.remove(c); disposeObj(c); });
    G.infra.children.slice().forEach(function (c) { G.infra.remove(c); disposeObj(c); });
    G.floors = []; G.flows = [];
    var P = G.pal;

    M.floors.forEach(function (f, i) {
      var g = new THREE.Group(); g.position.y = i * FH; G.root.add(g);
      var h = floorHeight(f);
      var slabMat = new THREE.MeshStandardMaterial({ color: P.slab, roughness: 0.65, metalness: 0.35, transparent: true });
      var slab = new THREE.Mesh(new THREE.BoxGeometry(FW + 0.35, SL, FD + 0.35), slabMat);
      slab.position.y = SL / 2; g.add(slab);
      var shellGeo = new THREE.BoxGeometry(FW, h - SL, FD);
      var shellMat = new THREE.MeshStandardMaterial({ color: P.edge, transparent: true, opacity: 0.1, depthWrite: false, roughness: 0.4, metalness: 0.1 });
      var shell = new THREE.Mesh(shellGeo, shellMat); shell.position.y = SL + (h - SL) / 2; shell.userData.floor = i; g.add(shell);
      var edgeMat = new THREE.LineBasicMaterial({ color: P.edge, transparent: true, opacity: 0.85 });
      var edges = new THREE.LineSegments(new THREE.EdgesGeometry(shellGeo), edgeMat); edges.position.copy(shell.position); g.add(edges);
      // façade windows (warm = lighting load)
      var winMat = new THREE.MeshBasicMaterial({ color: 0xffd28a, transparent: true, opacity: 0.2, depthWrite: false });
      if (f.kind !== 'roof') {
        for (var w = 0; w < 7; w++) {
          var wx = -FW / 2 + 1.1 + w * ((FW - 2.2) / 6);
          [FD / 2 + 0.006, -FD / 2 - 0.006].forEach(function (zz, zi) {
            var win = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.36), winMat);
            win.position.set(wx, SL + (h - SL) * 0.55, zz); if (zi) win.rotation.y = Math.PI; g.add(win);
          });
        }
      }
      var rg = new THREE.Group(); g.add(rg);
      var fo = { f: f, i: i, g: g, h: h, slabMat: slabMat, shell: shell, shellMat: shellMat, edgeMat: edgeMat, winMat: winMat, rg: rg, rooms: [], markers: [], cur: { a: 1, lift: 0, ra: f.kind === 'roof' ? 1 : 0 } };
      buildRooms(fo);
      G.floors.push(fo);
    });
    buildInfra();
  }

  function buildRooms(fo) {
    var f = fo.f, nr = f.rooms.length, P = G.pal;
    if (!nr) return;
    var rows = nr > 3 ? 2 : 1, cols = Math.ceil(nr / rows);
    var cw = (FW - 0.5) / cols, cd = (FD - 0.5) / rows;
    f.rooms.forEach(function (r, k) {
      var row = Math.floor(k / cols), col = k % cols;
      var cx = -FW / 2 + 0.25 + cw * (col + 0.5), cz = -FD / 2 + 0.25 + cd * (row + 0.5);
      var rh = (f.kind === 'roof') ? 0.55 : FH - SL - 0.2, geo, mesh, mat;
      mat = new THREE.MeshStandardMaterial({ color: P.ok, transparent: true, opacity: 0.2, depthWrite: false, roughness: 0.5, metalness: 0.1 });
      if (r.equip === 'tank') {
        var rad = Math.min(cw, cd) * 0.38; rh = 0.75;
        geo = new THREE.CylinderGeometry(rad, rad, rh, 32, 1, false);
      } else if (r.equip === 'solar') {
        rh = 0.12; geo = new THREE.BoxGeometry(cw - 0.2, rh, cd - 0.2);
      } else {
        geo = new THREE.BoxGeometry(cw - 0.16, rh, cd - 0.16);
      }
      mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(cx, SL + rh / 2 + 0.01, cz); mesh.userData.room = r.id; fo.rg.add(mesh);
      var eMat = new THREE.LineBasicMaterial({ color: P.ok, transparent: true, opacity: 0.9 });
      var edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), eMat); edges.position.copy(mesh.position); fo.rg.add(edges);
      var ro = { r: r, mesh: mesh, mat: mat, eMat: eMat, rh: rh, cx: cx, cz: cz, fill: null };
      if (r.equip === 'tank') {
        var fillGeo = new THREE.CylinderGeometry(Math.min(cw, cd) * 0.365, Math.min(cw, cd) * 0.365, 1, 32);
        var fillMat = new THREE.MeshBasicMaterial({ color: P.water, transparent: true, opacity: 0.55, depthWrite: false });
        ro.fill = new THREE.Mesh(fillGeo, fillMat); ro.fill.position.copy(mesh.position); fo.rg.add(ro.fill);
      }
      if (r.equip === 'solar') {
        var panels = new THREE.GridHelper(Math.max(cw, cd) - 0.3, 10, 0x6aa8ff, 0x3a6aa8);
        panels.position.set(cx, SL + rh + 0.02, cz); panels.scale.set((cw - 0.3) / (Math.max(cw, cd) - 0.3), 1, (cd - 0.3) / (Math.max(cw, cd) - 0.3)); fo.rg.add(panels);
      }
      // device markers
      var n = r.devices.length;
      r.devices.forEach(function (d, di) {
        var per = 6, rowi = Math.floor(di / per), coli = di % per;
        var cnt = Math.min(per, n - rowi * per);
        var span = Math.min(cw - 0.7, 0.55 * (cnt - 1));
        var mx = cx - span / 2 + (cnt > 1 ? span * coli / (cnt - 1) : 0);
        var mz = cz + (rowi - 0.5 * (Math.ceil(n / per) - 1)) * 0.5;
        var mm = new THREE.Mesh(new THREE.SphereGeometry(0.075, 14, 14), new THREE.MeshBasicMaterial({ color: P.off, transparent: true, opacity: 0.9 }));
        mm.position.set(mx, SL + 0.18, mz); mm.userData.dev = { roomId: r.id, devId: d.id };
        fo.rg.add(mm);
        fo.markers.push({ mesh: mm, dev: d, r: r });
      });
      fo.rooms.push(ro);
    });
  }

  function buildInfra() {
    var P = G.pal, n = M.floors.length, totalH = (n - 1) * FH + floorHeight(M.floors[n - 1]);
    // electrical riser (always)
    var ex = -FW / 2 - 0.55, ez = FD / 2 - 0.4;
    var eMat = new THREE.MeshBasicMaterial({ color: P.ok, transparent: true, opacity: 0.35 });
    var eRiser = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, totalH + 0.4, 8), eMat);
    eRiser.position.set(ex, (totalH + 0.4) / 2 - 0.2, ez); G.infra.add(eRiser);
    mkFlow('energy', P.ok, ex, ez, 0, totalH + 0.1, 12);
    var w = M.site && M.site.water;
    if (w) {
      var wx = FW / 2 + 0.55, wz = -FD / 2 + 0.4;
      var wMat = new THREE.MeshBasicMaterial({ color: P.water, transparent: true, opacity: 0.4 });
      var wRiser = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, totalH + 1.3, 10), wMat);
      wRiser.position.set(wx, (totalH + 1.3) / 2 - 1.3, wz); G.infra.add(wRiser);
      mkFlow('water', P.water, wx, wz, -1.1, totalH, 16);
      // underground tank
      var tw = FW * 0.62, td = FD * 0.55, th = 1.3;
      var tgeo = new THREE.BoxGeometry(tw, th, td);
      var tank = new THREE.Mesh(tgeo, new THREE.MeshBasicMaterial({ color: P.water, transparent: true, opacity: 0.08, depthWrite: false }));
      tank.position.set(0, -th / 2 - 0.05, 0); G.infra.add(tank);
      var tedge = new THREE.LineSegments(new THREE.EdgesGeometry(tgeo), new THREE.LineBasicMaterial({ color: P.water, transparent: true, opacity: 0.7 }));
      tedge.position.copy(tank.position); G.infra.add(tedge);
      var lvl = (w.ground && w.ground.level) || 0.9;
      G.groundFill = new THREE.Mesh(new THREE.BoxGeometry(tw - 0.1, 1, td - 0.1), new THREE.MeshBasicMaterial({ color: P.water, transparent: true, opacity: 0.4, depthWrite: false }));
      G.groundFill.userData = { base: -th - 0.05, h: th - 0.1 };
      G.groundFill.scale.y = Math.max(0.05, (th - 0.1) * lvl); G.groundFill.position.set(0, G.groundFill.userData.base + 0.05 + G.groundFill.scale.y / 2, 0);
      G.infra.add(G.groundFill);
      // pump
      var pump = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.5, 20), new THREE.MeshStandardMaterial({ color: 0x3b556f, metalness: 0.5, roughness: 0.4 }));
      pump.rotation.z = Math.PI / 2; pump.position.set(FW / 2 + 0.2, -0.6, wz); G.infra.add(pump);
    }
  }
  function mkFlow(kind, color, x, z, y0, y1, n) {
    var geo = new THREE.SphereGeometry(0.055, 10, 10);
    for (var i = 0; i < n; i++) {
      var m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.95 }));
      G.infra.add(m);
      G.flows.push({ m: m, kind: kind, x: x, z: z, y0: y0, y1: y1, t: i / n });
    }
  }

  // ---- camera presets ----
  function fitRadius(w, h) {
    var fov = G.camera.fov * Math.PI / 180, asp = Math.max(0.5, G.w / G.h);
    return Math.max((h / 2) / Math.tan(fov / 2), (w / 2) / (Math.tan(fov / 2) * asp));
  }
  function roomWorld(roomId) {
    for (var i = 0; i < G.floors.length; i++) {
      var fo = G.floors[i];
      for (var k = 0; k < fo.rooms.length; k++) if (fo.rooms[k].r.id === roomId) return { fo: fo, ro: fo.rooms[k] };
    }
    return null;
  }
  function presetFor() {
    var n = M.floors.length, last = M.floors[n - 1], totalH = (n - 1) * FH + floorHeight(last);
    var sideW = 160 + (S.roomId ? 340 : 0);
    var aspBoost = Math.max(0.6, (G.w - sideW) / Math.max(1, G.w));
    if (S.view === 'overview') {
      var r = fitRadius(FW * 1.7, Math.max(totalH * 1.35, FD * 1.7) + 4) / Math.pow(aspBoost, 0.6);
      return { theta: 0.62, phi: S.plan ? 0.05 : 1.1, radius: S.plan ? fitRadius(FW * 1.5, FD * 1.9) * 1.15 : r, tx: 0, ty: S.plan ? 0 : totalH * 0.42, tz: 0 };
    }
    var y = S.floorIdx * FH + FH * 0.4;
    var base = fitRadius(FW * 1.25, FD * 1.9) / Math.pow(aspBoost, 0.5);
    if (S.roomId) {
      var rw = roomWorld(S.roomId);
      if (rw) return { theta: S.plan ? 0 : 0.3, phi: S.plan ? 0.05 : 0.95, radius: base * 0.55, tx: rw.ro.cx, ty: y, tz: rw.ro.cz };
    }
    return { theta: S.plan ? 0 : 0.34, phi: S.plan ? 0.05 : 0.93, radius: base * (S.plan ? 1.02 : 0.92), tx: 0, ty: y, tz: 0 };
  }
  function applyPreset(snap) {
    if (!G.camera || !M) return;
    G.goal = presetFor();
    if (snap) G.cur = Object.assign({}, G.goal);
  }

  // ---- input ----
  function bindPointer(el) {
    el.addEventListener('pointerdown', function (e) {
      G.ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      G.moved = 0; G.downAt = { x: e.clientX, y: e.clientY };
      try { el.setPointerCapture(e.pointerId); } catch (x) { }
      if (G.ptrs.size === 2) { var p = Array.from(G.ptrs.values()); G.pinch = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); }
    });
    el.addEventListener('pointermove', function (e) {
      var p = G.ptrs.get(e.pointerId);
      if (!p) { onHover(e); return; }
      var dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (G.ptrs.size === 1) {
        G.goal.theta -= dx * 0.0055;
        G.goal.phi = clamp(G.goal.phi - dy * 0.0045, 0.04, 1.5);
        G.moved += Math.abs(dx) + Math.abs(dy);
        if (G.moved > 6) { S.userMoved = true; hideTip(); }
      } else if (G.ptrs.size === 2) {
        var q = Array.from(G.ptrs.values()), d = Math.hypot(q[0].x - q[1].x, q[0].y - q[1].y);
        if (G.pinch > 0) G.goal.radius = clamp(G.goal.radius * (G.pinch / d), 3, 90);
        G.pinch = d; G.moved += 10;
      }
    });
    var up = function (e) {
      var had = G.ptrs.has(e.pointerId);
      G.ptrs.delete(e.pointerId);
      if (G.ptrs.size < 2) G.pinch = 0;
      if (had && G.moved < 6 && G.ptrs.size === 0) onClickPick(e);
    };
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', function (e) { G.ptrs.delete(e.pointerId); G.pinch = 0; });
    el.addEventListener('pointerleave', function () { if (!G.ptrs.size) { setHover(null); hideTip(); } });
    el.addEventListener('wheel', function (e) {
      e.preventDefault();
      G.goal.radius = clamp(G.goal.radius * (1 + e.deltaY * 0.0012), 3, 90);
    }, { passive: false });
  }

  function pickAt(e) {
    var rect = G.renderer.domElement.getBoundingClientRect();
    var nx = ((e.clientX - rect.left) / rect.width) * 2 - 1, ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    G.ray.setFromCamera({ x: nx, y: ny }, G.camera);
    var hit;
    if (S.view === 'overview') {
      var shells = G.floors.filter(function (fo) { return fo.cur.a > 0.2; }).map(function (fo) { return fo.shell; });
      hit = G.ray.intersectObjects(shells, false)[0];
      if (hit) return { kind: 'floor', i: hit.object.userData.floor };
      return null;
    }
    var fo = G.floors[S.floorIdx]; if (!fo) return null;
    var mk = fo.markers.map(function (m) { return m.mesh; });
    hit = G.ray.intersectObjects(mk, false)[0];
    if (hit) return { kind: 'dev', roomId: hit.object.userData.dev.roomId, devId: hit.object.userData.dev.devId };
    var rm = fo.rooms.map(function (r) { return r.mesh; });
    hit = G.ray.intersectObjects(rm, false)[0];
    if (hit) return { kind: 'room', id: hit.object.userData.room };
    return null;
  }
  function onHover(e) {
    var h = pickAt(e);
    setHover(h);
    if (!h) { hideTip(); G.renderer.domElement.style.cursor = 'default'; return; }
    G.renderer.domElement.style.cursor = 'pointer';
    var shell = $('twinShell').getBoundingClientRect();
    var txt = '';
    if (h.kind === 'floor') { var f = M.floors[h.i]; txt = esc(nm(f.name)) + ' · ' + fmtPow(f.agg.kw); }
    else if (h.kind === 'room') { var rw = roomWorld(h.id); if (rw) txt = esc(nm(rw.ro.r.name)) + ' · ' + fmtPow(rw.ro.r.kw); }
    else if (h.kind === 'dev') {
      var rw2 = roomWorld(h.roomId); if (rw2) { var d = rw2.ro.r.devices.filter(function (x) { return x.id === h.devId; })[0]; if (d) txt = esc(nm(d.name)) + (d.channels.length ? ' · ' + (d.channels.some(function (c) { return c.state === 'ON'; }) ? T('on') : T('off')) : ''); }
    }
    var tip = $('twinTip'); tip.innerHTML = txt; tip.style.display = txt ? 'block' : 'none';
    tip.style.left = (e.clientX - shell.left + 14) + 'px'; tip.style.top = (e.clientY - shell.top + 14) + 'px';
  }
  function hideTip() { var tip = $('twinTip'); if (tip) tip.style.display = 'none'; }
  function setHover(h) {
    var a = JSON.stringify(h), b = JSON.stringify(S.hover);
    if (a === b) return;
    S.hover = h;
    CO.forEach(function (c) { c.el.classList.toggle('hot', !!h && ((h.kind === 'floor' && c.kind === 'floor' && c.i === h.i) || ((h.kind === 'room' || h.kind === 'dev') && c.kind === 'room' && c.id === (h.id || h.roomId)))); });
  }
  function onClickPick(e) {
    var h = pickAt(e);
    if (!h) { if (S.view === 'floor' && S.roomId) { selectRoom(null); } return; }
    if (h.kind === 'floor') selectFloor(h.i);
    else if (h.kind === 'room') selectRoom(h.id);
    else if (h.kind === 'dev') selectRoom(h.roomId);
  }

  // ---- navigation ----
  function selectFloor(i) {
    S.view = 'floor'; S.floorIdx = clamp(i, 0, M.floors.length - 1); S.roomId = null; S.userMoved = false;
    afterNav();
  }
  function selectRoom(id) {
    if (id && !roomWorld(id)) return;
    S.roomId = id; if (id) S.view = 'floor';
    afterNav();
  }
  function goOverview() { S.view = 'overview'; S.roomId = null; S.userMoved = false; afterNav(); }
  function goBack() { if (S.roomId) selectRoom(null); else if (S.view === 'floor') goOverview(); }
  function afterNav() {
    rebuildCallouts(); renderAll(); applyPreset(false);
  }

  // ---- per-frame ----
  function updateCamera(dt) {
    var k = 1 - Math.exp(-dt * 5.2), c = G.cur, g = G.goal;
    ['theta', 'phi', 'radius', 'tx', 'ty', 'tz'].forEach(function (key) { c[key] = lerp(c[key], g[key], k); });
    var sp = Math.sin(c.phi);
    G.camera.position.set(c.tx + c.radius * sp * Math.sin(c.theta), c.ty + c.radius * Math.cos(c.phi), c.tz + c.radius * sp * Math.cos(c.theta));
    G.camera.lookAt(c.tx, c.ty, c.tz);
  }
  function statusColor(P, st) { return st === 'crit' ? P.crit : st === 'warn' ? P.warn : st === 'off' ? P.off : P.ok; }

  function updateScene(dt) {
    var P = G.pal, k = 1 - Math.exp(-dt * 6);
    var maxF = 0.0001; M.floors.forEach(function (f) { if (f.kind !== 'roof') maxF = Math.max(maxF, f.agg.kw); });
    var hov = S.hover;
    G.grid.material.color.setHex(P.grid);
    G.floors.forEach(function (fo) {
      var f = fo.f, ta = 1, tl = 0, tr = 0;
      if (S.view === 'overview') { ta = 1; tl = 0; tr = f.kind === 'roof' ? 1 : 0; }
      else if (fo.i > S.floorIdx) { ta = 0; tl = 2.6; tr = 0; }
      else if (fo.i < S.floorIdx) { ta = 0.22; tl = 0; tr = 0; }
      else { ta = 1; tl = 0; tr = 1; }
      var c = fo.cur; c.a = lerp(c.a, ta, k); c.lift = lerp(c.lift, tl, k); c.ra = lerp(c.ra, tr, k);
      fo.g.position.y = fo.i * FH + c.lift;
      fo.g.visible = c.a > 0.015;
      if (!fo.g.visible) return;
      var ratio = f.kind === 'roof' ? 0.15 : f.agg.kw / maxF;
      var stc = statusColor(P, f.agg.alarms ? (f.rooms.some(function (r) { return r.status === 'crit'; }) ? 'crit' : 'warn') : 'ok');
      var isHover = hov && hov.kind === 'floor' && hov.i === fo.i;
      var isSel = S.view === 'floor' && S.floorIdx === fo.i;
      var edgeCol = (f.agg.alarms ? stc : P.edge);
      fo.shellMat.color.setHex(f.agg.alarms ? stc : P.edge);
      fo.shellMat.opacity = ((0.05 + 0.16 * ratio) + (isHover ? 0.12 : 0)) * c.a * (isSel ? 0.35 : 1);
      fo.edgeMat.color.setHex(isHover || isSel ? P.hl : edgeCol);
      fo.edgeMat.opacity = (isHover || isSel ? 1 : 0.7) * c.a;
      fo.slabMat.color.setHex(P.slab); fo.slabMat.opacity = c.a;
      var lr = f.agg.totL ? f.agg.onL / f.agg.totL : 0;
      fo.winMat.opacity = (0.08 + 0.55 * lr) * c.a;
      fo.rg.visible = c.ra > 0.02;
      if (fo.rg.visible) {
        var maxR = 0.0001; f.rooms.forEach(function (r) { maxR = Math.max(maxR, r.kw); });
        fo.rooms.forEach(function (ro) {
          var r = ro.r, col, op;
          var rh = hov && ((hov.kind === 'room' && hov.id === r.id) || (hov.kind === 'dev' && hov.roomId === r.id));
          var rs = S.roomId === r.id;
          if (r.equip === 'tank') { col = P.water; op = 0.16; }
          else if (r.equip === 'solar') { col = P.solar; op = 0.7; }
          else { col = statusColor(P, r.status); op = 0.12 + 0.34 * (r.kw / maxR); }
          ro.mat.color.setHex(col);
          ro.mat.opacity = clamp(op + (rh ? 0.14 : 0) + (rs ? 0.22 : 0), 0, 0.85) * c.ra * (S.roomId && !rs ? 0.55 : 1);
          ro.eMat.color.setHex(rs || rh ? P.hl : col);
          ro.eMat.opacity = (rs ? 1 : rh ? 0.95 : 0.65) * c.ra;
          if (ro.fill) { var lv = clamp(r.level || 0, 0.02, 1); ro.fill.scale.y = ro.rh * lv; ro.fill.position.y = SL + 0.01 + (ro.rh * lv) / 2; ro.fill.material.color.setHex(P.water); ro.fill.material.opacity = 0.55 * c.ra; }
        });
        fo.markers.forEach(function (m) {
          var d = m.dev, on = d.channels.some(function (c2) { return c2.state === 'ON'; });
          var col = d.cat === 'sensor' ? P.ok : (on ? (d.cat === 'light' ? P.lamp : d.cat === 'hvac' ? P.hvac : d.cat === 'socket' ? P.socket : P.ok) : P.off);
          m.mesh.material.color.setHex(col);
          m.mesh.material.opacity = (on || d.cat === 'sensor' ? 1 : 0.55) * c.ra;
          var sc = (on ? 1.35 : 1) * (hov && hov.kind === 'dev' && hov.devId === d.id ? 1.5 : 1);
          m.mesh.scale.setScalar(lerp(m.mesh.scale.x, sc, k));
        });
      }
    });
    G.infra.visible = S.view === 'overview';
    if (G.infra.visible) {
      var cons = M.site.cons || 0, w = M.site.water;
      G.flows.forEach(function (fl) {
        var sp = fl.kind === 'water' ? (w ? clamp(w.lpm / 245, 0, 1.6) * 0.3 : 0) : (cons > 0.02 ? clamp(cons / 140, 0.06, 1) * 0.3 : 0);
        fl.t = (fl.t + dt * sp) % 1;
        fl.m.position.set(fl.x, lerp(fl.y0, fl.y1, fl.t), fl.z);
        fl.m.visible = sp > 0.001;
        fl.m.material.opacity = Math.sin(fl.t * Math.PI) * 0.95;
      });
      if (G.groundFill && w && w.ground) {
        var sy = Math.max(0.05, G.groundFill.userData.h * w.ground.level);
        G.groundFill.scale.y = sy; G.groundFill.position.y = G.groundFill.userData.base + 0.05 + sy / 2;
      }
    }
  }

  // ---- callouts ----
  function rebuildCallouts() {
    var host = $('twinCallouts'), svg = $('twinLines');
    host.innerHTML = ''; svg.innerHTML = ''; CO = [];
    var items = [];
    if (!M) return;
    if (S.view === 'overview') {
      for (var i = M.floors.length - 1; i >= 0; i--) items.push({ kind: 'floor', i: i, id: M.floors[i].id });
    } else {
      M.floors[S.floorIdx].rooms.forEach(function (r) { items.push({ kind: 'room', id: r.id, i: S.floorIdx }); });
    }
    items.forEach(function (it) {
      var el = document.createElement('div'); el.className = 'tw-card'; el.setAttribute('data-act', 'card'); el.setAttribute('data-kind', it.kind); el.setAttribute('data-id', it.kind === 'floor' ? it.i : it.id);
      host.appendChild(el);
      var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      var dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); dot.setAttribute('r', '3.5');
      g.appendChild(line); g.appendChild(dot); svg.appendChild(g);
      it.el = el; it.g = g; it.line = line; it.dot = dot; it.side = null;
      CO.push(it);
    });
    updateCallouts();
  }
  function barsMini(n) { var h = ''; for (var i = 0; i < n; i++) h += '<i style="height:' + Math.round(25 + 75 * Math.abs(Math.sin(i * 1.7 + n))) + '%"></i>'; return h; }
  function updateCallouts() {
    if (!M) return;
    CO.forEach(function (it) {
      var el = it.el, html = '', cls = 'tw-card';
      if (it.kind === 'floor') {
        var f = M.floors[it.i]; if (!f) return;
        var st = f.rooms.some(function (r) { return r.status === 'crit'; }) ? ' crit' : (f.agg.alarms ? ' warn' : '');
        cls += st + (S.view === 'floor' && S.floorIdx === it.i ? ' sel' : '');
        var val = f.kind === 'roof' && M.mock ? fmtPow(f.agg.kw) : fmtPow(f.agg.kw);
        html = '<div class="tw-card-h"><span class="tw-card-name tw-t">' + esc(nm(f.name)) + '</span><b>' + val + '</b></div>';
      } else {
        var rw = M.floors[S.floorIdx] && M.floors[S.floorIdx].rooms.filter(function (r) { return r.id === it.id; })[0]; if (!rw) return;
        cls += (rw.status === 'crit' ? ' crit' : rw.status === 'warn' ? ' warn' : '') + (S.roomId === rw.id ? ' sel' : '') + (S.roomId && S.roomId !== rw.id ? ' dim' : '');
        var big = fmtPow(rw.kw), rows = '';
        if (rw.equip === 'solar') { big = fmtPow(rw.gen || 0); rows = '<div class="tw-card-row"><span>' + ic('solar', 'c-energy') + T('twGen') + '</span><b>' + fmtPow(rw.gen || 0) + '</b></div>'; }
        else if (rw.equip === 'tank') { big = Math.round((rw.level || 0) * 100) + '%'; rows = '<div class="tw-card-row"><span>' + ic('drop', 'c-water') + T('twLevel') + '</span><b>' + fmtNum((rw.level || 0) * (rw.cap || 0)) + ' L</b></div>'; }
        else {
          rows = '<div class="tw-card-row"><span>' + ic('bulb', 'c-light') + '</span><b>' + fmtPow(rw.kwLight) + '</b></div>' +
            '<div class="tw-card-row"><span>' + ic('snow', 'c-hvac') + '</span><b>' + fmtPow(rw.kwHvac) + '</b></div>' +
            '<div class="tw-card-row"><span>' + ic('plug', 'c-socket') + '</span><b>' + fmtPow(rw.kwSocket) + '</b></div>';
        }
        html = '<div class="tw-card-h"><span class="tw-card-name tw-t">' + ic(rw.icon && ICON[rw.icon] ? rw.icon : 'door', 'c-accent') + esc(nm(rw.name)) + '</span><b>' + big + '</b></div><div class="tw-card-rows">' + rows + '</div>';
      }
      if (el.innerHTML !== html) el.innerHTML = html;
      el.className = cls + (S.hover && ((S.hover.kind === 'floor' && it.kind === 'floor' && S.hover.i === it.i) || (S.hover.kind !== 'floor' && it.kind === 'room' && (S.hover.id || S.hover.roomId) === it.id)) ? ' hot' : '');
      it.w = el.offsetWidth; it.h = el.offsetHeight;
    });
  }
  var _v = null;
  function layoutCallouts() {
    if (!CO.length || !G.camera) return;
    if (!_v) _v = new THREE.Vector3();
    var W = G.w, H = G.h;
    var railW = 134, panelW = S.roomId ? 340 : 0;
    var showChips = M && M.mock && S.view === 'overview';
    var topY = S.view === 'overview' ? (M && M.mock ? 214 : 150) : 60;
    var botY = H - 150;
    var cols = { L: [], R: [] };
    CO.forEach(function (it) {
      if (!it.w) { it.w = it.el.offsetWidth; it.h = it.el.offsetHeight; }
      var fo, ax, ay, az;
      if (it.kind === 'floor') {
        fo = G.floors[it.i]; if (!fo || !fo.g.visible) { it.el.style.display = 'none'; it.g.style.display = 'none'; return; }
        _v.set(-FW / 2, fo.g.position.y + fo.h * 0.55, 0);
      } else {
        var rw = roomWorld(it.id); if (!rw) { it.el.style.display = 'none'; it.g.style.display = 'none'; return; }
        _v.set(rw.ro.cx, rw.fo.g.position.y + SL + rw.ro.rh + 0.02, rw.ro.cz);
      }
      _v.project(G.camera);
      if (_v.z > 1) { it.el.style.display = 'none'; it.g.style.display = 'none'; return; }
      it.el.style.display = ''; it.g.style.display = '';
      it.ax = (_v.x * 0.5 + 0.5) * W; it.ay = (-_v.y * 0.5 + 0.5) * H;
      var side;
      if (it.kind === 'floor') side = 'L';
      else {
        if (it.side == null) it.side = it.ax < W / 2 ? 'L' : 'R';
        else if (it.side === 'L' && it.ax > W / 2 + 70) it.side = 'R';
        else if (it.side === 'R' && it.ax < W / 2 - 70) it.side = 'L';
        side = it.side;
      }
      it.s = side; cols[side].push(it);
    });
    ['L', 'R'].forEach(function (s) {
      var col = cols[s]; col.sort(function (a, b) { return a.ay - b.ay; });
      var gap = it_gap(), y = topY;
      col.forEach(function (it) { it.ty = Math.max(it.ay - it.h / 2, y); y = it.ty + it.h + gap; });
      var over = (y - gap) - botY;
      if (over > 0) {
        for (var i = col.length - 1; i >= 0; i--) {
          var mx = (i === col.length - 1 ? botY : col[i + 1].ty - gap) - col[i].h;
          if (col[i].ty > mx) col[i].ty = mx;
        }
      }
      col.forEach(function (it) {
        var x = s === 'L' ? 14 : W - 14 - railW - panelW - it.w;
        it.el.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(it.ty) + 'px)';
        var ex = s === 'L' ? x + it.w : x, ey = it.ty + it.h / 2;
        it.line.setAttribute('x1', ex); it.line.setAttribute('y1', ey); it.line.setAttribute('x2', it.ax); it.line.setAttribute('y2', it.ay);
        it.dot.setAttribute('cx', it.ax); it.dot.setAttribute('cy', it.ay);
      });
    });
  }
  function it_gap() { return S.view === 'overview' ? 5 : 8; }

  // ---- render loop ----
  function frame(ts) {
    if (!S.visible) { G.raf = 0; return; }
    G.raf = requestAnimationFrame(frame);
    var dt = Math.min(0.05, (ts - (G.last || ts)) / 1000); G.last = ts;
    updateCamera(dt); updateScene(dt); layoutCallouts();
    G.renderer.render(G.scene, G.camera);
  }
  function resize() {
    if (!G.renderer) return;
    var wrap = $('twinCanvasWrap'); var w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return;
    var first = G.w <= 1;
    G.w = w; G.h = h; G.renderer.setSize(w, h, false);
    G.camera.aspect = w / h; G.camera.updateProjectionMatrix();
    if (M) applyPreset(first);
  }

  // ------------------------------------------------------------------------
  // HUD rendering
  // ------------------------------------------------------------------------
  function scopeRooms() {
    if (S.roomId) { var rw = roomWorld(S.roomId); return rw ? [rw.ro.r] : []; }
    if (S.view === 'floor') return M.floors[S.floorIdx].rooms;
    var all = []; M.floors.forEach(function (f) { all = all.concat(f.rooms); }); return all;
  }
  function scopeName() {
    if (S.roomId) { var rw = roomWorld(S.roomId); return rw ? nm(rw.ro.r.name) : ''; }
    if (S.view === 'floor') return nm(M.floors[S.floorIdx].name);
    return T('twBuilding');
  }
  function barsHTML(arr, color, hi) {
    if (!arr || !arr.length) return '';
    var mx = Math.max.apply(null, arr.concat([0.0001]));
    var out = '<div class="tw-bars" style="color:' + color + '">';
    arr.forEach(function (v, i) { out += '<i' + (hi != null && i !== hi ? ' class="dim"' : '') + ' style="height:' + Math.max(4, Math.round(v / mx * 100)) + '%"></i>'; });
    return out + '</div>';
  }
  function axisHTML() { return '<div class="tw-axis"><span>00</span><span>04</span><span>08</span><span>12</span><span>16</span><span>20</span><span>24</span></div>'; }

  function renderTop() {
    var cur = null;
    var crumbs = '<button class="tw-iconbtn" data-act="back" ' + (S.view === 'overview' ? 'disabled' : '') + ' title="' + T('twBack') + '">' + ic('left') + '</button>';
    crumbs += '<button class="tw-crumb tw-t ' + (S.view === 'overview' ? 'cur' : '') + '" data-act="overview">' + T('twBuilding') + '</button>';
    if (S.view === 'floor') {
      crumbs += '<span class="tw-sep">/</span><button class="tw-crumb tw-t ' + (S.roomId ? '' : 'cur') + '" data-act="floor" data-i="' + S.floorIdx + '">' + esc(nm(M.floors[S.floorIdx].name)) + '</button>';
      if (S.roomId) { var rw = roomWorld(S.roomId); crumbs += '<span class="tw-sep">/</span><span class="tw-crumb cur tw-t">' + esc(rw ? nm(rw.ro.r.name) : '') + '</span>'; }
    }
    var tools = '';
    if (M.mock) tools += '<span class="tw-badge-mock"><i></i>' + T('twMockBadge') + '</span>';
    tools += '<div class="tw-seg tw-panel-box"><button data-act="view3d" class="' + (S.plan ? '' : 'active') + '">' + ic('cube') + T('tw3d') + '</button><button data-act="viewplan" class="' + (S.plan ? 'active' : '') + '">' + ic('map') + T('twPlan') + '</button></div>';
    tools += '<div class="tw-seg tw-panel-box"><button data-act="mode" data-m="live" class="' + (S.mode === 'live' ? 'active' : '') + '">' + T('twLive') + '</button><button data-act="mode" data-m="mock" class="' + (S.mode === 'mock' ? 'active' : '') + '">' + T('twMock') + '</button></div>';
    if (!M.mock) tools += '<button class="tw-iconbtn tw-panel-box" style="width:34px;height:34px" data-act="manage" title="' + T('twManage') + '">' + ic('gear') + '</button>';
    $('twinTop').innerHTML = '<div class="tw-crumbs tw-panel-box">' + crumbs + '</div><div class="tw-tools">' + tools + '</div>';
  }

  function renderKpis() {
    var el = $('twinKpis');
    if (S.view !== 'overview') { el.style.display = 'none'; return; }
    el.style.display = 'flex';
    var s = M.site, a = M.agg, h = '';
    var card = function (icn, cls, label, val, unit, series, color) {
      return '<div class="tw-kpi tw-panel-box"><div class="tw-kpi-h">' + ic(icn, cls) + '<span class="tw-t">' + label + '</span></div><div class="tw-kpi-v">' + val + '<small>' + unit + '</small></div>' + (series && series.length ? barsHTML(series, color) : '<div style="height:22px"></div>') + '</div>';
    };
    if (M.mock) {
      h += card('bolt', 'c-energy', T('twTotalCons'), fmtNum(s.cons, 1), 'kW', M.series.cons, 'var(--tw-energy)');
      h += card('solar', 'c-energy', T('twSolar'), fmtNum(s.solar, 1), 'kW', M.series.solar, 'var(--tw-energy)');
      h += card('grid', 'c-hvac', T('twGrid'), fmtNum(s.grid, 1), 'kW', M.series.grid, 'var(--tw-hvac)');
      h += card('battery', 'c-light', T('twBattery'), fmtNum(s.battery.kw, 1), 'kW · ' + Math.round(s.battery.soc) + '%', M.series.batt, 'var(--tw-light)');
    } else {
      var on = a.onL + a.onH + a.onS, tot = a.totL + a.totH + a.totS;
      h += card('bolt', 'c-energy', T('twTotalCons'), fmtNum(s.cons < 1 ? s.cons * 1000 : s.cons, s.cons < 1 ? 0 : 1), s.cons < 1 ? 'W' : 'kW', M.series.cons, 'var(--tw-energy)');
      h += card('plug', 'c-socket', T('twActiveLoads'), on + '/' + tot, '', null);
      h += card('temp', 'c-hvac', T('twAvgTemp'), a.temp != null ? fmtNum(a.temp, 1) : '—', a.temp != null ? '°C' : '', null);
      h += card('building', 'c-accent', T('twRooms'), a.rooms, M.floors.length + ' ' + T('twFloorCount'), null);
    }
    el.innerHTML = h;
  }

  function renderChips() {
    var el = $('twinChips');
    if (!(M.mock && S.view === 'overview')) { el.style.display = 'none'; return; }
    el.style.display = 'flex';
    var w = M.site.water, tl = 0, tc = 0;
    w.tanks.forEach(function (tk) { tl += tk.level * tk.cap; tc += tk.cap; });
    el.innerHTML =
      '<div class="tw-chip tw-panel-box"><div class="tw-chip-h">' + ic('tank', 'c-water') + T('twTank') + '</div><div class="tw-chip-v">' + fmtNum(tl) + ' <small class="c-muted">/ ' + fmtNum(tc) + ' L</small></div><div class="tw-meter"><span style="width:' + Math.round(tl / tc * 100) + '%"></span></div></div>' +
      '<div class="tw-chip tw-panel-box"><div class="tw-chip-h">' + ic('pump', 'c-water') + T('twPump') + '</div><div class="tw-chip-v"><span class="tw-pill ' + (w.pumpOn ? 'ok' : 'off') + '">' + (w.pumpOn ? T('on') : T('off')) + '</span> ' + fmtNum(w.pumpKw, 1) + ' kW</div></div>' +
      '<div class="tw-chip tw-panel-box"><div class="tw-chip-h">' + ic('gauge', 'c-water') + T('twPressure') + '</div><div class="tw-chip-v">' + fmtNum(w.pressure, 1) + ' <small class="c-muted">bar</small></div></div>' +
      '<div class="tw-chip tw-panel-box"><div class="tw-chip-h">' + ic('flask', 'c-water') + T('twQuality') + '</div><div class="tw-chip-v">' + fmtNum(w.tds) + ' <small class="c-muted">ppm</small> · pH ' + fmtNum(w.ph, 1) + '</div></div>';
  }

  function renderRail() {
    var el = $('twinRail'), h = '';
    for (var i = M.floors.length - 1; i >= 0; i--) {
      var f = M.floors[i], dot = '';
      if (f.rooms.some(function (r) { return r.status === 'crit'; })) dot = '<span class="crit-dot"></span>'; else if (f.agg.alarms) dot = '<span class="warn-dot"></span>';
      h += '<button class="tw-floor-btn tw-t ' + (S.view === 'floor' && S.floorIdx === i ? 'active' : '') + '" data-act="floor" data-i="' + i + '"><span>' + esc(nm(f.name)) + '</span>' + (dot || '<em>' + fmtPow(f.agg.kw) + '</em>') + '</button>';
    }
    el.innerHTML = h;
  }

  function renderPanel() {
    var el = $('twinPanel');
    if (!S.roomId) { el.classList.remove('open'); el.innerHTML = ''; return; }
    var rw = roomWorld(S.roomId); if (!rw) { el.classList.remove('open'); return; }
    var r = rw.ro.r; el.classList.add('open');
    var h = '<div class="tw-p-head"><h3 class="tw-t">' + ic(r.icon && ICON[r.icon] ? r.icon : 'door', 'c-accent lg') + esc(nm(r.name)) + '</h3><button class="tw-iconbtn" data-act="closeRoom">' + ic('x') + '</button></div><div class="tw-p-body">';
    if (r.alarm && r.alarm.msg) h += '<div class="tw-pill ' + r.alarm.level + '" style="align-self:flex-start;padding:5px 10px">' + ic('alert') + esc(nm(r.alarm.msg)) + '</div>';
    if (r.equip === 'solar') {
      h += '<div class="tw-p-kw"><b>' + fmtPow(r.gen || 0) + '</b><small>' + T('twGen') + '</small></div>';
    } else if (r.equip === 'tank') {
      h += '<div class="tw-p-kw"><b>' + Math.round((r.level || 0) * 100) + '%</b><small>' + fmtNum((r.level || 0) * (r.cap || 0)) + ' / ' + fmtNum(r.cap || 0) + ' L</small></div><div class="tw-meter"><span style="width:' + Math.round((r.level || 0) * 100) + '%"></span></div>';
    } else {
      h += '<div class="tw-p-kw"><b>' + fmtPow(r.kw) + '</b><small>' + T('twLoad') + '</small></div>';
      h += '<div class="tw-p-split"><div>' + ic('bulb', 'c-light lg') + T('twLighting') + '<b>' + fmtPow(r.kwLight) + '</b></div><div>' + ic('snow', 'c-hvac lg') + T('twAC') + '<b>' + fmtPow(r.kwHvac) + '</b></div><div>' + ic('plug', 'c-socket lg') + T('twSockets') + '<b>' + fmtPow(r.kwSocket) + '</b></div></div>';
      if (r.temp != null || r.hum != null) h += '<div class="tw-p-env">' + (r.temp != null ? '<span>' + ic('temp', 'c-hvac') + fmtNum(r.temp, 1) + '°C</span>' : '') + (r.hum != null ? '<span>' + ic('drop', 'c-water') + fmtNum(r.hum, 0) + '%</span>' : '') + '</div>';
      if (r.totL + r.totH + r.totS > 0) h += '<div class="tw-p-actions"><button class="tw-btn primary" data-act="roomAll" data-on="1">' + T('twAllOn') + '</button><button class="tw-btn" data-act="roomAll" data-on="0">' + T('twAllOff') + '</button></div>';
      h += '<div class="tw-sec-t">' + T('twDevices') + ' (' + r.devices.length + ')</div>';
      if (!r.devices.length) h += '<div class="c-muted">' + T('twNoDevices') + '</div>';
      r.devices.forEach(function (d, di) {
        var multi = d.channels.length > 1;
        h += '<div class="tw-dev"><div class="tw-dev-h"><div class="tw-dev-n tw-t">' + ic(CAT_ICON[d.cat] || 'chip', CAT_CLS[d.cat] || 'c-muted') + '<span>' + esc(nm(d.name)) + '</span></div>';
        if (d.cat === 'sensor' && !d.channels.length) {
          h += '<span class="tw-dev-kw">' + (d.temp != null ? fmtNum(d.temp, 1) + '°C' : '') + (d.hum != null ? ' · ' + fmtNum(d.hum, 0) + '%' : '') + '</span>';
        } else if (!multi && d.channels[0]) {
          var c0 = d.channels[0];
          h += '<span style="display:flex;align-items:center;gap:8px"><span class="tw-dev-kw">' + fmtPow(c0.kw) + '</span>' + (c0.hasOnOff ? '<button class="tw-sw ' + (c0.state === 'ON' ? 'on' : '') + '" data-act="toggle" data-di="' + di + '" data-ci="0"></button>' : '') + '</span>';
        } else { h += '<span class="tw-dev-kw">' + fmtPow(d.kw) + '</span>'; }
        h += '</div>';
        if (multi) d.channels.forEach(function (c, ci) {
          h += '<div class="tw-ch"><span class="tw-t">' + esc(nm(c.name)) + '</span><span style="display:flex;align-items:center;gap:8px"><span class="tw-dev-kw">' + fmtPow(c.kw) + '</span>' + (c.hasOnOff ? '<button class="tw-sw ' + (c.state === 'ON' ? 'on' : '') + '" data-act="toggle" data-di="' + di + '" data-ci="' + ci + '"></button>' : '') + '</span></div>';
        });
        h += '</div>';
      });
    }
    h += '</div>';
    if (el.getAttribute('data-room') !== S.roomId) el.scrollTop = 0;
    el.setAttribute('data-room', S.roomId);
    var body = el.querySelector('.tw-p-body'), st = body ? body.scrollTop : 0;
    el.innerHTML = h;
    var nb = el.querySelector('.tw-p-body'); if (nb) nb.scrollTop = st;
  }

  function renderBottom() {
    var rooms = scopeRooms(), a = aggregate(rooms), site = M.site;
    var total = a.kwLight + a.kwHvac + a.kwSocket;
    var pct = function (v) { return total > 0.0001 ? Math.round(v / total * 100) : 0; };
    var C = 2 * Math.PI * 34, offs = 0, segs = '';
    [[a.kwLight, 'var(--tw-light)'], [a.kwHvac, 'var(--tw-hvac)'], [a.kwSocket, 'var(--tw-socket)']].forEach(function (p) {
      var len = total > 0.0001 ? p[0] / total * C : 0;
      segs += '<circle cx="42" cy="42" r="34" fill="none" stroke="' + p[1] + '" stroke-width="10" stroke-dasharray="' + len + ' ' + (C - len) + '" stroke-dashoffset="' + (-offs) + '" transform="rotate(-90 42 42)"/>';
      offs += len;
    });
    var big = total < 1 ? fmtNum(total * 1000, 0) : fmtNum(total, 1), unit = total < 1 ? 'W' : 'kW';
    var h = '<div class="tw-sum summary tw-panel-box"><div class="tw-donut"><svg viewBox="0 0 84 84" width="84" height="84"><circle cx="42" cy="42" r="34" fill="none" stroke="var(--tw-line)" stroke-width="10"/>' + segs + '</svg><div class="tw-donut-c"><b>' + big + '</b><small>' + unit + '</small></div></div>' +
      '<div class="tw-legend"><div class="tw-sum-h" style="margin-bottom:2px"><span class="tw-t" style="color:var(--tw-text)">' + esc(scopeName()) + ' · ' + T('twSummary') + '</span></div>' +
      '<div><span>' + ic('bulb', 'c-light') + T('twLighting') + '</span><b>' + fmtPow(a.kwLight) + ' · ' + pct(a.kwLight) + '%</b></div>' +
      '<div><span>' + ic('snow', 'c-hvac') + T('twAC') + '</span><b>' + fmtPow(a.kwHvac) + ' · ' + pct(a.kwHvac) + '%</b></div>' +
      '<div><span>' + ic('plug', 'c-socket') + T('twSockets') + '</span><b>' + fmtPow(a.kwSocket) + ' · ' + pct(a.kwSocket) + '%</b></div></div></div>';
    var share = 1;
    if (M.mock) { var siteKw = M.agg.kw + (M.baseKw || 0); share = siteKw > 0 ? clamp(a.kw / siteKw, 0.01, 1) : 1; if (S.view === 'overview') share = 1; }
    else { share = M.agg.kw > 0 ? clamp(a.kw / M.agg.kw, 0, 1) : 1; }
    var scale = function (arr) { return arr ? arr.map(function (v) { return v * share; }) : null; };
    var nodata = '<div class="tw-nodata tw-t">' + T('twNoData') + '</div>';
    var curHr = new Date().getHours();
    // energy
    var e = scale(M.series.energy), ev;
    if (M.mock) { ev = fmtNum(e.reduce(function (x, y) { return x + y; }, 0), 1) + ' <small>' + T('twKwh') + ' · ' + T('twToday') + '</small>'; }
    else { ev = fmtNum(S.sessionKwh * share, 3) + ' <small>' + T('twKwh') + ' · ' + T('twSession') + '</small>'; }
    h += '<div class="tw-sum tw-panel-box"><div class="tw-sum-h"><span class="tw-t">' + ic('bolt', 'c-energy') + ' ' + T('twEnergy') + '</span></div><div class="tw-sum-v">' + ev + '</div>' + (e && e.length ? barsHTML(e, 'var(--tw-energy)', M.mock ? curHr : null) + (M.mock ? axisHTML() : '') : nodata) + '</div>';
    // water
    var w = scale(M.series.water);
    h += '<div class="tw-sum tw-panel-box"><div class="tw-sum-h"><span class="tw-t">' + ic('drop', 'c-water') + ' ' + T('twWaterUsage') + '</span></div><div class="tw-sum-v">' + (w ? fmtNum(w.reduce(function (x, y) { return x + y; }, 0) / 1000 * 10, 1) + ' <small>m³ · ' + T('twToday') + '</small>' : '—') + '</div>' + (w ? barsHTML(w, 'var(--tw-water)', curHr) + axisHTML() : nodata) + '</div>';
    // hvac
    var hv = scale(M.series.hvac);
    h += '<div class="tw-sum tw-panel-box"><div class="tw-sum-h"><span class="tw-t">' + ic('snow', 'c-hvac') + ' ' + T('twHvacRuntime') + '</span></div><div class="tw-sum-v">' + (hv ? fmtNum(hv.reduce(function (x, y) { return x + y; }, 0) / 60, 1) + ' <small>h · ' + T('twToday') + '</small>' : '—') + '</div>' + (hv ? barsHTML(hv, 'var(--tw-hvac)', curHr) + axisHTML() : nodata) + '</div>';
    // status
    h += '<div class="tw-sum status tw-panel-box"><div class="tw-sum-h"><span class="tw-t">' + T('twLights') + ' / ' + T('twAcs') + ' / ' + T('twSockets') + ' / ' + T('twAlarms') + '</span></div><div class="tw-status-grid">' +
      '<div class="tw-stat">' + ic('bulb', 'c-light lg') + '<b>' + a.onL + '<small>/' + a.totL + '</small></b><small>' + T('twLights') + '</small></div>' +
      '<div class="tw-stat">' + ic('snow', 'c-hvac lg') + '<b>' + a.onH + '<small>/' + a.totH + '</small></b><small>' + T('twAcs') + '</small></div>' +
      '<div class="tw-stat">' + ic('plug', 'c-socket lg') + '<b>' + a.onS + '<small>/' + a.totS + '</small></b><small>' + T('twSockets') + '</small></div>' +
      '<div class="tw-stat ' + (a.alarms ? 'alarm' : '') + '">' + ic('alert', a.alarms ? 'c-crit lg' : 'c-muted lg') + '<b>' + a.alarms + '</b><small>' + T('twAlarms') + '</small></div></div></div>';
    $('twinBottom').innerHTML = h;
  }

  function renderEmpty() {
    var el = $('twinEmpty');
    var empty = !M.mock && (M.deviceCount === 0 && !(roomsData && roomsData.length));
    if (!empty) { el.style.display = 'none'; return; }
    el.style.display = 'flex';
    el.innerHTML = '<div class="twin-empty-card tw-panel-box">' + ic('building', 'c-accent') + '<h3 class="tw-t">' + T('twEmptyTitle') + '</h3><p class="tw-t">' + T('twEmptyDesc') + '</p><button class="tw-btn primary" data-act="mode" data-m="mock">' + T('twUseMock') + '</button></div>';
  }

  function renderAll() {
    if (!M) return;
    renderTop(); renderKpis(); renderChips(); renderRail(); renderPanel(); renderBottom(); renderEmpty();
  }

  // ---- manage modal (live building structure) ----
  function openManage() {
    var el = $('twinModal'); el.classList.add('open');
    var floors = floorsDef().map(function (f, i) { return { id: f.id, name: f.name || defaultFloorName(i) }; });
    S._draft = { floors: floors, rooms: (roomsData || []).map(function (r) { return { id: r.id, name: r.name, floor: r.floor }; }) };
    renderManage();
  }
  function renderManage() {
    var d = S._draft, h = '<div class="twin-modal-card tw-panel-box"><div class="tw-p-head"><h3 class="tw-t">' + ic('building', 'c-accent lg') + T('twManage') + '</h3><button class="tw-iconbtn" data-act="closeManage">' + ic('x') + '</button></div><div class="tw-p-body">';
    h += '<div class="c-muted tw-t" style="font-size:11.5px;line-height:1.5">' + T('twSetupHint') + '</div><div class="tw-sec-t">' + T('twFloors') + '</div>';
    d.floors.forEach(function (f, i) {
      h += '<div class="tw-row"><span class="c-muted" style="width:22px">' + (i + 1) + '</span><input class="tw-input tw-t" data-fl="' + i + '" value="' + esc(f.name) + '" placeholder="' + T('twFloorName') + '">' + (d.floors.length > 1 ? '<button class="tw-iconbtn" data-act="rmFloor" data-i="' + i + '">' + ic('trash') + '</button>' : '') + '</div>';
    });
    h += '<button class="tw-btn" data-act="addFloor" style="align-self:flex-start">' + ic('plus') + T('twAddFloor') + '</button>';
    h += '<div class="tw-sec-t">' + T('twRoomAssign') + '</div>';
    if (!d.rooms.length) h += '<div class="c-muted">—</div>';
    d.rooms.forEach(function (r, i) {
      var cur = d.floors.some(function (f) { return f.id === r.floor; }) ? r.floor : d.floors[0].id;
      h += '<div class="tw-row"><span class="tw-t" style="flex:1;font-weight:700">' + esc(nm(r.name)) + '</span><select class="tw-input" style="flex:0 0 160px" data-rm="' + i + '">' + d.floors.map(function (f) { return '<option value="' + esc(f.id) + '"' + (f.id === cur ? ' selected' : '') + '>' + esc(f.name) + '</option>'; }).join('') + '</select></div>';
    });
    h += '<div class="tw-p-actions" style="justify-content:flex-end"><button class="tw-btn" data-act="closeManage">' + T('twClose') + '</button><button class="tw-btn primary" data-act="saveManage">' + T('twSave') + '</button></div></div></div>';
    $('twinModal').innerHTML = h;
  }
  function syncDraft() {
    var d = S._draft; if (!d) return;
    document.querySelectorAll('#twinModal [data-fl]').forEach(function (i) { d.floors[+i.getAttribute('data-fl')].name = i.value; });
    document.querySelectorAll('#twinModal [data-rm]').forEach(function (s) { d.rooms[+s.getAttribute('data-rm')].floor = s.value; });
  }
  function saveManage() {
    syncDraft();
    var d = S._draft;
    S.building = { floors: d.floors.map(function (f) { return { id: f.id, name: (f.name || '').trim() || null }; }) };
    (roomsData || []).forEach(function (r) { var m = d.rooms.filter(function (x) { return x.id === r.id; })[0]; if (m) r.floor = m.floor; });
    try { saveRoomsToBackend(); } catch (e) { console.warn(e); }
    $('twinModal').classList.remove('open');
    refresh(true);
  }

  // ---- actions ----
  function toggleChannel(di, ci) {
    var rw = roomWorld(S.roomId); if (!rw) return;
    var d = rw.ro.r.devices[di]; if (!d) return; var c = d.channels[ci]; if (!c) return;
    if (M.mock) { c.state = c.state === 'ON' ? 'OFF' : 'ON'; c.kw = c.state === 'ON' ? c.nom : 0; refresh(); }
    else { try { toggleChannelState(c.nodeId, c.endpointId, c.deviceName); } catch (e) { console.warn(e); } refresh(); }
  }
  function roomAll(on) {
    var rw = roomWorld(S.roomId); if (!rw) return;
    rw.ro.r.devices.forEach(function (d) {
      d.channels.forEach(function (c) {
        if (!c.hasOnOff) return;
        var want = on ? 'ON' : 'OFF'; if (c.state === want) return;
        if (M.mock) { c.state = want; c.kw = on ? c.nom : 0; }
        else { try { toggleChannelState(c.nodeId, c.endpointId, c.deviceName); } catch (e) { console.warn(e); } }
      });
    });
    refresh();
  }
  function setMode(m) {
    if (S.mode === m) return;
    S.mode = m; localStorage.setItem(LS_MODE, m);
    S.view = 'overview'; S.roomId = null; S.floorIdx = 0;
    refresh(true);
  }
  function onShellClick(e) {
    var tgt = e.target.closest('[data-act]'); if (!tgt) return;
    var act = tgt.getAttribute('data-act');
    switch (act) {
      case 'back': goBack(); break;
      case 'overview': goOverview(); break;
      case 'floor': selectFloor(+tgt.getAttribute('data-i')); break;
      case 'card':
        if (tgt.getAttribute('data-kind') === 'floor') selectFloor(+tgt.getAttribute('data-id')); else selectRoom(tgt.getAttribute('data-id'));
        break;
      case 'view3d': S.plan = false; afterNav(); break;
      case 'viewplan': S.plan = true; afterNav(); break;
      case 'mode': setMode(tgt.getAttribute('data-m')); break;
      case 'manage': openManage(); break;
      case 'closeManage': $('twinModal').classList.remove('open'); break;
      case 'addFloor': syncDraft(); S._draft.floors.push({ id: 'f' + Date.now().toString(36), name: defaultFloorName(S._draft.floors.length) }); renderManage(); break;
      case 'rmFloor': syncDraft(); S._draft.floors.splice(+tgt.getAttribute('data-i'), 1); renderManage(); break;
      case 'saveManage': saveManage(); break;
      case 'closeRoom': selectRoom(null); break;
      case 'toggle': toggleChannel(+tgt.getAttribute('data-di'), +tgt.getAttribute('data-ci')); break;
      case 'roomAll': roomAll(tgt.getAttribute('data-on') === '1'); break;
    }
  }

  // ------------------------------------------------------------------------
  // Refresh / lifecycle
  // ------------------------------------------------------------------------
  function refresh(forceStruct) {
    if (!S.inited) return;
    var prev = M ? structSig(M) : '';
    M = S.mode === 'mock' ? buildMockModel() : buildLiveModel();
    var sig = structSig(M);
    if (S.floorIdx >= M.floors.length) { S.floorIdx = Math.max(0, M.floors.length - 1); }
    if (S.roomId && !roomWorldFromModel(S.roomId)) S.roomId = null;
    var struct = forceStruct || sig !== prev;
    if (G.renderer && struct) { buildScene(); rebuildCallouts(); applyPreset(!G.sized); G.sized = true; }
    updateCallouts(); renderAll();
  }
  function roomWorldFromModel(id) {
    for (var i = 0; i < M.floors.length; i++) for (var k = 0; k < M.floors[i].rooms.length; k++) if (M.floors[i].rooms[k].id === id) return true;
    return false;
  }

  function initDOM() {
    var shell = $('twinShell');
    shell.innerHTML =
      '<div class="twin-stage" id="twinStage"><div id="twinCanvasWrap"></div><svg id="twinLines"></svg><div id="twinCallouts"></div></div>' +
      '<div class="twin-nogl" id="twinNoGL"></div><div class="twin-top" id="twinTop"></div><div class="twin-kpis" id="twinKpis"></div>' +
      '<div class="twin-chips" id="twinChips"></div><div class="twin-rail" id="twinRail"></div>' +
      '<div class="twin-panel tw-panel-box" id="twinPanel"></div><div class="twin-bottom" id="twinBottom"></div>' +
      '<div class="twin-tip" id="twinTip"></div><div class="twin-empty" id="twinEmpty"></div><div class="twin-modal" id="twinModal"></div>';
    shell.addEventListener('click', onShellClick);
    shell.addEventListener('change', function (e) { if (e.target.matches('#twinModal [data-rm]')) syncDraft(); });
    if (window.ResizeObserver) new ResizeObserver(function () { resize(); }).observe(shell); else window.addEventListener('resize', resize);
  }

  function ensureInit() {
    if (S.inited) return true;
    initDOM();
    S.inited = true;
    var ok = initGL();
    M = S.mode === 'mock' ? buildMockModel() : buildLiveModel();
    if (ok) { resize(); buildScene(); rebuildCallouts(); applyPreset(true); G.sized = true; }
    renderAll();
    return true;
  }

  var Twin = {
    onShow: function () {
      document.body.classList.add('twin-active');
      ensureInit();
      S.visible = true;
      G.pal = G.renderer ? palette() : null;
      if (G.renderer) { resize(); G.last = 0; if (!G.raf) G.raf = requestAnimationFrame(frame); }
      refresh(!!G.renderer);
      if (S.tickTimer) clearInterval(S.tickTimer);
      S.tickTimer = setInterval(function () { if (S.mode === 'mock') { mockTick(); refresh(); } }, 3000);
    },
    onHide: function () {
      document.body.classList.remove('twin-active');
      S.visible = false;
      if (S.tickTimer) { clearInterval(S.tickTimer); S.tickTimer = null; }
    },
    onData: function () {
      if (!S.inited) return;
      if (S.mode === 'live') refresh();
    },
    onTheme: function () { if (G.renderer) G.pal = palette(); },
    applyI18n: function () { if (S.inited && M) { refresh(); } },
    getBuilding: function () { return S.building; },
    setBuilding: function (b) {
      if (b && Array.isArray(b.floors)) S.building = { floors: b.floors.filter(function (f) { return f && f.id; }).map(function (f) { return { id: String(f.id), name: f.name || null }; }) };
      if (S.inited) refresh(true);
    }
  };
  window.Twin = Twin;
})();

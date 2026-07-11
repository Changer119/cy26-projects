/* 数据轮询与面板渲染：每 60 秒自动拉取最新台风数据 */

const CITIES = [
  { name: '温州', lat: 27.994, lng: 120.699 },
  { name: '台州', lat: 28.656, lng: 121.421 },
  { name: '宁波', lat: 29.868, lng: 121.544 },
  { name: '舟山', lat: 29.985, lng: 122.208 },
  { name: '上海', lat: 31.230, lng: 121.474 },
  { name: '福州', lat: 26.074, lng: 119.297 },
];

let refreshInterval = 60;
let countdown = 60;

function $(id) { return document.getElementById(id); }

function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371, d2r = Math.PI / 180;
  const dLat = (lat2 - lat1) * d2r, dLng = (lng2 - lng1) * d2r;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * d2r) * Math.cos(lat2 * d2r) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function kv(k, v, unit) {
  return `<div class="kv"><div class="k">${k}</div><div class="v">${v ?? '--'}${unit ? ` <small>${unit}</small>` : ''}</div></div>`;
}

function renderLive(latest) {
  $('latest-time').textContent = latest.time;
  $('strong-tag').textContent = latest.strong || '--';
  $('strong-tag').style.background = strengthColor(latest.strong);
  $('power').textContent = latest.power ?? '--';
  $('live-grid').innerHTML = [
    kv('最大风速', latest.speed, 'm/s'),
    kv('中心气压', latest.pressure, 'hPa'),
    kv('移动方向', latest.move_direction || '--'),
    kv('移动速度', latest.move_speed, 'km/h'),
    kv('经度', latest.lng.toFixed(2), '°E'),
    kv('纬度', latest.lat.toFixed(2), '°N'),
  ].join('');
  $('ck-position').textContent = latest.ck_position || '';
  $('summary').textContent = latest.summary || '暂无研判信息';
}

function windRow(title, r) {
  if (!r) return '';
  const cell = (v) => `<span>${v ?? '--'}</span>`;
  return `<div class="wind-row"><div class="wind-title">${title}</div>
    <div class="wind-quads">${cell(r.ne)}${cell(r.se)}${cell(r.sw)}${cell(r.nw)}</div></div>`;
}

function renderWind(latest) {
  const html = windRow('七级风圈', latest.radius7) +
    windRow('十级风圈', latest.radius10) + windRow('十二级风圈', latest.radius12);
  $('wind-circles').innerHTML = html || '<p class="wind-empty">暂无风圈数据</p>';
}

function renderForecast(forecasts) {
  const cn = (forecasts || []).find((f) => f.agency === '中国') || (forecasts || [])[0];
  const rows = (cn ? cn.points : []).map((p) =>
    `<tr><td>${p.time.slice(5, 16)}</td><td style="color:${strengthColor(p.strong)}">${p.strong || '--'}</td>` +
    `<td>${p.power ?? '--'}级</td><td>${p.pressure ?? '--'}</td></tr>`).join('');
  document.querySelector('#forecast-table tbody').innerHTML =
    rows || '<tr><td colspan="4">暂无预报数据</td></tr>';
}

function renderCities(latest) {
  $('city-list').innerHTML = CITIES
    .map((c) => ({ ...c, d: haversineKm(latest.lat, latest.lng, c.lat, c.lng) }))
    .sort((a, b) => a.d - b.d)
    .map((c) => `<li class="${c.d < 200 ? 'near' : ''}"><span>${c.name}</span><span class="dist">${Math.round(c.d)} km</span></li>`)
    .join('');
}

function renderMeta(data) {
  const t = data.typhoon;
  const maxPower = Math.max(...t.points.map((p) => p.power || 0));
  $('meta-grid').innerHTML = [
    kv('台风编号', t.tfid),
    kv('英文名', t.enname),
    kv('起编时间', t.start_time.slice(0, 16)),
    kv('历史峰值', `${maxPower}`, '级'),
    kv('实况点数', t.points.length, '个'),
    kv('状态', t.is_active ? '活跃中' : '已停编'),
  ].join('');
  $('source').textContent = `数据来源：${data.source}`;
}

function render(data) {
  const t = data.typhoon;
  const latest = t.points[t.points.length - 1];
  if (!latest) return;
  $('title').textContent = `台风「${t.name}」实时监测大屏`;
  $('tfid-badge').textContent = `${t.tfid} ${t.enname}`;
  const active = $('active-badge');
  active.textContent = t.is_active ? '● 活跃中 LIVE' : '已停编';
  active.className = `badge badge-live ${t.is_active ? 'on' : 'off'}`;
  $('fetched-at').textContent = data.fetched_at;

  renderLive(latest);
  renderWind(latest);
  renderForecast(t.forecasts);
  renderCities(latest);
  renderMeta(data);
  renderTyphoon(data);
}

async function fetchData() {
  try {
    const resp = await fetch('/api/typhoon', { cache: 'no-store' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    refreshInterval = data.refresh_interval || 60;
    render(data);
    $('status-text').textContent = '系统状态：运行正常';
    $('status-text').className = 'ok';
  } catch (err) {
    $('status-text').textContent = `系统状态：数据获取失败（${err.message}），将自动重试`;
    $('status-text').className = 'err';
  } finally {
    countdown = refreshInterval;
  }
}

function tick() {
  const now = new Date();
  $('clock').textContent = now.toTimeString().slice(0, 8);
  countdown -= 1;
  if (countdown <= 0) {
    countdown = refreshInterval;
    fetchData();
  }
  $('countdown').textContent = Math.max(countdown, 0);
}

initMap();
fetchData();
setInterval(tick, 1000);

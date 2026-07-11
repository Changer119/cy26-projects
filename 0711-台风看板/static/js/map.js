/* 地图渲染：实况路径、预报路径、风圈、台风标记 */

const STRENGTH_COLORS = {
  '热带低压': '#22d3a5',
  '热带风暴': '#4aa8ff',
  '强热带风暴': '#ffd34d',
  '台风': '#ff9f43',
  '强台风': '#ff5c8a',
  '超强台风': '#ff3b30',
};
const AGENCY_COLORS = {
  '中国': '#ff4d4f',
  '日本': '#4aa8ff',
  '美国': '#b17aff',
  '中国台湾': '#ffd34d',
  '中国香港': '#22d3a5',
};
const WIND_STYLES = {
  radius7: { color: '#ffd34d', fill: 'rgba(255,211,77,.12)' },
  radius10: { color: '#ff9f43', fill: 'rgba(255,159,67,.16)' },
  radius12: { color: '#ff5c5c', fill: 'rgba(255,92,92,.20)' },
};

let map = null;
let trackLayer = null;
let hasFitted = false;

function strengthColor(s) { return STRENGTH_COLORS[s] || '#9aa9c0'; }

function initMap() {
  map = L.map('map', { zoomControl: false, attributionControl: false })
    .setView([27.5, 124], 6);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    { subdomains: ['1', '2', '3', '4'], className: 'dark-tiles' }
  ).addTo(map);
  trackLayer = L.layerGroup().addTo(map);
  renderLegend();
}

/* 以点为圆心、按方位角区间画扇形（用于风圈四象限） */
function sectorLatLngs(lat, lng, radiusKm, angleFrom, angleTo) {
  const pts = [[lat, lng]];
  const kmPerLat = 111.32;
  const kmPerLng = 111.32 * Math.cos((lat * Math.PI) / 180);
  for (let a = angleFrom; a <= angleTo; a += 6) {
    const rad = (a * Math.PI) / 180;
    pts.push([lat + (radiusKm * Math.cos(rad)) / kmPerLat, lng + (radiusKm * Math.sin(rad)) / kmPerLng]);
  }
  pts.push([lat, lng]);
  return pts;
}

function drawWindCircle(point, radius, style) {
  if (!radius) return;
  const quads = [
    [radius.ne, 0, 90], [radius.se, 90, 180],
    [radius.sw, 180, 270], [radius.nw, 270, 360],
  ];
  quads.forEach(([r, a0, a1]) => {
    if (!r) return;
    L.polygon(sectorLatLngs(point.lat, point.lng, r, a0, a1), {
      color: style.color, weight: 1, fillColor: style.fill, fillOpacity: 1, opacity: 0.8,
    }).addTo(trackLayer);
  });
}

function pointPopup(p) {
  return `<b>${p.time}</b><br/>强度：${p.strong || '--'}（${p.power ?? '--'}级）<br/>` +
    `风速：${p.speed ?? '--'} m/s　气压：${p.pressure ?? '--'} hPa<br/>` +
    `位置：${p.lng.toFixed(1)}°E, ${p.lat.toFixed(1)}°N`;
}

function renderTyphoon(data) {
  if (!map) initMap();
  trackLayer.clearLayers();

  const points = data.typhoon.points || [];
  if (!points.length) return;

  /* 实况路径：按强度分色的分段线 + 路径点 */
  for (let i = 1; i < points.length; i++) {
    L.polyline(
      [[points[i - 1].lat, points[i - 1].lng], [points[i].lat, points[i].lng]],
      { color: strengthColor(points[i].strong), weight: 3, opacity: 0.9 }
    ).addTo(trackLayer);
  }
  points.forEach((p) => {
    L.circleMarker([p.lat, p.lng], {
      radius: 3.5, color: strengthColor(p.strong), fillColor: strengthColor(p.strong), fillOpacity: 1, weight: 1,
    }).bindPopup(pointPopup(p)).addTo(trackLayer);
  });

  /* 各机构预报路径（虚线） */
  const latest = points[points.length - 1];
  (data.typhoon.forecasts || []).forEach((f) => {
    const color = AGENCY_COLORS[f.agency] || '#9aa9c0';
    const latlngs = [[latest.lat, latest.lng], ...f.points.map((p) => [p.lat, p.lng])];
    L.polyline(latlngs, { color, weight: 2, dashArray: '6 6', opacity: 0.85 }).addTo(trackLayer);
    f.points.forEach((p) => {
      L.circleMarker([p.lat, p.lng], { radius: 3, color, fillColor: '#0a1220', fillOpacity: 1, weight: 1.5 })
        .bindPopup(`<b>[${f.agency}预报]</b><br/>${pointPopup(p)}`).addTo(trackLayer);
    });
  });

  /* 最新点：风圈 + 旋转台风标记 */
  drawWindCircle(latest, latest.radius7, WIND_STYLES.radius7);
  drawWindCircle(latest, latest.radius10, WIND_STYLES.radius10);
  drawWindCircle(latest, latest.radius12, WIND_STYLES.radius12);
  L.marker([latest.lat, latest.lng], {
    icon: L.divIcon({ className: 'typhoon-icon', html: '<div class="eye"></div>', iconSize: [46, 46] }),
    zIndexOffset: 1000,
  }).addTo(trackLayer);

  if (!hasFitted) {
    const all = points.map((p) => [p.lat, p.lng]);
    map.fitBounds(L.latLngBounds(all).pad(0.15));
    hasFitted = true;
  }
}

function renderLegend() {
  const strengths = Object.entries(STRENGTH_COLORS)
    .map(([k, c]) => `<div><span class="legend-dot" style="background:${c}"></span>${k}</div>`).join('');
  const agencies = Object.entries(AGENCY_COLORS)
    .map(([k, c]) => `<div><span class="legend-line" style="border-color:${c}"></span>${k}预报</div>`).join('');
  document.getElementById('legend').innerHTML = strengths + '<hr style="border-color:rgba(64,120,200,.3);margin:4px 0"/>' + agencies;
}

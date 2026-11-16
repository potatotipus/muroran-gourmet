/* Leaflet 1.9.4。店舗から受け取った文字列を HTML として挿入しない。 */
(() => {
  const canvas = document.getElementById('restaurant-map');
  const payload = document.getElementById('map-data');
  const status = document.getElementById('map-status');
  if (!canvas || !payload || !status) return;
  const notice = (message) => { status.hidden = false; status.textContent = message; };
  if (!window.L) {
    notice('地図を読み込めませんでした。下の店舗リンクから詳細をご確認ください。');
    return;
  }
  try {
    const data = JSON.parse(payload.textContent);
    const map = L.map(canvas, {zoomControl: false}).setView(data.center, data.zoom);
    L.control.zoom({zoomInTitle: '拡大', zoomOutTitle: '縮小'}).addTo(map);
    map.on('popupopen', (event) => {
      const close = event.popup.getElement().querySelector('.leaflet-popup-close-button');
      if (close) close.setAttribute('aria-label', '閉じる');
    });
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    let failures = 0;
    let loaded = 0;
    tiles.on('tileerror', () => {
      failures += 1;
      notice('背景地図を読み込めませんでした。通信状況をご確認ください。店舗ピンと下の店舗リンクは引き続き利用できます。');
    });
    tiles.on('tileload', () => { loaded += 1; });
    tiles.on('load', () => { if (!failures && loaded) status.hidden = true; });
    tiles.addTo(map);
    const bounds = [];
    for (const store of data.stores) {
      const pin = document.createElement('span');
      const color = ['red', 'green', 'blue'].includes(store.color) ? store.color : 'blue';
      pin.className = `map-pin-dot pin-${color}`;
      const icon = L.divIcon({html: pin, className: 'store-map-marker', iconSize: [44, 48], iconAnchor: [22, 44]});
      const marker = L.marker([store.latitude, store.longitude], {icon, title: store.name, keyboard: true}).addTo(map);
      marker.getElement().setAttribute('aria-label', `${store.name}の店舗ピン`);
      const popup = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = store.name;
      popup.append(title);
      const summary = document.createElement('p');
      summary.textContent = store.description;
      popup.append(summary);
      const flags = document.createElement('p');
      flags.textContent = [store.is_demo ? '架空のデモ店舗・位置' : '', store.is_favorite ? 'お気に入り' : '', store.is_visited ? '訪問済み（自己申告）' : '未訪問'].filter(Boolean).join(' / ');
      popup.append(flags);
      const link = document.createElement('a');
      link.href = store.detail_url;
      link.textContent = '店舗詳細を見る';
      link.className = 'map-popup-link';
      popup.append(link);
      marker.bindPopup(popup, {maxWidth: 250, autoPanPadding: [20, 20]});
      bounds.push([store.latitude, store.longitude]);
    }
    if (bounds.length === 1) map.setView(bounds[0], 16);
    else if (bounds.length > 1) map.fitBounds(bounds, {padding: [36, 36], maxZoom: 15});
    setTimeout(() => { if (!loaded) notice('背景地図を取得できませんでした。通信状況をご確認ください。下の店舗リンクからも詳細をご覧いただけます。'); }, 8000);
  } catch (error) {
    notice('地図を表示できませんでした。下の店舗リンクをご利用ください。');
  }
})();

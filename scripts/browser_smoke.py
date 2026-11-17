"""任意の実ブラウザ検証。既存DBを変更せず、一時DBのサーバーを起動する。

依存: requirements-dev.txt、Playwright Chromium（または MURORAN_CHROMIUM_PATH）。
外部地図の可否は機能テストと区別して report.json に記録する。
"""

import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run_checks(root, artifacts, tile_mode):
    errors = []
    report = {'real_osm_loaded': None, 'real_osm_screens': {}, 'tile_mode': tile_mode,
              'functional_flow': False, 'viewport_checks': []}
    fixture = BytesIO()
    Image.new('RGB', (256, 256), '#edeae3').save(fixture, 'PNG')
    with sync_playwright() as playwright:
        executable = os.environ.get('MURORAN_CHROMIUM_PATH') or shutil.which('chromium')
        launch_options = {'headless': True}
        if executable:
            launch_options['executable_path'] = executable
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
        if proxy:
            launch_options['proxy'] = {'server': proxy, 'bypass': os.environ.get('NO_PROXY', '127.0.0.1,localhost')}
        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(viewport={'width': 390, 'height': 844})
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on('pageerror', lambda error: errors.append(str(error)))

        def fixture_tiles(route):
            route.fulfill(status=200, content_type='image/png', body=fixture.getvalue())

        if tile_mode == 'fixture':
            page.route('https://tile.openstreetmap.org/**', fixture_tiles)

        def shot(name):
            page.screenshot(path=str(artifacts / f'{name}.png'), full_page=True)

        def check_real_map(screen):
            if tile_mode != 'auto':
                return
            all_tiles_loaded = """() => {
                const tiles = [...document.querySelectorAll('.leaflet-tile')];
                return tiles.length > 0 && tiles.every(tile => tile.complete && tile.naturalWidth > 0);
            }"""
            page.wait_for_function("""() => {
                const tiles = [...document.querySelectorAll('.leaflet-tile')];
                return (tiles.length > 0 && tiles.every(tile => tile.complete && tile.naturalWidth > 0))
                    || document.getElementById('map-status').textContent.includes('背景地図');
            }""", timeout=15000)
            report['real_osm_screens'][screen] = page.evaluate(all_tiles_loaded)
            report['real_osm_loaded'] = len(report['real_osm_screens']) == 3 and all(report['real_osm_screens'].values())

        def nav(name):
            page.get_by_role('navigation', name='メインナビゲーション').get_by_role('link', name=name, exact=True).click()

        def logout():
            page.locator('.site-header').get_by_role('button', name='ログアウト', exact=True).click()

        def login(email='browser@example.test', password='Smoke-Only!426'):
            page.get_by_label(re.compile('^メールアドレス')).fill(email)
            page.get_by_label(re.compile('^パスワード')).fill(password)
            page.get_by_role('button', name='ログイン', exact=True).click()

        page.goto(root + '/', wait_until='load')
        shot('01-top')
        page.get_by_role('link', name='ログイン', exact=True).click()
        shot('02-login')
        login(password='wrong-password')
        assert page.get_by_role('alert').is_visible()
        login()
        page.wait_for_url('**/accounts/choose/')
        shot('04-choose')
        page.get_by_role('link', name=re.compile('ジャンルから探す')).click()
        shot('05-genres')
        page.get_by_role('link', name='すべて', exact=True).click()
        assert page.locator('.restaurant-card').count() == 10
        shot('06-list')
        page.get_by_role('link', name=re.compile('条件で絞り込む')).click()
        page.get_by_label(re.compile('^店舗名・キーワード')).fill('サンプルカレー店02')
        page.get_by_label(re.compile('^予算')).select_option('1000')
        page.get_by_label(re.compile('^ジャンル')).select_option('curry')
        page.get_by_label(re.compile('^エリア')).select_option('中島')
        page.get_by_label('テイクアウト', exact=True).check()
        shot('07-filters')
        page.get_by_role('button', name='この条件で検索').click()
        assert page.locator('.restaurant-card').count() == 1
        filtered_query = parse_qs(urlsplit(page.url).query)
        page.get_by_role('link', name='地図で見る', exact=True).click()
        page.wait_for_selector('.store-map-marker')
        check_real_map('08')
        shot('08-map-real-or-error')
        page.get_by_role('button', name='サンプルカレー店02の店舗ピン', exact=True).click()
        page.get_by_role('link', name='店舗詳細を見る', exact=True).click()
        assert page.get_by_role('heading', name='サンプルカレー店02', exact=True).is_visible()
        store_path = urlsplit(page.url).path
        detail_url = page.url
        shot('09-detail')
        page.get_by_role('link', name='地図を見る', exact=True).click()
        page.wait_for_selector('.store-map-marker')
        place_url = page.get_by_role('link', name='Googleマップで開く（外部サイト）').get_attribute('href')
        assert parse_qs(urlsplit(place_url).query)['api'] == ['1']
        check_real_map('10')
        shot('10-store-map-real-or-error')
        page.get_by_role('link', name='← 店舗詳細へ').click()
        assert page.url == detail_url
        page.get_by_role('link', name='地図を見る', exact=True).click()
        page.get_by_role('button', name='サンプルカレー店02の店舗ピン', exact=True).click()
        page.get_by_role('link', name='店舗詳細を見る', exact=True).click()
        assert page.url == detail_url
        page.get_by_role('link', name='← 地図に戻る', exact=True).click()
        assert urlsplit(page.url).path == '/maps/search/'
        assert parse_qs(urlsplit(page.url).query) == filtered_query
        page.get_by_role('button', name='サンプルカレー店02の店舗ピン', exact=True).click()
        page.get_by_role('link', name='店舗詳細を見る', exact=True).click()
        report['search_context_preserved'] = True
        page.get_by_role('link', name='バスで行く', exact=True).click()
        for name, mode in [('公共交通機関の経路を確認（Googleマップ）', 'transit'), ('徒歩の経路を確認（Googleマップ）', 'walking')]:
            url = page.get_by_role('link', name=name, exact=True).get_attribute('href')
            assert parse_qs(urlsplit(url).query)['travelmode'] == [mode]
        shot('11-directions')
        page.get_by_role('link', name='← 店舗詳細へ').click()
        page.get_by_role('link', name='口コミを投稿する', exact=True).click()
        page.get_by_label(re.compile('^評価')).select_option('5')
        page.get_by_role('textbox', name=re.compile('^口コミ')).fill('また行きたいです。<img src=x onerror=window.REVIEW_XSS=true>')
        shot('12-review')
        page.get_by_role('button', name='投稿する', exact=True).click()
        assert '5.0' in page.locator('.reviews-section').inner_text()
        assert page.evaluate('window.REVIEW_XSS !== true')
        page.get_by_role('link', name='編集する', exact=True).click()
        page.get_by_label(re.compile('^評価')).select_option('3')
        page.get_by_role('textbox', name=re.compile('^口コミ')).fill('編集後の口コミです。')
        page.get_by_role('button', name='更新する', exact=True).click()
        assert '3.0' in page.locator('.reviews-section').inner_text()
        page.get_by_role('button', name='お気に入りに追加', exact=True).click()
        page.get_by_role('button', name='訪問済みに登録', exact=True).click()
        page.wait_for_url('**/maps/mine/')
        data = json.loads(page.locator('#map-data').text_content())
        assert len(data['stores']) == 1 and data['stores'][0]['is_visited']
        check_real_map('16')
        shot('16-personal-map-real-or-error')
        report['visit_registration_opens_personal_map'] = True
        # 実背景を08・10・16で確認後、多数の画面検証には固定画像を使う。
        if tile_mode == 'auto':
            page.route('https://tile.openstreetmap.org/**', fixture_tiles)
        nav('スタンプ')
        assert page.locator('.summary-grid strong').all_text_contents() == ['1', '1', '10']
        shot('13-stamps')
        nav('お気に入り')
        assert page.locator('.restaurant-card').count() == 1
        shot('14-favorites')
        page.get_by_role('button', name='お気に入りを解除', exact=True).click()
        assert page.get_by_text('お気に入りはまだありません。', exact=True).is_visible()
        page.goto(root + '/restaurants/?q=サンプルカレー店02', wait_until='load')
        page.get_by_role('button', name='お気に入りに追加', exact=True).click()
        nav('マイページ')
        assert page.locator('.summary-grid strong').all_text_contents() == ['1', '1', '10']
        assert page.get_by_text('他の利用者だけの履歴', exact=False).count() == 0
        shot('15-profile')
        page.get_by_role('link', name='自分のマップ', exact=True).click()
        data = json.loads(page.locator('#map-data').text_content())
        assert len(data['stores']) == 1
        assert data['stores'][0]['color'] == 'red'
        assert data['stores'][0]['is_visited'] and data['stores'][0]['is_favorite']
        page.wait_for_selector('.store-map-marker')
        page.get_by_role('button', name='サンプルカレー店02の店舗ピン', exact=True).click()
        assert 'お気に入り' in page.locator('.leaflet-popup-content').inner_text()
        assert '訪問済み' in page.locator('.leaflet-popup-content').inner_text()
        shot('16-personal-map-fixture')
        page.get_by_role('link', name='店舗詳細を見る', exact=True).click()
        assert page.get_by_role('link', name='← 自分のマップに戻る').count() == 1
        page.get_by_role('button', name='訪問済み登録を解除', exact=True).click()
        nav('スタンプ')
        assert page.locator('.summary-grid strong').all_text_contents() == ['0', '0', '0']
        page.goto(root + store_path, wait_until='load')
        page.get_by_role('link', name='削除する', exact=True).click()
        page.get_by_role('button', name='削除する', exact=True).click()
        assert page.get_by_text('まだ口コミがありません', exact=True).is_visible()
        page.get_by_role('link', name='店舗情報の通報・修正提案').click()
        page.get_by_label(re.compile('^通報・修正提案')).fill('デモ情報の確認をお願いします。')
        page.get_by_role('button', name='管理者へ送信する').click()
        assert page.get_by_role('heading', name='サンプルカレー店02', exact=True).is_visible()
        nav('マイページ')
        page.get_by_role('link', name='プロフィール編集', exact=True).click()
        page.get_by_label(re.compile('^ユーザー名')).fill('変更した表示名')
        page.get_by_label(re.compile('^メールアドレス')).fill('updated-browser@example.test')
        page.get_by_label(re.compile('^現在のパスワード')).fill('Smoke-Only!426')
        page.get_by_role('button', name='変更を保存する').click()
        assert page.locator('.profile-info').get_by_text('変更した表示名', exact=True).is_visible()
        logout()
        page.get_by_role('link', name='ログイン', exact=True).click()
        login(email='updated-browser@example.test')
        page.wait_for_url('**/accounts/choose/')
        print('PASS: login/search/map/popup/routes/review CRUD/favorite from detail and card/visit add-remove/points/profile/email/report/privacy', flush=True)

        # エラー時の画面も確認。成功用の固定画像とは別に通信断を模擬する。
        failed = context.new_page()
        failed.route('https://tile.openstreetmap.org/**', lambda route: route.abort())
        failed.goto(root + '/maps/search/', wait_until='load')
        failed.wait_for_function("document.getElementById('map-status').textContent.includes('背景地図')")
        assert failed.locator('.store-map-marker').count() == 10
        assert failed.locator('.map-store-links a').count() == 10
        failed.screenshot(path=str(artifacts / 'map-offline-fallback.png'), full_page=True)
        failed.close()

        urls = ['/accounts/choose/', '/restaurants/genres/', '/restaurants/', '/restaurants/filters/',
                '/maps/search/', store_path, '/maps/stores/2/', '/maps/stores/2/directions/',
                '/community/stores/2/reviews/new/', '/visits/stamps/', '/community/favorites/',
                '/accounts/profile/', '/maps/mine/']
        for width, height in [(320, 780), (390, 844), (768, 1024), (1440, 1000)]:
            page.set_viewport_size({'width': width, 'height': height})
            for path in urls:
                response = page.goto(root + path, wait_until='load')
                assert response.status == 200, path
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
                assert page.locator('nav [aria-current="page"]').count() == 1, path
                assert page.locator('nav a').count() == 5
            report['viewport_checks'].append({'width': width, 'private_screens': len(urls)})
            print(f'PASS {width}px: 13 private screens, 5 navigation links, current location, no horizontal overflow', flush=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        logout()
        for path in urls:
            page.goto(root + path, wait_until='load')
            assert '/accounts/login/' in page.url, path
        page.goto(root + '/accounts/signup/', wait_until='load')
        page.get_by_label(re.compile('^ユーザー名')).fill('新規登録の確認')
        page.get_by_label(re.compile('^メールアドレス')).fill('new-browser@example.test')
        page.locator('#id_password1').fill('NewAccount-Only!426')
        page.locator('#id_password2').fill('NewAccount-Only!426')
        shot('03-signup')
        page.get_by_role('button', name='登録する', exact=True).click()
        page.wait_for_url('**/accounts/choose/')
        nav('お気に入り')
        assert page.locator('.restaurant-card').count() == 0
        nav('スタンプ')
        assert page.locator('.summary-grid strong').all_text_contents() == ['0', '0', '0']
        page.goto(root + '/maps/mine/', wait_until='load')
        assert json.loads(page.locator('#map-data').text_content())['stores'] == []
        assert not errors, errors
        report['functional_flow'] = True
        print('PASS: anonymous restrictions, signup, per-user empty state, offline fallback; no page errors', flush=True)
        context.close()
        browser.close()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', type=Path, default=Path(tempfile.gettempdir()) / 'muroran-browser-artifacts')
    parser.add_argument('--tile-mode', choices=['auto', 'fixture'], default='auto')
    parser.add_argument('--require-osm', action='store_true')
    options = parser.parse_args()
    options.artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='muroran-browser-') as temporary:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        environment = os.environ.copy()
        environment.update(MURORAN_SMOKE_DIRECTORY=temporary, MURORAN_SMOKE_PORT=str(port), PYTHONIOENCODING='utf-8')
        candidates = [ROOT / '.venv/Scripts/python.exe', ROOT / '.venv/bin/python']
        python = next((str(path) for path in candidates if path.exists()), sys.executable)
        with (options.artifacts / 'server.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([python, str(ROOT / 'scripts/smoke_server.py')], cwd=ROOT, env=environment, stdout=log, stderr=log)
            try:
                for _ in range(180):
                    if process.poll() is not None:
                        raise RuntimeError('検証サーバーの起動失敗。server.log を確認してください。')
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=.2):
                            break
                    except OSError:
                        time.sleep(.25)
                else:
                    raise RuntimeError('検証サーバー起動待ちがタイムアウトしました。')
                report = run_checks(f'http://127.0.0.1:{port}', options.artifacts, options.tile_mode)
                report['migration_preserved'] = 'MIGRATION_PRESERVATION_OK' in (options.artifacts / 'server.log').read_text(encoding='utf-8')
                assert report['migration_preserved']
                (options.artifacts / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps(report, ensure_ascii=False), flush=True)
                if options.require_osm:
                    assert report['real_osm_loaded'] is True, '実際のOpenStreetMapタイルを取得できませんでした。'
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main()

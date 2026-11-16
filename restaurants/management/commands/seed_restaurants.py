"""架空の10店舗を追加する。再実行時に既存データは上書きしない。"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from restaurants.catalog import GENRES, TAGS
from restaurants.models import Genre, Restaurant, Tag

DEMO_STORES = [
    ('食堂', 'set-meal', '高砂', 450, 500, ['one-coin', 'cheap', 'large', 'solo'], '日替わり定食', '11:00〜20:00'),
    ('カレー店', 'curry', '中島', 600, 850, ['large', 'takeout'], '特製カレー', '11:00〜19:00'),
    ('ラーメン店', 'ramen', '高砂', 500, 1000, ['cheap', 'large', 'solo'], 'しょうゆラーメン', '11:00〜21:00'),
    ('やきとり店', 'izakaya', '本町', 700, 1200, ['late-night', 'takeout'], 'やきとり盛り合わせ', '17:00〜24:00'),
    ('カフェ', 'cafe', '東町', 350, 500, ['one-coin', 'solo', 'takeout'], '手作りプリン', '10:00〜18:00'),
    ('洋食店', 'western', '中島', 800, 1500, ['solo'], 'オムライス', '11:00〜20:00'),
    ('レストラン', 'western', '祝津', 1100, 1800, [], '季節のパスタ', '11:00〜20:00'),
    ('居酒屋', 'izakaya', '輪西', 900, 1300, ['late-night', 'solo'], 'おつまみセット', '17:00〜23:00'),
    ('食堂', 'set-meal', '本町', 400, 800, ['cheap', 'large', 'takeout'], '大盛り焼きそば', '11:00〜19:00'),
    ('喫茶店', 'cafe', '高砂', None, None, ['solo'], 'メニュー準備中', ''),
]


class Command(BaseCommand):
    help = '架空のデモ店舗10件を投入します。再実行しても重複・上書きしません。'

    @transaction.atomic
    def handle(self, *args, **options):
        genres = {slug: Genre.objects.get_or_create(slug=slug, defaults={'name': name, 'sort_order': i})[0]
                  for i, (slug, name) in enumerate(GENRES)}
        tags = {slug: Tag.objects.get_or_create(slug=slug, defaults={'name': name, 'sort_order': i})[0]
                for i, (slug, name) in enumerate(TAGS)}
        created_count = 0
        for i, (kind, genre, area, low, high, features, menu, hours) in enumerate(DEMO_STORES, start=1):
            restaurant, created = Restaurant.objects.get_or_create(
                demo_key=f'muroran-sample-{i:02}',
                defaults={
                    'name': f'サンプル{kind}{i:02}',
                    'description': '架空のデモ店舗です。住所・位置・営業時間・価格・メニューは実在のお店の情報ではありません。'
                                   f' {menu}を試しに検索してみてください。',
                    'address': f'室蘭市{area} サンプル区画{i:02}（架空の住所）',
                    'area': area,
                    'latitude': Decimal('42.330000') + Decimal((i - 1) // 3) * Decimal('0.006000'),
                    'longitude': Decimal('140.980000') + Decimal((i - 1) % 3) * Decimal('0.008000'),
                    'genre': genres[genre], 'price_min': low, 'price_max': high,
                    'opening_hours': f'{hours}（デモ）' if hours else '',
                    'closed_days': '水曜日（デモ）',
                    'owner_description': '街の食事の時間を大切にしたい、という架空の紹介文です。',
                    'recommended_menu': f'{menu}（デモメニュー）',
                },
            )
            if created:
                restaurant.tags.set([tags[slug] for slug in features])
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f'デモ店舗: {created_count}件追加、{len(DEMO_STORES) - created_count}件は既存のため維持しました。'))

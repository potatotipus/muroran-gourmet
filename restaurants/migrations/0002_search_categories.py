from django.db import migrations


def create_categories(apps, schema_editor):
    # マイグレーションは将来の catalog.py の変更に影響されない固定値を使う。
    categories = {
        'Genre': [('ramen', 'ラーメン'), ('curry', 'カレー'), ('set-meal', '定食屋'),
                  ('izakaya', 'やきとり・居酒屋'), ('cafe', 'カフェ・スイーツ'), ('western', '洋食')],
        'Tag': [('one-coin', 'ワンコイン'), ('cheap', '激安'), ('large', '大盛り'),
                ('solo', '一人でも入りやすい'), ('late-night', '夜遅くまで営業'), ('takeout', 'テイクアウト')],
    }
    for model_name, values in categories.items():
        model = apps.get_model('restaurants', model_name)
        for order, (slug, name) in enumerate(values):
            model.objects.using(schema_editor.connection.alias).get_or_create(
                slug=slug, defaults={'name': name, 'sort_order': order},
            )


class Migration(migrations.Migration):
    dependencies = [('restaurants', '0001_initial')]
    operations = [migrations.RunPython(create_categories, migrations.RunPython.noop)]

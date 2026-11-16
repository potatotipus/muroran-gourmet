"""店舗検索・詳細・データ整合性・管理画面・デモ投入の回帰テスト。"""

from decimal import Decimal
from html.parser import HTMLParser
from io import BytesIO, StringIO
import tempfile
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import RestaurantAdminForm
from .models import Genre, Restaurant, Tag


class LinkParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))


class RestaurantSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='search@example.test', password='Walk!Muroran426')
        cls.ramen = Genre.objects.get(slug='ramen')
        cls.curry = Genre.objects.get(slug='curry')
        cls.a = Restaurant.objects.create(name='検索食堂A', genre=cls.ramen, area='高砂',
                                          price_min=400, price_max=500, description='あっさりスープ',
                                          recommended_menu='しょうゆ麺', opening_hours='11:00〜20:00')
        cls.a.tags.set(Tag.objects.filter(slug__in=['one-coin', 'cheap', 'solo']))
        cls.b = Restaurant.objects.create(name='検索食堂B', genre=cls.curry, area='中島',
                                          price_min=600, price_max=1000, description='辛口スパイス',
                                          owner_description='地元への思い', address='中島テスト区画',
                                          recommended_menu='特製カレー', opening_hours='11:00〜23:00')
        cls.b.tags.set(Tag.objects.filter(slug__in=['cheap', 'large', 'takeout', 'late-night']))
        cls.c = Restaurant.objects.create(name='検索食堂C', genre=cls.ramen, area='高砂',
                                          price_min=500, price_max=2000)
        cls.c.tags.set(Tag.objects.filter(slug__in=['large', 'solo', 'late-night']))
        cls.d = Restaurant.objects.create(name='情報準備中D', area='輪西')

    def setUp(self):
        self.client.force_login(self.user)

    def results(self, **params):
        response = self.client.get(reverse('restaurants:list'), params)
        self.assertEqual(response.status_code, 200)
        return response, list(response.context['restaurants'])

    def test_login_can_reach_genre_screen_through_selection(self):
        self.client.logout()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'search@example.test', 'password': 'Walk!Muroran426',
        }, follow=True)
        self.assertContains(response, f'href="{reverse("restaurants:genres")}"')
        response = self.client.get(reverse('restaurants:genres'))
        for label in ['すべて', 'ラーメン', 'カレー', '定食屋', 'やきとり・居酒屋', 'カフェ・スイーツ', '洋食', 'ワンコイン', '激安大盛り']:
            self.assertContains(response, label)
        self.assertContains(response, '?tags=cheap&amp;tags=large')

    def test_all_lists_every_registered_store_with_a_count(self):
        response, stores = self.results()
        self.assertEqual(stores, [self.d, self.a, self.b, self.c])
        self.assertEqual(response.context['result_count'], 4)
        for store in stores:
            self.assertContains(response, store.name)
            self.assertContains(response, store.get_absolute_url())
        self.assertContains(response, '500円')

    def test_genre_filter_returns_matching_stores(self):
        _, stores = self.results(genre='ramen')
        self.assertEqual(stores, [self.a, self.c])

    def test_one_coin_is_a_tag_not_a_genre(self):
        _, stores = self.results(tags=['one-coin'])
        self.assertEqual(stores, [self.a])
        self.assertFalse(Genre.objects.filter(slug='one-coin').exists())
        self.assertEqual(self.a.genre, self.ramen)

    def test_cheap_large_requires_both_tags(self):
        _, stores = self.results(tags=['cheap', 'large'])
        self.assertEqual(stores, [self.b])

    def test_keyword_matches_names_menus_descriptions_genres_addresses_and_tags(self):
        for keyword, expected in [
            ('食堂B', [self.b]), ('特製', [self.b]), ('辛口', [self.b]),
            ('ラーメン', [self.a, self.c]), ('区画', [self.b]), ('地元', [self.b]),
            ('テイクアウト', [self.b]),
        ]:
            with self.subTest(keyword=keyword):
                _, stores = self.results(q=keyword)
                self.assertEqual(stores, expected)

    def test_multiple_keywords_can_match_different_fields(self):
        _, stores = self.results(q='辛口 大盛り')
        self.assertEqual(stores, [self.b])

    def test_multiple_keywords_can_match_different_tags(self):
        _, stores = self.results(q='激安 大盛り')
        self.assertEqual(stores, [self.b])

    def test_many_keywords_do_not_exceed_sqlite_join_limit(self):
        _, stores = self.results(q='食 ' * 45)
        self.assertEqual(stores, [self.a, self.b, self.c])

    def test_joined_tag_keyword_does_not_duplicate_results(self):
        response, stores = self.results(q='食堂')
        self.assertEqual(stores, [self.a, self.b, self.c])
        self.assertEqual(response.context['result_count'], 3)

    def test_budget_checks_known_upper_bound_not_minimum(self):
        for limit, expected in [('500', [self.a]), ('1000', [self.a, self.b]), ('1500', [self.a, self.b])]:
            with self.subTest(limit=limit):
                _, stores = self.results(budget=limit)
                self.assertEqual(stores, expected)

    def test_combined_search_applies_every_condition(self):
        _, stores = self.results(q='辛口', genre='curry', budget='1000', area='中島', tags=['cheap', 'large'])
        self.assertEqual(stores, [self.b])
        _, stores = self.results(q='辛口', genre='curry', area='高砂')
        self.assertEqual(stores, [])

    def test_additional_muroran_areas_are_selectable(self):
        response = self.client.get(reverse('restaurants:filters'))
        self.assertContains(response, '<option value="輪西">輪西</option>', html=True)
        _, stores = self.results(area='輪西')
        self.assertEqual(stores, [self.d])

    def test_late_night_requires_recorded_hours_and_does_not_claim_open_now(self):
        response, stores = self.results(tags=['late-night'])
        self.assertEqual(stores, [self.b])
        response = self.client.get(self.b.get_absolute_url())
        self.assertContains(response, '現在の営業状況を示すものではありません')
        self.assertNotContains(response, '現在営業中')

    def test_invalid_search_values_show_errors_without_returning_all_stores(self):
        for params in [{'genre': 'missing'}, {'budget': 'invalid'}, {'tags': ['missing']},
                       {'q': 'a' * 101}, {'area': '未登録エリア'}]:
            with self.subTest(params=params):
                response, stores = self.results(**params)
                self.assertEqual(stores, [])
                self.assertTrue(response.context['form'].errors)
                self.assertContains(response, '検索条件をご確認ください。')

    def test_empty_results_explain_how_to_retry(self):
        response, stores = self.results(q='一致しないキーワード')
        self.assertEqual(stores, [])
        self.assertContains(response, '一致するお店が見つかりませんでした。')
        self.assertContains(response, 'すべてのお店を見る')

    def test_filters_and_details_preserve_all_search_parameters(self):
        params = {'q': '辛口', 'budget': '1000', 'genre': 'curry', 'area': '中島', 'tags': ['cheap', 'large']}
        response, _ = self.results(**params, next='https://example.invalid/')
        links = LinkParser(response.content.decode()).links
        filter_link = next(link for link in links if urlsplit(link).path == reverse('restaurants:filters'))
        detail_link = next(link for link in links if urlsplit(link).path == self.b.get_absolute_url())
        for link in [filter_link, detail_link]:
            query = parse_qs(urlsplit(link).query)
            self.assertEqual(query, {key: value if isinstance(value, list) else [value] for key, value in params.items()})
        response = self.client.get(filter_link)
        form = response.context['form']
        for field, value in params.items():
            self.assertEqual(form[field].value(), value)
        self.assertContains(response, f'action="{reverse("restaurants:list")}"')
        self.assertContains(response, f'href="{reverse("restaurants:filters")}"')
        response = self.client.get(detail_link)
        back = next(link for link in LinkParser(response.content.decode()).links
                    if urlsplit(link).path == reverse('restaurants:list'))
        self.assertEqual(parse_qs(urlsplit(back).query), parse_qs(urlsplit(detail_link).query))

    def test_quick_search_retains_other_selected_conditions(self):
        response, _ = self.results(budget='1000', area='中島', tags=['cheap', 'large'])
        for name, value in [('budget', '1000'), ('area', '中島'), ('tags', 'cheap'), ('tags', 'large')]:
            self.assertContains(response, f'<input type="hidden" name="{name}" value="{value}">', html=True)

    def test_reset_clears_every_condition(self):
        _, stores = self.results(genre='ramen', tags=['large'])
        self.assertEqual(stores, [self.c])
        response, stores = self.results()
        self.assertEqual(len(stores), 4)
        self.assertFalse(response.context['query_string'])
        response = self.client.get(reverse('restaurants:filters'))
        self.assertFalse(response.context['form']['tags'].value())

    def test_detail_displays_selected_store_and_handles_missing_data(self):
        response = self.client.get(self.b.get_absolute_url())
        for value in ['検索食堂B', '辛口スパイス', '中島テスト区画', '11:00〜23:00', '地元への思い', '特製カレー', '600〜1,000円']:
            self.assertContains(response, value)
        response = self.client.get(self.d.get_absolute_url())
        self.assertContains(response, '未登録')
        self.assertContains(response, 'placeholder.svg')

    def test_missing_store_returns_404(self):
        self.assertEqual(self.client.get(reverse('restaurants:detail', args=[999999])).status_code, 404)

    def test_store_actions_connect_to_maps_reviews_and_favorites(self):
        response = self.client.get(self.a.get_absolute_url())
        self.assertContains(response, reverse('maps:store', args=[self.a.pk]))
        self.assertContains(response, reverse('maps:directions', args=[self.a.pk]))
        self.assertContains(response, reverse('community:review_create', args=[self.a.pk]))
        self.assertContains(response, reverse('community:favorite_update', args=[self.a.pk]))
        self.assertNotContains(response, 'type="button" disabled')

    def test_store_content_and_search_queries_are_escaped(self):
        self.a.name = '<script>alert(1)</script>'
        self.a.description = '<img src=x onerror=alert(1)>'
        self.a.save()
        response = self.client.get(self.a.get_absolute_url())
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')
        response, _ = self.results(q='" onfocus="alert(1)')
        self.assertNotContains(response, 'value="" onfocus=')

    def test_all_restaurant_screens_require_login_and_share_navigation(self):
        urls = [reverse('restaurants:genres'), reverse('restaurants:list'), reverse('restaurants:filters'), self.a.get_absolute_url()]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'includes/bottom_nav.html')
                self.assertContains(response, 'aria-current="page"', count=1)
                self.assertIn('no-store', response.headers['Cache-Control'])
        self.client.logout()
        for url in urls:
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)


class RestaurantDataTests(TestCase):
    def test_model_rejects_invalid_prices_coordinates_and_partial_location(self):
        for data in [{'price_min': 1000, 'price_max': 500}, {'price_min': -1},
                     {'latitude': 91, 'longitude': 140}, {'latitude': 42, 'longitude': 181}, {'latitude': 42}]:
            with self.subTest(data=data):
                with self.assertRaises(ValidationError):
                    Restaurant(name='検証用', **data).full_clean()

    def test_database_constraints_also_protect_direct_writes(self):
        for data in [{'price_min': 1000, 'price_max': 500}, {'latitude': 91, 'longitude': 140}, {'latitude': 42}]:
            with self.subTest(data=data):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Restaurant.objects.create(name='不正データ', **data)

    def test_valid_optional_data_and_coordinates(self):
        Restaurant(name='情報未登録').full_clean()
        restaurant = Restaurant(name='位置登録', latitude=Decimal('42.330000'), longitude=Decimal('140.980000'))
        restaurant.full_clean()
        restaurant.save()
        restaurant.refresh_from_db()
        self.assertEqual(restaurant.latitude, Decimal('42.330000'))

    def test_genre_deletion_cannot_orphan_a_store(self):
        genre = Genre.objects.get(slug='ramen')
        Restaurant.objects.create(name='分類保持', genre=genre)
        with self.assertRaises(ProtectedError):
            genre.delete()

    def test_price_labels_cover_partial_and_empty_ranges(self):
        for data, label in [({}, '予算未登録'), ({'price_min': 0}, '0円〜'),
                            ({'price_max': 1500}, '〜1,500円'),
                            ({'price_min': 500, 'price_max': 500}, '500円')]:
            with self.subTest(data=data):
                self.assertEqual(Restaurant(**data).price_label, label)

    def test_missing_image_file_uses_placeholder_and_can_still_be_edited(self):
        restaurant = Restaurant(name='画像準備中', image='restaurants/missing.png')
        self.assertTrue(restaurant.image_url.endswith('placeholder.svg'))
        restaurant.full_clean()

    def test_seed_is_idempotent_and_preserves_admin_edits_and_non_demo_stores(self):
        normal = Restaurant.objects.create(name='通常登録のお店')
        call_command('seed_restaurants', stdout=StringIO())
        self.assertEqual(Restaurant.objects.count(), 11)
        sample = Restaurant.objects.get(demo_key='muroran-sample-01')
        sample.name = '管理画面で変更した名前'
        sample.save()
        sample.tags.clear()
        call_command('seed_restaurants', stdout=StringIO())
        sample.refresh_from_db()
        self.assertEqual(Restaurant.objects.count(), 11)
        self.assertEqual(sample.name, '管理画面で変更した名前')
        self.assertEqual(sample.tags.count(), 0)
        self.assertTrue(Restaurant.objects.filter(pk=normal.pk).exists())
        self.assertEqual(Genre.objects.count(), 6)
        self.assertEqual(Tag.objects.count(), 6)
        self.assertEqual(Restaurant.objects.filter(demo_key__isnull=False).count(), 10)

    def test_demo_details_are_marked_as_fiction(self):
        call_command('seed_restaurants', stdout=StringIO())
        self.client.force_login(get_user_model().objects.create_user(username='demo-reader'))
        response = self.client.get(Restaurant.objects.get(demo_key='muroran-sample-01').get_absolute_url())
        self.assertContains(response, '架空のデモ店舗です。')
        self.assertContains(response, '実際のお店の情報ではありません。')


class RestaurantAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin', 'admin@example.test', 'Admin-Only!426')
        cls.member = get_user_model().objects.create_user('member')

    def test_admin_requires_staff_privileges(self):
        url = reverse('admin:restaurants_restaurant_add')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_can_add_and_update_a_store_with_image_and_tags(self):
        self.client.force_login(self.admin)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            content = BytesIO()
            Image.new('RGB', (8, 8), 'green').save(content, format='PNG')
            image = SimpleUploadedFile('store.png', content.getvalue(), content_type='image/png')
            response = self.client.post(reverse('admin:restaurants_restaurant_add'), {
                'name': '管理登録テスト', 'genre': Genre.objects.get(slug='ramen').pk,
                'area': '高砂', 'price_min': 500, 'price_max': 1000,
                'tags': [Tag.objects.get(slug='solo').pk], 'image': image,
            })
            self.assertEqual(response.status_code, 302, response.context and response.context['adminform'].form.errors)
            restaurant = Restaurant.objects.get(name='管理登録テスト')
            self.assertTrue(restaurant.image.storage.exists(restaurant.image.name))
            self.assertTrue(restaurant.image_url.startswith('/media/'))
            self.assertEqual(list(restaurant.tags.values_list('slug', flat=True)), ['solo'])
            response = self.client.post(reverse('admin:restaurants_restaurant_change', args=[restaurant.pk]), {
                'name': '変更後テスト', 'genre': restaurant.genre_id, 'area': '中島',
                'price_min': 600, 'price_max': 1000,
            })
            self.assertEqual(response.status_code, 302)
            restaurant.refresh_from_db()
            self.assertEqual(restaurant.name, '変更後テスト')
            self.assertEqual(restaurant.area, '中島')

    def test_admin_rejects_invalid_image_and_unknown_late_night_hours(self):
        image = SimpleUploadedFile('fake.png', b'not-an-image', content_type='image/png')
        form = RestaurantAdminForm(data={'name': '画像検証'}, files={'image': image})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)
        form = RestaurantAdminForm(data={'name': '営業時間未確認', 'tags': [Tag.objects.get(slug='late-night').pk]})
        self.assertFalse(form.is_valid())
        self.assertIn('opening_hours', form.errors)

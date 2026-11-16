from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from restaurants.models import Restaurant
from .services import google_maps_urls, map_data


class MapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='map-user')
        cls.store = Restaurant.objects.create(name='地図テスト店', latitude=Decimal('42.33'),
                                               longitude=Decimal('140.98'), address='架空のテスト住所')
        cls.missing = Restaurant.objects.create(name='位置未登録')

    def setUp(self):
        self.client.force_login(self.user)

    def test_map_contains_numeric_coordinates_and_detail_link(self):
        response = self.client.get(reverse('maps:search'))
        self.assertEqual(response.status_code, 200)
        data = response.context['map_data']['stores']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['latitude'], 42.33)
        self.assertEqual(data[0]['longitude'], 140.98)
        self.assertEqual(data[0]['color'], 'blue')
        self.assertTrue(data[0]['detail_url'].startswith(self.store.get_absolute_url()))
        self.assertEqual(response.context['missing_count'], 1)
        self.assertContains(response, 'OpenStreetMap')
        self.assertIsNotNone(finders.find('maps/vendor/leaflet/leaflet.js'))

    def test_map_search_reuses_keyword_and_preserves_conditions(self):
        response = self.client.get(reverse('maps:search'), {'q': '地図テスト'})
        self.assertEqual(response.context['total_count'], 1)
        link = response.context['map_data']['stores'][0]['detail_url']
        self.assertEqual(parse_qs(urlsplit(link).query), {'source': ['map'], 'q': ['地図テスト']})

    def test_missing_coordinates_are_explained(self):
        response = self.client.get(reverse('maps:store', args=[self.missing.pk]))
        self.assertContains(response, '緯度・経度はまだ登録されていません')
        response = self.client.get(reverse('maps:directions', args=[self.missing.pk]))
        self.assertContains(response, '経路リンクを表示できません')

    def test_google_urls_follow_maps_urls_specification(self):
        urls = google_maps_urls(self.store)
        for key, mode in [('transit', 'transit'), ('walking', 'walking')]:
            parsed = urlsplit(urls[key])
            self.assertEqual(parsed.scheme, 'https')
            self.assertEqual(parsed.netloc, 'www.google.com')
            query = parse_qs(parsed.query)
            self.assertEqual(query['api'], ['1'])
            self.assertEqual(query['travelmode'], [mode])
            self.assertEqual(query['destination'], ['42.33,140.98'])
            self.assertNotIn('key', query)
        self.assertEqual(parse_qs(urlsplit(urls['place']).query)['query'], ['42.33,140.98'])

    def test_address_fallback_is_url_encoded_and_empty_destination_has_no_link(self):
        self.assertEqual(google_maps_urls(self.missing), {})
        self.missing.address = '室蘭市 テスト & 区画'
        query = parse_qs(urlsplit(google_maps_urls(self.missing)['transit']).query)
        self.assertEqual(query['destination'], [self.missing.address])

    def test_both_statuses_use_red_and_remain_in_popup_data(self):
        self.store.is_favorite = True
        self.store.is_visited = True
        record = map_data([self.store])['stores'][0]
        self.assertEqual(record['color'], 'red')
        self.assertTrue(record['is_visited'])
        self.assertTrue(record['is_favorite'])

    def test_store_and_directions_exist_and_unknown_ids_return_404(self):
        for name in ['maps:store', 'maps:directions']:
            self.assertEqual(self.client.get(reverse(name, args=[self.store.pk])).status_code, 200)
            self.assertEqual(self.client.get(reverse(name, args=[999999])).status_code, 404)

    def test_map_data_cannot_close_json_script(self):
        self.store.name = '</script><script>alert(1)</script>'
        self.store.save()
        response = self.client.get(reverse('maps:search'))
        self.assertNotContains(response, '</script><script>alert(1)</script>')
        self.assertContains(response, r'\u003C/script\u003E')

    def test_map_screens_require_login(self):
        self.client.logout()
        for url in [reverse('maps:search'), reverse('maps:store', args=[self.store.pk]),
                    reverse('maps:directions', args=[self.store.pk])]:
            self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

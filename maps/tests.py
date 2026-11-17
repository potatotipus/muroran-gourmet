from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from restaurants.models import Genre, Restaurant, Tag
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

    def test_store_map_popup_preserves_all_filters_and_original_list_or_map(self):
        genre = Genre.objects.get(slug='ramen')
        tags = list(Tag.objects.filter(slug__in=['cheap', 'large']))
        self.store.genre = genre
        self.store.area = '高砂'
        self.store.price_max = 900
        self.store.save()
        self.store.tags.set(tags)
        conditions = {'q': '地図テスト', 'genre': 'ramen', 'budget': '1000', 'area': '高砂', 'tags': ['cheap', 'large']}
        for source, screen, count_key in [('', 'restaurants:list', 'result_count'), ('map', 'maps:search', 'total_count')]:
            with self.subTest(source=source):
                query = {**conditions, **({'source': source} if source else {})}
                detail_url = self.store.get_absolute_url() + '?' + urlencode(query, doseq=True)
                response = self.client.get(reverse('maps:store', args=[self.store.pk]), {'back': detail_url})
                popup_url = response.context['map_data']['stores'][0]['detail_url']
                self.assertEqual(popup_url, detail_url)
                self.assertEqual(response.context['detail_url'], detail_url)
                detail = self.client.get(popup_url)
                back_url = detail.context['back_url']
                self.assertEqual(urlsplit(back_url).path, reverse(screen))
                self.assertEqual(parse_qs(urlsplit(back_url).query), parse_qs(urlencode(conditions, doseq=True)))
                self.assertEqual(self.client.get(back_url).context[count_key], 1)

    def test_store_map_popup_preserves_personal_map_display_mode(self):
        detail_url = self.store.get_absolute_url() + '?source=personal&mode=favorites'
        response = self.client.get(reverse('maps:store', args=[self.store.pk]), {'back': detail_url})
        popup_url = response.context['map_data']['stores'][0]['detail_url']
        self.assertEqual(popup_url, detail_url)
        detail = self.client.get(popup_url)
        self.assertEqual(detail.context['back_url'], reverse('maps:personal') + '?mode=favorites')

    def test_store_map_popup_and_back_link_use_safe_default_without_valid_origin(self):
        for origin in ['', 'https://example.invalid/', '//example.invalid/']:
            with self.subTest(origin=origin):
                response = self.client.get(reverse('maps:store', args=[self.store.pk]), {'back': origin})
                self.assertEqual(response.context['detail_url'], self.store.get_absolute_url())
                self.assertEqual(response.context['map_data']['stores'][0]['detail_url'], self.store.get_absolute_url())

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

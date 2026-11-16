"""地図の公開用データと、有料 API を使わない Google Maps URLs。"""

from urllib.parse import urlencode


def map_data(restaurants, query_string='', source='map'):
    stores = []
    for restaurant in restaurants:
        if restaurant.latitude is None or restaurant.longitude is None:
            continue
        favorite = bool(getattr(restaurant, 'is_favorite', False))
        visited = bool(getattr(restaurant, 'is_visited', False))
        query = f'source={source}'
        if query_string:
            query += '&' + query_string
        stores.append({
            'id': restaurant.pk, 'name': restaurant.name,
            'description': restaurant.description[:120],
            'latitude': float(restaurant.latitude), 'longitude': float(restaurant.longitude),
            'detail_url': restaurant.get_absolute_url() + '?' + query,
            'is_demo': restaurant.is_demo, 'is_favorite': favorite, 'is_visited': visited,
            'color': 'red' if favorite else 'green' if visited else 'blue',
        })
    return {'center': [42.345, 140.985], 'zoom': 12, 'stores': stores}


def google_maps_urls(restaurant):
    if restaurant.latitude is not None and restaurant.longitude is not None:
        destination = f'{restaurant.latitude},{restaurant.longitude}'
    elif restaurant.address.strip():
        destination = restaurant.address
    else:
        return {}
    return {
        'place': 'https://www.google.com/maps/search/?' + urlencode({'api': 1, 'query': destination}),
        'transit': 'https://www.google.com/maps/dir/?' + urlencode({
            'api': 1, 'destination': destination, 'travelmode': 'transit',
        }),
        'walking': 'https://www.google.com/maps/dir/?' + urlencode({
            'api': 1, 'destination': destination, 'travelmode': 'walking',
        }),
    }

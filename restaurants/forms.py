"""一覧と条件画面で共通の GET 検索条件。"""

from django import forms
from django.http import QueryDict

from .models import Genre, Restaurant, Tag


class RestaurantSearchForm(forms.Form):
    q = forms.CharField(label='店舗名・キーワード', max_length=100, required=False,
                        widget=forms.TextInput(attrs={'placeholder': '店名、メニュー、特徴など'}))
    budget = forms.ChoiceField(label='予算', required=False, choices=[
        ('', '指定なし'), ('500', '500円以内'), ('1000', '1,000円以内'), ('1500', '1,500円以内'),
    ], help_text='価格帯の上限が予算以内のお店を表示します。価格未登録のお店は対象外です。')
    genre = forms.ModelChoiceField(label='ジャンル', queryset=Genre.objects.all(), to_field_name='slug',
                                   empty_label='すべてのジャンル', required=False)
    area = forms.ChoiceField(label='エリア', required=False)
    tags = forms.ModelMultipleChoiceField(label='特徴', queryset=Tag.objects.all(), to_field_name='slug',
                                         required=False, widget=forms.CheckboxSelectMultiple,
                                         help_text='選択した特徴をすべて持つお店を表示します。')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        areas = list(Restaurant.objects.exclude(area='').order_by('area').values_list('area', flat=True).distinct())
        self.fields['area'].choices = [('', '指定なし')] + [
            (name, name) for name in dict.fromkeys(['高砂', '中島', '本町', *areas])
        ]

    @property
    def query_string(self):
        """既知の検索条件のみ引き継ぐ。戻り先自体は名前付き URL で固定する。"""
        query = QueryDict(mutable=True)
        for name in self.fields:
            if hasattr(self.data, 'getlist'):
                values = self.data.getlist(name)
            else:
                values = self.data.get(name, [])
                if not isinstance(values, (list, tuple)):
                    values = [values]
            values = [value for value in values if value]
            if values:
                query.setlist(name, values)
        return query.urlencode()


class RestaurantAdminForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = '__all__'

    def clean(self):
        data = super().clean()
        tags = data.get('tags')
        if tags is not None and any(tag.slug == 'late-night' for tag in tags) and not data.get('opening_hours'):
            self.add_error('opening_hours', '「夜遅くまで営業」を付ける場合は、確認済みの営業時間を入力してください。')
        return data

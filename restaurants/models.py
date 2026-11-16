"""店舗情報の管理元。他アプリは Restaurant の主キーと位置情報を参照する。"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.templatetags.static import static
from django.urls import reverse


class Genre(models.Model):
    name = models.CharField('ジャンル名', max_length=50, unique=True)
    slug = models.SlugField('識別子', unique=True)
    sort_order = models.PositiveSmallIntegerField('表示順', default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = '料理ジャンル'
        verbose_name_plural = '料理ジャンル'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField('特徴名', max_length=50, unique=True)
    slug = models.SlugField('識別子', unique=True)
    sort_order = models.PositiveSmallIntegerField('表示順', default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = '特徴タグ'
        verbose_name_plural = '特徴タグ'

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    name = models.CharField('店舗名', max_length=150)
    description = models.TextField('店舗説明', blank=True)
    address = models.CharField('住所', max_length=255, blank=True)
    area = models.CharField('エリア', max_length=50, blank=True, db_index=True)
    latitude = models.DecimalField('緯度', max_digits=9, decimal_places=6, null=True, blank=True,
                                   validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField('経度', max_digits=9, decimal_places=6, null=True, blank=True,
                                    validators=[MinValueValidator(-180), MaxValueValidator(180)])
    genre = models.ForeignKey(Genre, verbose_name='料理ジャンル', on_delete=models.PROTECT,
                              related_name='restaurants', null=True, blank=True)
    price_min = models.PositiveIntegerField('最低価格の目安（円）', null=True, blank=True)
    price_max = models.PositiveIntegerField('最高価格の目安（円）', null=True, blank=True)
    opening_hours = models.CharField('営業時間', max_length=255, blank=True)
    closed_days = models.CharField('定休日', max_length=150, blank=True)
    owner_description = models.TextField('店主のこだわり', blank=True)
    recommended_menu = models.TextField('おすすめメニュー', blank=True)
    image = models.ImageField('店舗画像', upload_to='restaurants/%Y/%m/', blank=True,
                              validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
                              help_text='掲載許可のある JPEG・PNG・WebP 画像（5MB以内）。')
    tags = models.ManyToManyField(Tag, verbose_name='特徴タグ', related_name='restaurants', blank=True)
    demo_key = models.CharField('デモ管理キー', max_length=40, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ['name', 'pk']
        verbose_name = '店舗'
        verbose_name_plural = '店舗'
        constraints = [
            models.CheckConstraint(condition=Q(price_min__isnull=True) | Q(price_max__isnull=True)
                                   | Q(price_max__gte=F('price_min')), name='restaurant_valid_price_range'),
            models.CheckConstraint(condition=Q(latitude__isnull=True) | Q(latitude__range=(-90, 90)),
                                   name='restaurant_valid_latitude'),
            models.CheckConstraint(condition=Q(longitude__isnull=True) | Q(longitude__range=(-180, 180)),
                                   name='restaurant_valid_longitude'),
            models.CheckConstraint(condition=(Q(latitude__isnull=True) & Q(longitude__isnull=True))
                                   | (Q(latitude__isnull=False) & Q(longitude__isnull=False)),
                                   name='restaurant_coordinate_pair'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        errors = {}
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            errors['price_max'] = '最高価格は最低価格以上にしてください。'
        if (self.latitude is None) != (self.longitude is None):
            errors['latitude'] = '緯度・経度は両方を入力するか、両方とも空欄にしてください。'
        if self.image and not self.image._committed and self.image.size > 5 * 1024 * 1024:
            errors['image'] = '画像は5MB以内にしてください。'
        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return reverse('restaurants:detail', args=[self.pk])

    @property
    def price_label(self):
        if self.price_min is not None and self.price_max is not None:
            if self.price_min == self.price_max:
                return f'{self.price_min:,}円'
            return f'{self.price_min:,}〜{self.price_max:,}円'
        if self.price_min is not None:
            return f'{self.price_min:,}円〜'
        if self.price_max is not None:
            return f'〜{self.price_max:,}円'
        return '予算未登録'

    @property
    def image_url(self):
        if self.image and self.image.storage.exists(self.image.name):
            return self.image.url
        return static('restaurants/images/placeholder.svg')

    @property
    def is_demo(self):
        return bool(self.demo_key)

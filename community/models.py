"""口コミ・お気に入りと、公開情報を直接変更しない通報記録。"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Length, Trim
from django.db.models.lookups import GreaterThan, LessThanOrEqual


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews', verbose_name='投稿者')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='reviews', verbose_name='店舗')
    rating = models.PositiveSmallIntegerField('評価', validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField('口コミ', max_length=200)
    created_at = models.DateTimeField('投稿日', auto_now_add=True)
    edited_at = models.DateTimeField('編集日時', null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = '口コミ'
        verbose_name_plural = '口コミ'
        constraints = [
            models.CheckConstraint(condition=Q(rating__range=(1, 5)), name='review_rating_1_to_5'),
            models.CheckConstraint(condition=LessThanOrEqual(Length('comment'), Value(200)), name='review_comment_max_200'),
            models.CheckConstraint(condition=GreaterThan(Length(Trim('comment')), Value(0)), name='review_comment_not_blank'),
        ]

    def __str__(self):
        return f'{self.restaurant} / {self.rating}点'

    @property
    def stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites', verbose_name='ユーザー')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='favorite_records', verbose_name='店舗')
    created_at = models.DateTimeField('登録日', auto_now_add=True)

    class Meta:
        verbose_name = 'お気に入り'
        verbose_name_plural = 'お気に入り'
        constraints = [models.UniqueConstraint(fields=['user', 'restaurant'], name='favorite_user_restaurant_unique')]


class Report(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', '未確認'
        REVIEWED = 'reviewed', '確認中'
        RESOLVED = 'resolved', '対応済み'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='報告者')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, verbose_name='対象店舗')
    review = models.ForeignKey(Review, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='対象口コミ')
    kind = models.CharField('種別', max_length=10, choices=[('restaurant', '店舗情報'), ('review', '口コミ')])
    reason = models.TextField('内容', max_length=500)
    status = models.CharField('確認状態', max_length=10, choices=Status.choices, default=Status.NEW)
    moderator_notes = models.TextField('管理者メモ', blank=True)
    created_at = models.DateTimeField('報告日', auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = '情報の通報・修正提案'
        verbose_name_plural = '情報の通報・修正提案'

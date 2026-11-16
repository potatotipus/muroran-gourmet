from django.conf import settings
from django.db import models


class Visit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visits', verbose_name='ユーザー')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='visit_records', verbose_name='店舗')
    visited_at = models.DateTimeField('訪問登録日時（自己申告）', auto_now_add=True)

    class Meta:
        ordering = ['-visited_at', '-pk']
        verbose_name = '訪問登録（自己申告）'
        verbose_name_plural = '訪問登録（自己申告）'
        constraints = [models.UniqueConstraint(fields=['user', 'restaurant'], name='visit_user_restaurant_unique')]

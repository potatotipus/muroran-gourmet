"""ポイントを重複保存せず、現在の異なる訪問店舗数から算出する。"""

from django.conf import settings
from .models import Visit


def visit_summary(user):
    count = Visit.objects.filter(user=user).count()
    per_store = settings.VISIT_POINTS_PER_STORE
    goal = settings.STAMP_GOAL
    return {
        'visit_count': count, 'stamp_count': count, 'points': count * per_store,
        'points_per_store': per_store, 'goal': goal, 'goal_count': min(count, goal),
        'progress_percent': min(100, count * 100 // goal),
    }

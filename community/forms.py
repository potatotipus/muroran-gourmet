from django import forms

from .models import Report, Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label='評価', coerce=int, choices=[
        (value, f'{"★" * value}{"☆" * (5 - value)}（{value}点）') for value in range(1, 6)
    ])

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {'comment': forms.Textarea(attrs={'rows': 5, 'maxlength': 200})}
        help_texts = {'comment': '200文字以内。画像は添付できません。'}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason']
        labels = {'reason': '通報・修正提案の内容'}
        widgets = {'reason': forms.Textarea(attrs={'rows': 5, 'maxlength': 500})}


class StateActionForm(forms.Form):
    action = forms.ChoiceField(choices=[('add', '登録'), ('remove', '解除')])

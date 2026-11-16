from django import forms


class PersonalMapForm(forms.Form):
    mode = forms.ChoiceField(label='表示する記録', required=False, choices=[
        ('', 'お気に入り・訪問済み'), ('favorites', 'お気に入りのみ'), ('visited', '訪問済みのみ'),
    ])

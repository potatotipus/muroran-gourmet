"""Django 標準 User を使うメールアドレス認証用フォーム。"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        label='ユーザー名',
        max_length=150,
        help_text='画面に表示する名前です。',
        widget=forms.TextInput(attrs={'autocomplete': 'nickname', 'autofocus': True}),
    )
    email = forms.EmailField(
        label='メールアドレス',
        max_length=150,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
        help_text='ログインに使用します（150文字以内）。',
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('first_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        users = self._meta.model.objects
        if users.filter(username__iexact=email).exists() or users.filter(email__iexact=email).exists():
            raise forms.ValidationError('このメールアドレスはすでに登録されています。')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # 標準 User.username の一意制約を利用し、DB/認証バックエンドを変更しない。
        user.username = user.email
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='メールアドレス',
        max_length=150,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'メールアドレスまたはパスワードが正しくありません。',
    }

    def clean_username(self):
        return self.cleaned_data['username'].lower()


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='ユーザー名', max_length=150)
    email = forms.EmailField(label='メールアドレス', max_length=150)
    current_password = forms.CharField(
        label='現在のパスワード', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        help_text='メールアドレスを変更する場合だけ必要です。',
    )

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = self.instance.email
        self.original_username = self.instance.username

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        others = self._meta.model.objects.exclude(pk=self.instance.pk)
        if others.filter(username__iexact=email).exists() or others.filter(email__iexact=email).exists():
            raise forms.ValidationError('このメールアドレスはすでに登録されています。')
        return email

    def clean(self):
        data = super().clean()
        if data.get('email') and data['email'] != self.original_email.lower():
            if not self.instance.check_password(data.get('current_password', '')):
                self.add_error('current_password', 'メールアドレスの変更には、正しい現在のパスワードが必要です。')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        # 表示名だけの変更では、従来の管理者ユーザー名を変更しない。
        if user.email != self.original_email.lower() or self.original_username.lower() == self.original_email.lower():
            user.username = user.email
        if commit:
            user.save()
        return user

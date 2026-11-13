"""アカウント作成・認証とログイン後の入口。"""

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView

from .forms import EmailAuthenticationForm, SignUpForm


class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # 仕様どおり毎回「探し方の選択」へ。外部/任意の next は採用しない。
        return reverse('accounts:choose')


@method_decorator(never_cache, name='dispatch')
class SignUpView(FormView):
    template_name = 'accounts/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('accounts:choose')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:choose')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            # 同じメールアドレスの同時登録も一意制約で拒否し、入力画面に戻す。
            if form._meta.model.objects.filter(username=form.cleaned_data['email']).exists():
                form.add_error('email', 'このメールアドレスはすでに登録されています。')
                return self.form_invalid(form)
            raise
        login(self.request, user)
        return super().form_valid(form)


class AccountLogoutView(LogoutView):
    next_page = reverse_lazy('home')

    def get_success_url(self):
        return reverse('home')


@method_decorator(never_cache, name='dispatch')
class ChooseView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/choose.html'

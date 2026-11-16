from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def local_destination(request, destination, default):
    """戻り先は現在ホストの絶対パスに限定する。"""
    destination = destination or ''
    if not (destination.startswith('/') and not destination.startswith('//')
            and url_has_allowed_host_and_scheme(destination, {request.get_host()}, require_https=request.is_secure())):
        destination = default
    return destination


def redirect_back(request, default):
    return redirect(local_destination(request, request.POST.get('next', ''), default))

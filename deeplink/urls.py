"""URL routes for the deferred-deep-link bridge.

The landing routes are mounted under /l/ at the project root, while the
well-known association files must live at exactly /.well-known/... — they
are wired separately in the project urls.py.
"""

from django.urls import path

from . import views

app_name = 'deeplink'

urlpatterns = [
    path('<str:code>/', views.landing, name='landing'),
]

well_known_urlpatterns = [
    path('apple-app-site-association', views.apple_app_site_association, name='aasa'),
    path('assetlinks.json', views.android_assetlinks, name='assetlinks'),
]

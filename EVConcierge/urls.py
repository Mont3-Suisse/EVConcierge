"""
URL configuration for EVConcierge project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from deeplink.urls import well_known_urlpatterns as deeplink_well_known

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="property_manager/auth/login.html",
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", include("property_manager.api.urls")),
    path("l/", include("deeplink.urls")),
    path(".well-known/", include((deeplink_well_known, "deeplink_well_known"))),
    path("", include("property_manager.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

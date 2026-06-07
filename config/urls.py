from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config.health import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("", include("apps.users.urls", namespace="users")),
    path("constitution/", include("apps.constitution.urls", namespace="constitution")),
    path("consultation/", include("apps.consultation.urls", namespace="consultation")),
    path("ia/", include("apps.ai_engine.urls", namespace="ai_engine")),
    path("api/", include("apps.constitution.api_urls", namespace="constitution_api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

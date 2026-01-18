"""
URL configuration for cleanupapk project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# JWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Login Custom (Jika ingin response tambahan)
from apk.auth_views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Semua API dari aplikasi apk
    path('api/', include('apk.urls')),

    # ======================
    #  JWT AUTHENTICATION
    # ======================

    # Standar JWT Login
    # path('api/login/', TokenObtainPairView.as_view(), name='jwt_login'),
     # ✅ LOGIN JWT (CUSTOM + is_active)
    path('api/login/', CustomLoginView.as_view(), name='jwt_login'),

    # Refresh Token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),

    # Custom login (opsional, jika ingin tambahan user info)
    path('api/auth/login/', CustomLoginView.as_view(), name="custom_jwt_login"),
]

# ======================
#   MEDIA STATIC FILES
# ======================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

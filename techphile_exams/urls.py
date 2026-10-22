from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from exams import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # Add this line for set_language



    # Other app URLs
    path('exams/', include('exams.urls')),
    path('', include('tech.urls')),
    path('explore_courses', include('core.urls')),

    path('accounts/', include('accounts.urls')),
    path('api/', include('api.urls')),
    path('coding/', include('coding.urls')),
    path('careers/', include('careers.urls')),
    path('interview-prep/', include('interview_prep.urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]


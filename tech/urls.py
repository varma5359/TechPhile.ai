from django.contrib import admin
from django.urls import path,include
from tech import views
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [

    # Public Pages
    path('', views.home, name="home"),
    path('about/', views.about, name="about"),
    path('services/', views.services, name="services"),  
    path('api/about/', views.api_about, name='api_about'),
    path('api/services/', views.api_services, name='api_services'),
    path('contact/', views.contact, name='contact'),
    path('api/contact/', views.ContactAPIView.as_view(), name='api_contact'),
]
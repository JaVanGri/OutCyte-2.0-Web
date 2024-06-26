"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
# from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from main.views import ImpressumView, TechnicalInformationView, PrivacyPolicyView

urlpatterns = [
    path('predictions/', include('predictions.urls')),
    path('', RedirectView.as_view(url='/predictions/', permanent=True),name='home'),  # Redirect von der Root URL
    path('impressum/', ImpressumView.as_view(), name='impressum'),
    path('howitworks/', TechnicalInformationView.as_view(), name='howitworks'),
    path('privacy/', PrivacyPolicyView.as_view(), name='privacy'),
]

from django.views.generic import TemplateView


class ImpressumView(TemplateView):
    template_name = 'impressum.html'  # Der Dateiname des Impressum-Templates


class TechnicalInformationView(TemplateView):
    template_name = 'howitworks.html'  # Der Dateiname des Impressum-Templates


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy.html'  # Der Dateiname des Impressum-Templates

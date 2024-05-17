from django.views.generic import TemplateView


class ImpressumView(TemplateView):
    template_name = 'impressum.html'


class TechnicalInformationView(TemplateView):
    template_name = 'howitworks.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy.html'

import time
from django.core.cache import cache
from django.shortcuts import render

import oc_settings


class GlobalConcurrencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_concurrent_requests = oc_settings.max_number_requests_different_clients
        current_requests = cache.get('current_requests', 0)

        if current_requests >= max_concurrent_requests:
            return render(request, 'prediction_form.html', {'error_message': 'OutCyte is Busy. Please Try it later.'})

        # Inkrementiere den Zähler für aktive Anfragen
        cache.set('current_requests', current_requests + 1, timeout=None)

        try:
            response = self.get_response(request)
        finally:
            # Dekrementiere den Zähler, wenn die Anfrage abgeschlossen ist
            current_requests = cache.get('current_requests', 1)
            cache.set('current_requests', current_requests - 1, timeout=None)

        return response
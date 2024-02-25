# middleware.py
from django.conf import settings
from django.http import HttpResponseForbidden
from collections import defaultdict
from django.utils import timezone



class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_count = defaultdict(list)

        self.max_requests = getattr(settings, "MAX_REQUESTS_PER_WINDOW")
        self.block_duration = getattr(settings, "BLOCK_DURATION")
        self.blocked_ips = {}

    def __call__(self, request):
        ip = self.get_client_ip(request)

        if ip in self.blocked_ips and timezone.now() < self.blocked_ips[ip]:
            return HttpResponseForbidden("Rate limit exceeded, Please try again later.")
        elif self.is_over_rate_limit(ip):
            self.block_ip(ip)
            return HttpResponseForbidden("Rate limit exceeded, Please try again later.")

        response = self.get_response(request)
        self.process_response(request, response)
        return response

    def process_response(self, request, response):
        ip = self.get_client_ip(request)
        self.request_count[ip].append((timezone.now(), 1))

    def is_over_rate_limit(self, ip):
        current_time = timezone.now()
        requests_in_window = sum(count for time_stamp, count in self.request_count[ip] if time_stamp > current_time - timezone.timedelta(seconds=self.block_duration))
        return requests_in_window > self.max_requests

    def block_ip(self, ip):
        self.blocked_ips[ip] = timezone.now() + timezone.timedelta(seconds=self.block_duration)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


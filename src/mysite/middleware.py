# middleware.py

from collections import defaultdict
from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils import timezone



class RateLimitMiddleware:
    """
    Middleware class to implement rate limiting based on IP addresses.

    Attributes:
        get_response: The callable function to get the response in the Django middleware chain.
        request_count: A dictionary to store the request count for each IP address.
        max_requests: Maximum number of requests allowed per window.
        block_duration: Duration in seconds for which an IP address is blocked after exceeding the rate limit.
        blocked_ips: Dictionary to store IP addresses that are currently blocked.
    """

    def __init__(self, get_response):
        """
        Constructor method to initialize the middleware.

        Args:
            get_response: The callable function to get the response in the Django middleware chain.
        """
        self.get_response = get_response
        self.request_count = defaultdict(list)

        # Fetching configuration settings from Django settings
        self.max_requests = getattr(settings, "MAX_REQUESTS_PER_WINDOW")
        self.block_duration = getattr(settings, "BLOCK_DURATION")
        self.blocked_ips = dict()


    def __call__(self, request):
        """
        Method called when an instance of the middleware is called like a function.

        Args:
            request: The HTTP request object.

        Returns:
            HTTP response object.
        """
        ip = self.get_client_ip(request)

        # Check if the IP is currently blocked
        if ip in self.blocked_ips and timezone.now() < self.blocked_ips[ip]:
            return HttpResponseForbidden("Rate limit exceeded, Please try again later.")
        # Check if the IP has exceeded the rate limit
        elif self.is_over_rate_limit(ip):
            # If exceeded, block the IP and return forbidden response
            self.block_ip(ip)
            return HttpResponseForbidden("Rate limit exceeded, Please try again later.")

        # If the request is within limits, proceed with the normal flow
        response = self.get_response(request)
        self.process_response(request, response)
        return response

    def process_response(self, request, response):
        """
        Method to process the response and update the request count for the IP.

        Args:
            request: The HTTP request object.
            response: The HTTP response object.
        """
        ip = self.get_client_ip(request)
        # Append the current timestamp and count of 1 for the IP
        self.request_count[ip].append((timezone.now(), 1))

    def is_over_rate_limit(self, ip):
        """
        Method to check if the given IP has exceeded the rate limit.

        Args:
            ip: The IP address to check.

        Returns:
            True if the IP has exceeded the rate limit, False otherwise.
        """
        current_time = timezone.now()
        # Sum up the counts of requests within the defined window
        requests_in_window = sum(count for time_stamp, count in self.request_count[ip] if time_stamp > current_time - timezone.timedelta(seconds=self.block_duration))
        return requests_in_window > self.max_requests

    def block_ip(self, ip):
        """
        Method to block an IP address for a certain duration.

        Args:
            ip: The IP address to block.
        """
        # Set the block duration for the IP
        self.blocked_ips[ip] = timezone.now() + timezone.timedelta(seconds=self.block_duration)

    def get_client_ip(self, request):
        """
        Method to extract the client's IP address from the request.

        Args:
            request: The HTTP request object.

        Returns:
            The client's IP address.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # If there's a forwarded IP, use it
            ip = x_forwarded_for.split(",")[0]
        else:
            # Otherwise, use the remote IP address
            ip = request.META.get("REMOTE_ADDR")
        return ip

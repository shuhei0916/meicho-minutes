import requests


class AmazonScraper:
    def __init__(self, request_delay=1.0, max_retries=3):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.session = requests.Session()
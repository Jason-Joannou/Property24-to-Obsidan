import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import os

class PropertyScrapper:

    def __init__(self) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
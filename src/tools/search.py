# src/tools/search.py
import os
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
import time

class SearchTool:
    def __init__(self, serpapi_key: str = None):
        self.serpapi_key = serpapi_key or os.environ.get("SERPAPI_KEY")
        if not self.serpapi_key:
            raise RuntimeError("SERPAPI_KEY not set in env")

    def web_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Perform a Google search via SerpAPI.
        Returns list of dicts {title, url, snippet}.
        """
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google",
            "q": query,
            "num": top_k,
            "api_key": self.serpapi_key
        }
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"SerpAPI error {resp.status_code}: {resp.text}")
        data = resp.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results

    def fetch_full_page(self, url: str) -> str:
        """
        Fetch the full text content of a webpage with robust error handling.
        Returns cleaned text content, limited to 2000 characters.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # First try with SSL verification
            try:
                resp = requests.get(url, headers=headers, timeout=15, verify=True)
                resp.raise_for_status()
            except requests.exceptions.SSLError:
                # Fallback to without SSL verification
                print(f"SSL verification failed for {url}, trying without verification...")
                resp = requests.get(url, headers=headers, timeout=15, verify=False)
                resp.raise_for_status()

            # Handle different response status codes
            if resp.status_code == 403:
                print(f"Access forbidden for {url} - site blocks automated requests")
                return ""
            elif resp.status_code != 200:
                print(f"HTTP {resp.status_code} error for {url}")
                return ""

            # Detect encoding properly
            resp.encoding = resp.apparent_encoding or 'utf-8'

            soup = BeautifulSoup(resp.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.extract()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace and normalize
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            # Remove excessive whitespace
            text = ' '.join(text.split())

            # Limit to 2000 characters to manage token budget
            if len(text) > 2000:
                text = text[:2000] + "..."

            return text

        except requests.exceptions.Timeout:
            print(f"Timeout fetching {url}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
            return ""
        except Exception as e:
            print(f"Failed to fetch {url}: {str(e)}")
            return ""

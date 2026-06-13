import re

from bs4 import BeautifulSoup


def get_total_pages(html: str) -> int:
    soup = BeautifulSoup(html, "lxml")
    links = soup.select(".pagination a[href*='page=']")
    if not links:
        return 1
    page_nums = []
    for link in links:
        match = re.search(r"page=(\d+)", link.get("href", ""))
        if match:
            page_nums.append(int(match.group(1)))
    return max(page_nums) if page_nums else 1

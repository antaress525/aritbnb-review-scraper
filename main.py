from typing import List, Dict
from pprint import pprint

from selectolax.parser import HTMLParser
from playwright.sync_api import sync_playwright, Playwright


def extract_avis(tree: HTMLParser) -> List[Dict]:
    avis = []
    comment_modal = tree.css_first("[data-testid='dls-modal-container']")
    if not comment_modal:
        return []

    comment_divs = comment_modal.css("[data-testid='pdp-reviews-modal-scrollable-panel'] > div > div:not(:nth-last-child(-n+2))")

    for comment_div in comment_divs:
        avis.append({
            "username": comment_div.css_first("h2").text(),
            "date": comment_div.css_first("div[data-review-id] div:first-child div:nth-child(2) div:nth-child(3)").text(),
            "comment": comment_div.css_first("[data-review-id] div[style*='line-height']").text()
        })

    return avis

def extract_logment_data(html: str) -> Dict:
    tree = HTMLParser(html)
    return {
        "title": tree.css_first("h1").text() or "",
        "commentaires": extract_avis(tree)
    }



def main(pw: Playwright):
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context()
    context.set_default_timeout(60000)
    page = context.new_page()
    page.goto("https://fr.airbnb.com/rooms/46708572")
    page.get_by_role("button", name="Fermer").click()
    show_all_comment_button = page.get_by_test_id("pdp-show-all-reviews-button")

    if show_all_comment_button:
        show_all_comment_button.click()
        page.wait_for_timeout(5000)
        html_content = page.content()
        data = extract_logment_data(html_content)
        pprint(data)
    else:
        pass

    page.pause()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        main(playwright)

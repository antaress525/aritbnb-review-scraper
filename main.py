from typing import List, Dict
from pprint import pprint

from selectolax.parser import HTMLParser
from playwright.sync_api import sync_playwright, Playwright


URL_1 = "https://fr.airbnb.com/rooms/46708572"
URL_2 = "https://fr.airbnb.com/rooms/1612384942433387618"
URL_3 = "https://fr.airbnb.com/rooms/1625461250109416169"
URL_4 = "https://fr.airbnb.com/rooms/1572101850266624270"
URL_5 = "https://fr.airbnb.com/rooms/1620326932832830950"

def extract_review(tree: HTMLParser) -> List[Dict]:
    review = []
    review_modal = tree.css_first("[data-testid='dls-modal-container']")
    if not review_modal:
        return []

    review_divs = review_modal.css("[data-testid='pdp-reviews-modal-scrollable-panel'] > div > div")

    for review_div in review_divs:
        if username := review_div.css_first("h2"):
            date = review_div.css_first("div[data-review-id] div:first-child div:nth-child(2) div:nth-child(3)").text()
            comment = review_div.css_first("[data-review-id] div[style*='line-height']").text()
            review.append({
                "username": username.text(),
                "date": date,
                "comment": comment
            })

    return review

def extract_logment_data(html: str) -> Dict:
    tree = HTMLParser(html)
    return {
        "title": tree.css_first("h1").text() or "",
        "commentaires": extract_review(tree)
    }



def main(pw: Playwright):
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context()
    context.set_default_timeout(60000)
    page = context.new_page()
    page.goto(URL_2)
    close_modal_button = page.get_by_role("button", name="Fermer")
    if close_modal_button.is_visible(timeout=2000):
        close_modal_button.click()

    show_all_comment_button = page.get_by_test_id("pdp-show-all-reviews-button")

    if show_all_comment_button.is_visible():
        show_all_comment_button.click()
        page.wait_for_timeout(5000)
        html_content = page.content()
        reviews = extract_logment_data(html_content)
    else:
        read_more_button = page.locator("css=div._13nmyp [aria-describedby] >> text=Lire la suite").first
        if read_more_button:
            read_more_button.click()
            page.wait_for_timeout(6000)
            html_content = page.content()
            reviews = extract_logment_data(html_content)

    page.pause()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        main(playwright)

from typing import List, Dict, Optional
from pprint import pprint
import json
import os
from pathlib import Path

from selectolax.parser import HTMLParser, Node
from playwright.sync_api import sync_playwright, Playwright, Route, Page

BLOCK_RESOURCE_TYPES = ["image", "font"]

URL_1 = "https://fr.airbnb.com/rooms/46708572"
URL_2 = "https://fr.airbnb.com/rooms/1612384942433387618"
URL_3 = "https://fr.airbnb.com/rooms/1625461250109416169"
URL_4 = "https://fr.airbnb.com/rooms/1572101850266624270"
URL_5 = "https://fr.airbnb.com/rooms/1620326932832830950"
URL_6 = "https://fr.airbnb.com/rooms/1680822447979343297"

def safe_text(node: Optional[Node], fallback: str = "") -> str:
    return node.text(strip=True) if node else fallback


def save_to_json(data: Dict, filepath: str = "airbnb_reviews.json") -> None:
    path = Path(filepath)

    existing_data = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Fichier {filepath} corrompu, réinitialisation.")
                existing_data = {}

    existing_data.update(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Données sauvegardées dans {filepath}")


def extract_reviews_from_modal(tree: HTMLParser) -> List[Dict]:
    reviews = []
    modal = tree.css_first("[data-testid='dls-modal-container']")

    if not modal:
        return reviews

    review_divs = modal.css("[data-testid='pdp-reviews-modal-scrollable-panel'] > div > div")

    for review_div in review_divs:
        username_node = review_div.css_first("h2")
        comment_node = review_div.css_first("[data-review-id] div[style*='line-height']")
        date_node = review_div.css_first("div[data-review-id] div:first-child div:nth-child(2) div:nth-child(3)")

        username = safe_text(username_node, fallback="")
        date     = safe_text(date_node,     fallback="")
        comment  = safe_text(comment_node,  fallback="")

        # Blocks without useful content are ignored
        if not username and not comment:
            continue

        reviews.append({
            "username": username,
            "date":     date,
            "comment":  comment,
        })

    return reviews


def extract_reviews_from_page(tree: HTMLParser) -> List[Dict]:
    reviews = []
    review_items = tree.css("div._13nmyp div[role='listitem']")
    for items in review_items:
        username_node = items.css_first("h3")
        date_node = items.css_first(".d18si1uy")
        comment_node = items.css_first("div[style*='line-height']")

        username = safe_text(username_node, fallback="Inconnu")
        date     = safe_text(date_node,     fallback="")
        comment  = safe_text(comment_node,  fallback="")

        if not username and not comment:
            continue

        reviews.append({
            "username": username,
            "date":     date,
            "comment":  comment,
        })


    return reviews



# Block non-essential resources from accessing the load
def block_resources(route: Route) -> None:
    if route.request.resource_type in BLOCK_RESOURCE_TYPES:
        return route.abort()
    if "google" in route.request.url:
        return route.abort()
    return route.continue_()

def scroll_modal(page: Page):
    panel_selector = "div[style='padding: 0px 24px;']"
    panel = page.locator(panel_selector)
    previous_count = 0

    while True:
        panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")

        page.wait_for_timeout(1_500)

        current_count = page.locator("div[data-review-id]").count()
        print(f"  → {current_count} avis chargés...")

        if current_count == previous_count:
            break

        previous_count = current_count


def scrape_listing(page: Page, url: str) -> Dict:
    print("Chargement de la page...")
    page.goto(url)

    title = ""
    reviews: List[Dict] = []

    # Close translate popup if present
    try:
        page.get_by_role("button", name="Fermer").click()
        print("Popup de traduction fermée")
    except Exception:
        pass


    # Modal "See all reviews"
    try:
        show_all_btn = page.get_by_test_id("pdp-show-all-reviews-button")
        show_all_btn.wait_for(state="visible", timeout=10_000)
        print("Ouverture de la modale des avis...")
        show_all_btn.click()

        page.wait_for_selector(
                "div[data-review-id]",
                timeout=10_000
            )

        scroll_modal(page)

        html = page.content()
        tree = HTMLParser(html)
        title = safe_text(tree.css_first("h1"), fallback="Inconnu")
        reviews = extract_reviews_from_modal(tree)
        return {"title": title, "commentaires": reviews}

    except Exception as e:
        print(f"Modale indisponible ({e}), tentative via 'Lire la suite'...")

    # Read more button
    try:
        read_more = page.locator(
            "css=div._13nmyp [aria-describedby] >> text=Lire la suite"
        ).first
        print("Ouverture via 'Lire la suite'...")
        read_more.click()

        page.wait_for_selector(
                "div[data-review-id]",
                timeout=10_000
            )

        scroll_modal(page)

        html = page.content()
        tree = HTMLParser(html)
        title = safe_text(tree.css_first("h1"), fallback="Inconnu")
        reviews = extract_reviews_from_modal(tree)
        return {"title": title, "commentaires": reviews}

    except Exception as e:
        print(f"Bouton 'Lire la suite' indisponible ({e}), extraction directe...")

    # Direct extraction
    page.wait_for_selector("h1", timeout=10_000)
    html = page.content()
    tree = HTMLParser(html)
    title = safe_text(tree.css_first("h1"))
    reviews = extract_reviews_from_page(tree)
    return {"title": title, "commentaires": reviews}



def main(pw: Playwright):
    browser  = pw.chromium.launch(headless=False)

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.95 Safari/537.36",
        viewport={"width": 1280, "height": 820},
        locale="fr-FR",
    )

    page = context.new_page()
    page.route("**/*", block_resources)

    result = scrape_listing(page, URL_3)
    save_to_json(result)

    page.close()
    context.close()



if __name__ == "__main__":
    with sync_playwright() as playwright:
        main(playwright)

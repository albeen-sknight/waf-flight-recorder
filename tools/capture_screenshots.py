#!/usr/bin/env python3
"""Take browser screenshots of the running Docker lab (real Juice Shop behind
the WAF) for the docs. Used by .github/workflows/screenshots.yml.

    python3 tools/capture_screenshots.py on        # WAF enforcing
    python3 tools/capture_screenshots.py detection # WAF in DetectionOnly

Writes PNG files to docs/screenshots/. Only ever talks to http://localhost:8080.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
FP001 = ("The link https://example.com/?ref=juice&utm_source=mail "
         "in your newsletter has a typo")


def shot(page, name, full=False):
    page.screenshot(path=str(OUT / name), full_page=full)
    print("saved", name)


def text_page(browser, url, name):
    page = browser.new_page(viewport={"width": 1100, "height": 260})
    page.goto(url)
    page.wait_for_timeout(500)
    shot(page, name)
    page.close()


def run(mode):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        ctx.add_cookies([{"name": n, "value": "dismiss", "url": BASE}
                         for n in ("welcomebanner_status", "cookieconsent_status")])
        ctx.add_cookies([{"name": "language", "value": "en", "url": BASE}])
        page = ctx.new_page()

        if mode == "detection":
            try:
                page.goto(BASE + "/ftp")
                page.wait_for_timeout(1500)
                shot(page, "08-ftp-listing-detectiononly.png")
            except Exception as e:
                print("ftp detection shot failed:", e)
            browser.close()
            return

        steps = []

        def home():
            page.goto(BASE + "/#/")
            page.wait_for_timeout(4000)
            shot(page, "01-juice-shop-through-waf.png")
        steps.append(home)

        def search():
            page.goto(BASE + "/#/search?q=apple")
            page.wait_for_timeout(3000)
            shot(page, "02-normal-search-allowed.png")
        steps.append(search)

        steps.append(lambda: text_page(browser, BASE + "/rest/products/search?q=%27%20OR%201%3D1--",
                                       "03-sqli-search-blocked.png"))

        def login():
            page.goto(BASE + "/#/login")
            page.wait_for_timeout(2500)
            page.fill("#email", "' OR 1=1--")
            page.fill("#password", "anything")
            page.click("#loginButton")
            page.wait_for_timeout(2500)
            shot(page, "04-login-sqli-bypass-blocked.png")
        steps.append(login)

        def feedback():
            page.goto(BASE + "/#/contact")
            page.wait_for_timeout(3000)
            page.fill("#comment", FP001)
            page.locator("mat-slider, .mat-mdc-slider").first.click()
            q = page.locator("#captcha").inner_text()
            expr = re.sub(r"[^0-9+\-*/ ]", "", q)
            page.fill("#captchaControl", str(eval(expr)))  # simple arithmetic captcha
            page.wait_for_timeout(500)
            shot(page, "05-fp001-feedback-form.png")
            page.click("#submitButton")
            page.wait_for_timeout(2000)
            shot(page, "06-fp001-feedback-accepted.png")
        steps.append(feedback)

        steps.append(lambda: text_page(browser, BASE + "/ftp", "07-ftp-blocked.png"))

        for step in steps:
            try:
                step()
            except Exception as e:  # keep going; a missing screenshot is not fatal
                print("step failed:", getattr(step, "__name__", step), e)
        browser.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "on")

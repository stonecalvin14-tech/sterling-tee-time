"""
Sterling Farms Tee Time Auto-Booker
====================================
Books the earliest available tee time on June 20, 2026
between 8:00am and 12:00pm for 4 golfers.

Schedule this script to run at 4:58am on June 13, 2026
using Task Scheduler (Windows) or cron (Mac/Linux).

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── Configuration ──────────────────────────────────────────────────────────────
USERNAME       = "83417"
PASSWORD       = "Golf1234"
BOOKING_URL    = "https://sterling.chelseareservations.com/golf/bookingadmin.aspx"
TARGET_DATE    = "June 20"       # Must match calendar display
TARGET_DAY_NUM = 20              # Day number to click
NUM_GOLFERS    = "4 Golfers"
NUM_HOLES      = "18 Holes"
EARLIEST_TIME  = 9               # 9am (no earlier)
LATEST_TIME    = 12              # 12pm (no later)

PREFERRED_TIMES = [
    "09:00 am", "09:30 am",
    "10:00 am", "10:30 am", "11:00 am", "11:30 am",
    "12:00 pm"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("tee_time_log.txt"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def parse_hour(time_str: str) -> float:
    """Convert '08:30 am' / '12:00 pm' → 8.5 / 12.0"""
    t = datetime.strptime(time_str.strip(), "%I:%M %p")
    return t.hour + t.minute / 60


async def book_tee_time():
    log.info("Starting tee time booker for Sterling Farms — June 20, 2026")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # set True to run silently
        context = await browser.new_context()
        page = await context.new_page()

        # ── 1. Load booking page ───────────────────────────────────────────────
        log.info("Loading booking page...")
        await page.goto(BOOKING_URL, wait_until="networkidle")

        # ── 2. Log in ──────────────────────────────────────────────────────────
        log.info("Logging in...")
        try:
            username_field = page.locator("input[type='text'], input[name*='user'], input[name*='User'], input[id*='user'], input[id*='User']").first
            password_field = page.locator("input[type='password']").first
            await username_field.fill(USERNAME)
            await password_field.fill(PASSWORD)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            log.info("Login submitted.")
        except Exception as e:
            log.error(f"Login failed: {e}")
            await browser.close()
            return

        # ── 3. Select # of Golfers ─────────────────────────────────────────────
        log.info(f"Selecting {NUM_GOLFERS}...")
        try:
            await page.select_option("select", label=NUM_GOLFERS)
        except Exception:
            # Try selecting by golfer count dropdowns individually
            selects = await page.locator("select").all()
            for sel in selects:
                options = await sel.inner_text()
                if "Golfer" in options:
                    await sel.select_option(label=NUM_GOLFERS)
                    break

        # ── 4. Select # of Holes ──────────────────────────────────────────────
        log.info("Selecting 18 Holes...")
        try:
            selects = await page.locator("select").all()
            for sel in selects:
                options = await sel.inner_text()
                if "Holes" in options:
                    await sel.select_option(label=NUM_HOLES)
                    break
        except Exception as e:
            log.warning(f"Could not set holes: {e}")

        # ── 5. Click June 20 on the calendar ──────────────────────────────────
        log.info(f"Clicking day {TARGET_DAY_NUM} on the calendar...")
        try:
            # The calendar uses __doPostBack('Day20', '')
            day_link = page.locator(f"a[href*='Day{TARGET_DAY_NUM}']")
            await day_link.click()
            await page.wait_for_load_state("networkidle")
            log.info("Calendar day selected.")
        except Exception as e:
            log.error(f"Could not click calendar day: {e}")
            await browser.close()
            return

        # ── 6. Find available time slots ──────────────────────────────────────
        log.info("Scanning available tee times...")
        await page.wait_for_timeout(1500)

        booked = False
        for time_str in PREFERRED_TIMES:
            hour = parse_hour(time_str)
            if hour < EARLIEST_TIME or hour > LATEST_TIME:
                continue

            try:
                # Look for a link or button matching this time
                slot = page.locator(f"text={time_str}").first
                if await slot.is_visible():
                    log.info(f"Found available slot: {time_str} — clicking...")
                    await slot.click()
                    await page.wait_for_load_state("networkidle")

                    # ── 7. Confirm booking ─────────────────────────────────────
                    confirm_btn = page.locator("input[type='submit'][value*='Confirm'], button:has-text('Confirm'), input[value*='Book']").first
                    if await confirm_btn.is_visible():
                        await confirm_btn.click()
                        await page.wait_for_load_state("networkidle")
                        log.info(f"✅ TEE TIME BOOKED: {time_str} on June 20 for 4 golfers!")
                        booked = True

                        # Screenshot as proof
                        await page.screenshot(path="booking_confirmation.png")
                        log.info("Confirmation screenshot saved: booking_confirmation.png")
                        break
                    else:
                        log.warning(f"No confirm button found after selecting {time_str}")
            except PlaywrightTimeout:
                log.warning(f"Timeout on slot {time_str}, trying next...")
            except Exception as e:
                log.warning(f"Could not book {time_str}: {e}")

        if not booked:
            log.error("❌ No available slots found between 8am–12pm on June 20.")
            await page.screenshot(path="booking_failed.png")
            log.info("Screenshot saved: booking_failed.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(book_tee_time())

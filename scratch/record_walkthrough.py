import os
import sys
import asyncio
from playwright.async_api import async_playwright

# Setup base URL from arguments or default
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def record_walkthrough():
    print(f"Starting detailed 5-minute walkthrough recording targeting: {BASE_URL}")
    print(f"Video file will be saved in: {OUTPUT_DIR}")

    async with async_playwright() as p:
        # Launch Chromium headless
        browser = await p.chromium.launch(headless=True)
        
        # Open context with a high definition viewport
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # Inject standard style overrides to display visual clicks
        await page.add_init_script("""
            window.addEventListener('DOMContentLoaded', () => {
                const style = document.createElement('style');
                style.innerHTML = `
                    .playwright-click-pulse {
                        position: absolute;
                        width: 26px;
                        height: 26px;
                        border: 3px solid var(--color-accent, #00ffcc);
                        border-radius: 50%;
                        transform: translate(-50%, -50%) scale(1);
                        animation: clickPulse 0.5s ease-out forwards;
                        pointer-events: none;
                        z-index: 99999;
                    }
                    @keyframes clickPulse {
                        0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                        100% { transform: translate(-50%, -50%) scale(2.8); opacity: 0; }
                    }
                `;
                document.head.appendChild(style);
            });
            window.showClickVisual = (x, y) => {
                const div = document.createElement('div');
                div.className = 'playwright-click-pulse';
                div.style.left = x + 'px';
                div.style.top = y + 'px';
                document.body.appendChild(div);
                setTimeout(() => div.remove(), 500);
            };
        """)

        async def smooth_click(selector):
            element = page.locator(selector).first
            if await element.is_visible():
                box = await element.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    # Move mouse smoothly
                    await page.mouse.move(x, y, steps=12)
                    await page.evaluate(f"window.showClickVisual({x}, {y})")
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.8)

        async def smooth_hover(selector):
            element = page.locator(selector).first
            if await element.is_visible():
                box = await element.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    await page.mouse.move(x, y, steps=10)
                    await asyncio.sleep(1.0)

        # -----------------------------------------------------------------
        #  0:00 - 0:05 | Load Page
        # -----------------------------------------------------------------
        print("0:00 | Loading website homepage...")
        await page.goto(BASE_URL)
        await page.wait_for_selector(".app-header", timeout=12000)
        await asyncio.sleep(4.0)

        # -----------------------------------------------------------------
        #  0:05 - 0:35 | Schematic Mode, Station Boards, & Train clicks
        # -----------------------------------------------------------------
        print("0:05 | Switching to Schematic View...")
        await smooth_click("button:has-text('SCHEMATIC')")
        await asyncio.sleep(2.0)

        print("0:07 | Clicking NDLS station to load live arrival board...")
        # In Schematic SVG, click the circle marker near NDLS text
        await smooth_click("svg >> text:has-text('NDLS')")
        await asyncio.sleep(8.0)  # Wait for live board info to be observed

        print("0:15 | Clicking GZB station...")
        await smooth_click("svg >> text:has-text('GZB')")
        await asyncio.sleep(6.0)

        print("0:21 | Clicking Vande Bharat train node (22415) to inspect telemetry...")
        await smooth_click("g.train-node >> text:has-text('22415')")
        await asyncio.sleep(5.0)

        print("0:26 | Adjusting safety speed limits on telemetry inspector...")
        await smooth_click("button:has-text('60')")
        await asyncio.sleep(3.0)
        await smooth_click("button:has-text('110')")
        await asyncio.sleep(3.0)
        await smooth_click("button:has-text('130')")
        await asyncio.sleep(3.0)

        # -----------------------------------------------------------------
        #  0:35 - 1:15 | Geo Map & Live Route Search
        # -----------------------------------------------------------------
        print("0:35 | Returning to Geo Map Mode...")
        await smooth_click("button:has-text('GEO MAP')")
        await asyncio.sleep(4.0)

        print("0:39 | Entering Live Route Search preset (DEL→KNP)...")
        await smooth_click("button:has-text('DEL→KNP')")
        await asyncio.sleep(2.0)
        
        print("0:41 | Triggering live search...")
        await smooth_click("button:has-text('SEARCH')")
        print("Waiting 12s for IRCTC live query results...")
        await asyncio.sleep(12.0)

        print("0:55 | Scrolling route trains in the side inspector...")
        inspector_list = page.locator("div.glass-card:has(h4:has-text('Telemetry Inspector')) >> div >> div").first
        if await inspector_list.is_visible():
            box = await inspector_list.bounding_box()
            if box:
                await page.mouse.move(box["x"] + 50, box["y"] + 50)
                await page.mouse.wheel(0, 150)
                await asyncio.sleep(2.0)
                await page.mouse.wheel(0, -150)
                await asyncio.sleep(2.0)

        print("0:59 | Clicking one of the live route trains to view live JSON telemetry...")
        # Click the first live train listed in the Telemetry Inspector
        await smooth_click("div.glass-card:has(h4:has-text('Telemetry Inspector')) >> div >> div >> div >> span >> nth=0")
        await asyncio.sleep(10.0)  # Let live JSON telemetry render

        print("1:09 | Clearing live search to resume scenario mode...")
        await smooth_click("button:has-text('Clear')")
        await asyncio.sleep(4.0)

        # -----------------------------------------------------------------
        #  1:13 - 2:25 | Scenario Autoplay & Controller Action
        # -----------------------------------------------------------------
        print("1:13 | Starting Autoplay sequence...")
        await smooth_click("button:has-text('START AUTOPLAY')")
        
        # We wait through the autoplay steps (each takes 6 seconds internally)
        print("1:14 | Autoplay: Step 0 -> Step 1...")
        await asyncio.sleep(8.0)
        print("1:22 | Autoplay: Step 1 -> Step 2...")
        await asyncio.sleep(8.0)
        print("1:30 | Autoplay: Step 2 -> Step 3...")
        await asyncio.sleep(8.0)
        print("1:38 | Autoplay: Step 3 -> Step 4...")
        await asyncio.sleep(8.0)

        # At step 4, conflict is active. Let's approve recommendations.
        print("1:46 | Pause Autoplay to review critical dispatch conflicts...")
        await smooth_click("button:has-text('PAUSE AUTOPLAY')")
        await asyncio.sleep(2.0)
        
        print("1:48 | Scrolling down conflict details...")
        await page.mouse.wheel(0, 250)
        await asyncio.sleep(3.0)

        print("1:51 | Approving conflict resolution advisory as Controller...")
        await smooth_click("button:has-text('Approve')")
        await asyncio.sleep(4.0)

        print("1:55 | Resuming Autoplay for final resolution stages...")
        await smooth_click("button:has-text('START AUTOPLAY')")
        print("1:56 | Autoplay: Step 4 -> Step 5...")
        await asyncio.sleep(8.0)
        print("2:04 | Autoplay: Step 5 -> Step 6 (Resolved)...")
        await asyncio.sleep(8.0)
        print("2:12 | Scenario fully normalized. Observing final network map...")
        await asyncio.sleep(8.0)
        
        print("2:20 | Pausing Autoplay...")
        await smooth_click("button:has-text('PAUSE AUTOPLAY')")
        await asyncio.sleep(2.0)

        # -----------------------------------------------------------------
        #  2:22 - 3:35 | ML RAC Waitlist Predictor Tab
        # -----------------------------------------------------------------
        print("2:22 | Navigating to ML RAC Solver...")
        await smooth_click("button.nav-tab:has-text('ML RAC Solver')")
        await page.wait_for_selector("input", timeout=6000)
        await asyncio.sleep(3.0)

        print("2:25 | Filling waitlist pos input with custom value 45...")
        await page.locator("label:has-text('Waitlist Pos') + input").fill("45")
        await asyncio.sleep(2.0)

        print("2:27 | Filling RAC size input with custom value 18...")
        await page.locator("label:has-text('RAC Size') + input").fill("18")
        await asyncio.sleep(2.0)

        print("2:29 | Filling Days to Go input with custom value 10...")
        await page.locator("label:has-text('Days to Go') + input").fill("10")
        await asyncio.sleep(2.0)

        print("2:31 | Clicking Calculate Confirmation Odds...")
        await smooth_click("button:has-text('Calculate Confirmation Odds')")
        await asyncio.sleep(8.0)  # Wait for SHAP graph and heatmap updates to display

        print("2:39 | Tuning Model parameter: Journey Days Bias (Range slider)...")
        slider_days = page.locator("input[type='range']").nth(0)
        # Move slider value by setting it in javascript and triggering events
        await slider_days.evaluate("el => { el.value = 1.7; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); }")
        await asyncio.sleep(5.0)

        print("2:44 | Tuning Model parameter: Waitlist Weight Bias...")
        slider_wl = page.locator("input[type='range']").nth(1)
        await slider_wl.evaluate("el => { el.value = 1.5; el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); }")
        await asyncio.sleep(5.0)

        print("2:49 | Clicking Calculate Confirmation Odds after bias tuning...")
        await smooth_click("button:has-text('Calculate Confirmation Odds')")
        await asyncio.sleep(8.0)

        print("2:57 | Testing seat auto-upgrade classes...")
        await smooth_click("button:has-text('2AC')")
        await asyncio.sleep(4.0)
        await smooth_click("button:has-text('1AC')")
        await asyncio.sleep(4.0)

        print("3:05 | Comparing predictions against Rajdhani (12301)...")
        # Direct select comparative dropdown (3rd select box)
        await page.locator("select").nth(2).select_option("12301")
        await asyncio.sleep(6.0)

        print("3:11 | Comparing predictions against Vande Bharat (22415)...")
        await page.locator("select").nth(2).select_option("22415")
        await asyncio.sleep(6.0)

        print("3:17 | Hovering over SHAP feature explanation bar items...")
        await smooth_hover("span:has-text('current_waitlist_position')")
        await smooth_hover("span:has-text('days_to_journey')")
        await smooth_hover("span:has-text('current_rac_count')")
        await asyncio.sleep(6.0)

        # -----------------------------------------------------------------
        #  3:35 - 4:10 | Audit Ledger Tab
        # -----------------------------------------------------------------
        print("3:35 | Navigating to Audit Ledger...")
        await smooth_click("button.nav-tab:has-text('Audit Ledger')")
        await page.wait_for_selector(".glass-card", timeout=6000)
        await asyncio.sleep(3.0)

        print("3:38 | Scrolling slowly down ledger blocks table...")
        ledger_body = page.locator("div.glass-card:has(h3:has-text('Cryptographic Audit Ledger'))").first
        if await ledger_body.is_visible():
            box = await ledger_body.bounding_box()
            if box:
                # Move to table center
                await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                
                # Perform timed scrolling steps
                await page.mouse.wheel(0, 180)
                await asyncio.sleep(3.0)
                await page.mouse.wheel(0, 180)
                await asyncio.sleep(3.0)
                await page.mouse.wheel(0, 180)
                await asyncio.sleep(3.0)
                await page.mouse.wheel(0, 180)
                await asyncio.sleep(3.0)
                
                print("3:50 | Scrolling up back to top...")
                await page.mouse.wheel(0, -720)
                await asyncio.sleep(4.0)

        print("3:54 | Hovering over cryptographic block metadata...")
        # Hover over verification hashes or links to show tooltip details
        await smooth_hover("span:has-text('mem-')")
        await asyncio.sleep(6.0)

        # -----------------------------------------------------------------
        #  4:10 - 4:45 | Decision Flow (LangGraph diagram)
        # -----------------------------------------------------------------
        print("4:10 | Navigating to Decision Flow (LangGraph)...")
        await smooth_click("button.nav-tab:has-text('Decision Flow')")
        await asyncio.sleep(4.0)

        print("4:14 | Hovering agent nodes to inspect LangGraph agent details...")
        # Move mouse across agent cards on the page to display responsibilities
        await smooth_hover("h4:has-text('MonitorAgent')")
        await smooth_hover("h4:has-text('ConflictDetector')")
        await smooth_hover("h4:has-text('CascadePredictor')")
        await smooth_hover("h4:has-text('DispatchAgent')")
        await smooth_hover("h4:has-text('NotificationAgent')")
        await smooth_hover("h4:has-text('AuditAgent')")
        await asyncio.sleep(5.0)

        # -----------------------------------------------------------------
        #  4:45 - 5:00 | Return & Reset
        # -----------------------------------------------------------------
        print("4:45 | Returning to Main Telemetry Radar...")
        await smooth_click("button.nav-tab:has-text('Telemetry Radar')")
        await asyncio.sleep(3.0)

        print("4:48 | Resetting system to base nominal state...")
        await smooth_click("button:has-text('Reset')")
        await asyncio.sleep(5.0)

        print("4:53 | Final hover on map...")
        await page.mouse.move(960, 540, steps=8)
        await asyncio.sleep(7.0)

        print("5:00 | Completed walkthrough recording sequence successfully!")
        
        # Close components
        await page.close()
        await context.close()
        await browser.close()
        
        # Save recording
        video_path = await context.pages[0].video.path() if context.pages else None
        if video_path and os.path.exists(video_path):
            final_path = os.path.join(OUTPUT_DIR, "railmind_walkthrough.webm")
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(video_path, final_path)
            print(f"Recording successfully saved to: {final_path}")
        else:
            print("Recording completed successfully.")

if __name__ == "__main__":
    asyncio.run(record_walkthrough())

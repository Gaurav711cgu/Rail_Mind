import os
from playwright.sync_api import sync_playwright

def capture_screenshots():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.abspath(os.path.join(script_dir, "..", "railmind_deck_v4 (4).html"))
    output_dir = os.path.join(script_dir, "slides")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading HTML: {html_path}")
    print(f"Saving to: {output_dir}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Create a page with a typical presentation viewport
        # Standard screen: 1366x768 or 1280x800 or 1920x1080.
        # Let's test on 1366x768 first as it's a common laptop size.
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(2000) # wait for animations/styles to load
        
        # Slide order from the HTML JS
        slide_order = ['slide-1','slide-2','slide-2b','slide-3','slide-4','slide-5','slide-6','slide-7','slide-8','slide-8b','slide-9','slide-10','slide-11','slide-12','slide-13','slide-14','slide-15']
        
        for i, slide_id in enumerate(slide_order, 1):
            # Navigate to the slide
            print(f"Screenshotting Slide {i}: {slide_id}")
            page.evaluate(f"showSlide({i})")
            page.wait_for_timeout(500) # wait for slide transitions
            
            # Take screenshot of the viewport
            screenshot_path = os.path.join(output_dir, f"slide_{i:02d}_{slide_id}.png")
            page.screenshot(path=screenshot_path)
            
        browser.close()
    print("Done screenshotting all slides!")

if __name__ == "__main__":
    capture_screenshots()

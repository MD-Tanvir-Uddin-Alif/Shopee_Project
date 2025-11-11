import random
import time

def play_simulate_human_behavior(page, num_actions=10):
    print("Simulating human-like behavior...")

    for _ in range(num_actions):
        scroll_y = random.randint(100, 800)
        page.evaluate(f"window.scrollBy(0, {scroll_y});")
        time.sleep(random.uniform(0.5, 2))

    elements = page.query_selector_all("div")
    for _ in range(num_actions):
        if elements:
            element = random.choice(elements)
            try:
                element.hover()
                time.sleep(random.uniform(0.5, 2))
            except Exception:
                pass

    print("Human-like actions completed.")
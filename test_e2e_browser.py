import json
import time
import base64
import urllib.request
import subprocess
import os
import websocket

def run_browser_verification():
    # 1. Launch Chrome with DevTools debugging port
    temp_dir = os.path.join(os.environ.get("TEMP", "."), "chrome-urbanflow-profile")
    os.makedirs(temp_dir, exist_ok=True)
    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_exe):
        chrome_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    print(f"[1] Launching headless browser from {chrome_exe} ...")
    proc = subprocess.Popen([
        chrome_exe,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "http://localhost:5173/"
    ])

    try:
        # Wait for debugging port to be ready
        targets = []
        for _ in range(15):
            time.sleep(1.0)
            try:
                req = urllib.request.urlopen("http://localhost:9222/json", timeout=2)
                targets = json.loads(req.read().decode())
                if targets:
                    break
            except Exception:
                pass

        if not targets:
            raise RuntimeError("Could not connect to Chrome DevTools port 9222!")

        page_target = None
        for t in targets:
            if t.get("type") == "page" and "localhost:5173" in t.get("url", ""):
                page_target = t
                break

        if not page_target:
            page_target = [t for t in targets if t.get("type") == "page"][0]

        ws_url = page_target["webSocketDebuggerUrl"]
        print(f"    Connecting to target '{page_target['title']}' via CDP WebSocket...")

        ws = websocket.create_connection(ws_url, timeout=10)
        msg_id = 1

        def send_cdp(method, params=None):
            nonlocal msg_id
            cur_id = msg_id
            msg_id += 1
            payload = {"id": cur_id, "method": method, "params": params or {}}
            ws.send(json.dumps(payload))
            while True:
                resp_raw = ws.recv()
                resp = json.loads(resp_raw)
                if resp.get("id") == cur_id:
                    return resp.get("result", {})

        def evaluate(expression):
            res = send_cdp("Runtime.evaluate", {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True
            })
            if "exceptionDetails" in res:
                raise RuntimeError(f"JS Exception: {res['exceptionDetails']}")
            return res.get("result", {}).get("value")

        # Enable runtime & page
        send_cdp("Runtime.enable")
        send_cdp("Page.enable")

        print("[2] Waiting for page scripts, Leaflet map, and backend API handshake...")
        time.sleep(3.0)

        # 3. Check title & page header
        title = evaluate("document.title")
        print(f"[3] Page title: '{title}'")
        assert "UrbanFlow AI" in title, f"Unexpected title: {title}"

        # 4. Check Map Container
        print("[4] Checking Leaflet map container & dimensions...")
        map_info = evaluate("""
            (() => {
                const el = document.querySelector('.leaflet-container');
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                const polylines = document.querySelectorAll('path.leaflet-interactive').length;
                const markers = document.querySelectorAll('.custom-unit-icon, .custom-incident-icon, .leaflet-marker-icon, circle').length;
                return {
                    exists: true,
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    polylines: polylines,
                    markers: markers
                };
            })()
        """)
        print(f"    Map Info: {map_info}")
        assert map_info is not None, "Leaflet map container not found in DOM!"
        assert map_info["width"] > 200, f"Map width is too small ({map_info['width']})"
        assert map_info["height"] > 200, f"Map height is too small ({map_info['height']})"
        print(f"    Map is successfully loaded with live dimensions: {map_info['width']}x{map_info['height']}px.")

        # 5. Check API connectivity badge in UI
        badge_text = evaluate("""
            (() => {
                const badges = Array.from(document.querySelectorAll('header span, header div'));
                const live = badges.find(b => b.textContent && b.textContent.includes('API Live'));
                return live ? live.textContent.trim() : 'NOT_FOUND';
            })()
        """)
        print(f"[5] Live API Connection Badge in Header: '{badge_text}'")
        assert "API Live" in badge_text, f"Frontend did not connect to backend API: {badge_text}"

        # 6. Click 'Reset' to ensure clean baseline
        print("[6] Clicking 'Reset' button to ensure clean baseline...")
        evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const resetBtn = btns.find(b => b.textContent && b.textContent.trim().toUpperCase() === 'RESET');
                if (resetBtn) resetBtn.click();
            })()
        """)
        time.sleep(1.5)

        # 7. Test Step-by-Step Scenario workflow: Detect Incident
        print("[7] Testing Step-by-Step Incident Triage: Clicking 'Detect Incident'...")
        evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const detectBtn = btns.find(b => b.textContent && b.textContent.includes('Detect Incident'));
                if (detectBtn) detectBtn.click();
            })()
        """)
        time.sleep(2.0)

        # 8. Check Candidate Incident
        inc_status = evaluate("""
            (() => {
                const spans = Array.from(document.querySelectorAll('span, h3, div'));
                const cand = spans.find(s => s.textContent && (s.textContent.includes('candidate') || s.textContent.includes('CANDIDATE')));
                const verifyBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Verify Incident'));
                const rejectBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Reject'));
                return {
                    candidateFound: !!cand,
                    hasVerifyBtn: !!verifyBtn,
                    hasRejectBtn: !!rejectBtn
                };
            })()
        """)
        print(f"[8] Candidate verification UI state: {inc_status}")
        assert inc_status["hasVerifyBtn"], "Verify Incident button not found in candidate state!"
        assert inc_status["hasRejectBtn"], "Reject (False Alarm) button not found in candidate state!"

        # 9. Verify Incident
        print("[9] Clicking 'Verify Incident' to confirm collision...")
        evaluate("""
            (() => {
                const verifyBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Verify Incident'));
                if (verifyBtn) verifyBtn.click();
            })()
        """)
        time.sleep(2.0)

        # 10. Check Dispatch Button appeared
        dispatch_status = evaluate("""
            (() => {
                const dispatchBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Dispatch Emergency Units'));
                return { hasDispatchBtn: !!dispatchBtn };
            })()
        """)
        print(f"[10] Verified state: Dispatch button available: {dispatch_status['hasDispatchBtn']}")
        assert dispatch_status["hasDispatchBtn"], "Dispatch Emergency Units button not present after verification!"

        # 11. Click Dispatch
        print("[11] Clicking 'Dispatch Emergency Units'...")
        evaluate("""
            (() => {
                const dispatchBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Dispatch Emergency Units'));
                if (dispatchBtn) dispatchBtn.click();
            })()
        """)
        time.sleep(2.5)

        # 12. Check Active Emergency Response State
        post_dispatch = evaluate("""
            (() => {
                const resolveBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Resolve Incident'));
                const paths = document.querySelectorAll('path.leaflet-interactive').length;
                return {
                    resolveBtnFound: !!resolveBtn,
                    polylinesOnMap: paths
                };
            })()
        """)
        print(f"[12] Post-dispatch state: {post_dispatch}")
        assert post_dispatch["resolveBtnFound"], "Resolve Incident button not present during active dispatch!"
        assert post_dispatch["polylinesOnMap"] > 10, "Polylines (roads & emergency corridors) not rendered on map!"

        # 13. Resolve Incident
        print("[13] Clicking 'Resolve Incident & Reopen Corridors'...")
        evaluate("""
            (() => {
                const resolveBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Resolve Incident'));
                if (resolveBtn) resolveBtn.click();
            })()
        """)
        time.sleep(2.0)

        # 14. Check resolved state
        final_status = evaluate("""
            (() => {
                const text = document.body.innerText;
                return {
                    allCorridorsClear: text.includes('All Corridors Clear') || text.includes('resolved') || text.includes('Standby')
                };
            })()
        """)
        print(f"[14] Scene resolution confirmed: {final_status}")
        assert final_status["allCorridorsClear"], "Scene resolution not reflected in UI!"

        # 15. Capture high-res screenshot
        print("[15] Capturing full-screen browser screenshot...")
        screenshot_res = send_cdp("Page.captureScreenshot", {"format": "png"})
        if "data" in screenshot_res:
            os.makedirs("assets", exist_ok=True)
            with open("assets/dashboard_verified.png", "wb") as f:
                f.write(base64.b64decode(screenshot_res["data"]))
            print("    Saved browser verification screenshot to 'assets/dashboard_verified.png'")

        ws.close()
        print("\n=======================================================")
        print("ALL REAL BROWSER INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("=======================================================\n")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    run_browser_verification()

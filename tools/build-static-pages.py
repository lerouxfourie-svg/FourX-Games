#!/usr/bin/env python3
"""
Generate the crawlable static pages from index.html.

WHY THIS EXISTS
---------------
The site is a single-page app routed by URL hash, so /privacy, /terms,
/delete-account and /support used to return HTTP 404 — GitHub Pages had no file
at those paths, and 404.html bounced the browser to the hash route with a script.
A human landed on the right page; a machine saw a dead link. That mattered because
those exact URLs are published inside the Privacy Policy and the Terms, Google Play
validates the account-deletion URL before it will accept the Data Safety form, and
Apple wants a privacy policy URL that resolves.

The pages this writes return 200, contain the real text, and need no JavaScript.

WHY IT IS GENERATED AND NOT HAND-WRITTEN
----------------------------------------
Copying the legal text into a second file is how two versions of a binding document
start disagreeing with each other — which had already happened here twice
(FourXGames.dc.html, and the unfilled drafts under uploads/). index.html stays the
single authored source. These pages are DERIVED from it, by rendering the real site
in a headless browser and capturing what it actually produced, so the static copy
cannot say something the site does not.

    python tools/build-static-pages.py

Re-run it after ANY edit to the policy text, the Terms, or the support and
delete-account pages, and commit the result.
"""
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {
    "privacy": "Privacy Policy",
    "terms": "Terms & Conditions",
    "delete-account": "Delete your account",
    "support": "Support & contact",
}
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    found = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    sys.exit("Chrome not found — install it or add its path to CHROME_CANDIDATES.")


def serve(directory):
    """Serve the site locally so the SPA can fetch its own document."""
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=directory, **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


HINT = ("""

  The usual cause is the vendored libraries failing their Subresource Integrity check, which
  blocks React and leaves only index.html's static fallback. On Windows that happens when Git
  rewrites their line endings on checkout. Check:

      openssl dgst -sha384 -binary assets/vendor/react.production.min.js | openssl base64 -A

  against REACT_SRI in support.js. If they differ, .gitattributes is missing or not applied:

      rm -rf assets/vendor && git checkout -- assets/vendor
""")


# A phrase that appears on THAT page and on no other. The size check below cannot tell a right
# page from a wrong one of the same length — and on 2026-08-27 that is exactly what happened: a
# Windows checkout rewrote the vendored React to CRLF, its Subresource Integrity hash stopped
# matching, the browser blocked it, the app never booted, and every slug rendered index.html's
# static <main> fallback — the HOME page, 12,903 characters of it. Four copies of the front page
# would have been written over the privacy policy, terms, deletion and support pages, and the
# guard would have passed all four.
#
# So the guard now asks whether the page IS THE PAGE, which is the question that matters.
MUST_CONTAIN = {
    "privacy":        "POPIA",
    "terms":          "Terms and Conditions",
    "delete-account": "Delete your account",
    "support":        "Support",
}

# ...and text that means we captured the WRONG page, whatever its length.
MUST_NOT_CONTAIN = "Coming late 2026"      # the home-page hero


def render(chrome, url, profile):
    """Let the real page render, then take the DOM it produced."""
    out = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox",
         f"--user-data-dir={profile}", "--virtual-time-budget=12000",
         "--dump-dom", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    return out.stdout


def extract_main(dom):
    m = re.search(r"<main\b[^>]*>(.*?)</main>", dom, re.S | re.I)
    return m.group(1).strip() if m else None


def absolutise(html):
    """The static pages live one directory down, and their links must not be hash routes."""
    html = re.sub(r'href="#([a-z-]+)"', lambda m: f'href="/{m.group(1)}/"'
                  if m.group(1) != "home" else 'href="/"', html)
    html = re.sub(r'\s+onclick="[^"]*"', "", html, flags=re.I)
    html = re.sub(r'\s+data-page="[^"]*"', "", html, flags=re.I)
    html = html.replace('src="assets/', 'src="/assets/')
    return html


SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — FourX Games</title>
<link rel="icon" type="image/svg+xml" href="/assets/fourx-logo.svg">
<link rel="canonical" href="https://www.fourxgames.com/{slug}/">
<!-- GENERATED by tools/build-static-pages.py from index.html — do not edit by hand.
     Edit the text in index.html and re-run the script, or the two will disagree. -->
<style>
  body {{ margin:0; background:#F4F3F1; color:#14264D;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         line-height:1.65; }}
  header, footer {{ background:#14264D; }}
  header a {{ color:#F4F3F1; }}
  footer {{ color:rgba(244,243,241,0.7); font-size:13.5px; }}
  footer a {{ color:rgba(244,243,241,0.7); }}
  .bar {{ max-width:1120px; margin:0 auto; padding:18px 32px; display:flex; gap:20px;
          align-items:center; flex-wrap:wrap; }}
  .bar .brand {{ font-family:Georgia,'Times New Roman',serif; font-size:18px; margin-right:auto; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:48px 32px 88px; }}
  h1 {{ font-family:Georgia,'Times New Roman',serif; font-weight:500; font-size:34px;
        line-height:1.15; margin:0 0 18px; }}
  h2 {{ font-size:20px; margin:32px 0 10px; }}
  h3 {{ font-size:16px; margin:22px 0 8px; }}
  table {{ border-collapse:collapse; width:100%; margin:14px 0; font-size:14px; }}
  th, td {{ border:1px solid #d5dae5; padding:7px 9px; text-align:left; vertical-align:top; }}
  th {{ background:#e8ecf4; }}
  code {{ background:#e8ecf4; padding:1px 4px; border-radius:3px; }}
  a {{ color:#14264D; }}
  blockquote {{ border-left:3px solid #c9d0e0; margin:14px 0; padding:2px 0 2px 14px; color:#41506f; }}
  img {{ max-width:100%; height:auto; }}
</style>
</head>
<body>
<header><div class="bar">
  <span class="brand">FourX Games</span>
  <a href="/">Home</a><a href="/support/">Support</a><a href="/privacy/">Privacy</a>
  <a href="/terms/">Terms</a><a href="/delete-account/">Delete account</a>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="bar">
  <span>FourX Games Proprietary Limited · Reg. 2026/552177/07 · Republic of South Africa</span>
</div></footer>
</body>
</html>
"""


def main():
    chrome = find_chrome()
    httpd, port = serve(ROOT)
    profile = tempfile.mkdtemp(prefix="fourx-render-")
    written = 0
    try:
        for slug, title in PAGES.items():
            dom = render(chrome, f"http://127.0.0.1:{port}/#{slug}", profile)
            body = extract_main(dom)
            if not body or len(body) < 400:
                sys.exit(f"FAILED {slug}: the page rendered {len(body or '')} characters. "
                         "Nothing written — a truncated legal page is worse than none.{}".format(
                             HINT if not body else ""))

            # IDENTITY, not just length. See MUST_CONTAIN above for why this exists.
            needle = MUST_CONTAIN.get(slug)
            if needle and needle not in body:
                sys.exit(f"FAILED {slug}: rendered {len(body)} characters that do not contain "
                         f"{needle!r}. That is not the {slug} page. Nothing written.{HINT}")
            if MUST_NOT_CONTAIN in body:
                sys.exit(f"FAILED {slug}: the render contains {MUST_NOT_CONTAIN!r}, which only "
                         f"appears on the HOME page — the app did not route to #{slug}. "
                         f"Nothing written.{HINT}")
            page = SHELL.format(title=title, slug=slug, body=absolutise(body))
            outdir = os.path.join(ROOT, slug)
            os.makedirs(outdir, exist_ok=True)
            with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(page)
            print(f"  /{slug}/index.html  ({len(page):,} bytes)")
            written += 1
    finally:
        httpd.shutdown()
        shutil.rmtree(profile, ignore_errors=True)
    print(f"{written} static pages generated.")


if __name__ == "__main__":
    main()

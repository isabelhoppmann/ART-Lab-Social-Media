"""Turn WHATEVER Meta token you managed to generate into the Page token we need.

Meta's app UI changes constantly and its Explorer sometimes refuses to hand out the
specific token type a guide asks for ("no configurations available"). So this script
does not care which kind you got. Paste any working token into .env and it will
identify it, upgrade it if it can, and derive the Page token.

Put these in .env (gitignored -- nothing here reaches git or a chat transcript):

    META_TOKEN=<whatever the Explorer gave you>
    META_APP_ID=<App settings -> Basic>
    META_APP_SECRET=<App settings -> Basic -> Show>

App id and secret are optional but strongly preferred: without them a short-lived
token stays short-lived, and the whole point is a Page token that doesn't expire.

    python3 tools/derive_page_token.py                # identify + discover Pages
    python3 tools/derive_page_token.py <PAGE_ID>      # derive the Page token
"""

import json, os, sys, urllib.parse, urllib.request

API = "https://graph.facebook.com/v21.0"
OUT = "/tmp/artlab_page_token.txt"


def env(name):
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def call(path, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API}/{path}?{qs}",
                                 headers={"User-Agent": "ARTLabSetup/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        try:
            return {"__error": json.loads(e.read().decode())["error"]["message"]}
        except Exception:
            return {"__error": str(e)}


def main():
    token   = env("META_TOKEN") or env("META_USER_TOKEN")
    app_id  = env("META_APP_ID")
    secret  = env("META_APP_SECRET")
    if not token:
        sys.exit("No META_TOKEN in .env — paste whatever token the Explorer gave you.")

    # ── What kind of token is this? ──────────────────────────────────────────
    kind, expires = "unknown", None
    if app_id and secret:
        dbg = call("debug_token", {"input_token": token,
                                   "access_token": f"{app_id}|{secret}"})
        d = dbg.get("data", {}) if "__error" not in dbg else {}
        if d:
            kind    = d.get("type", "unknown").lower()
            expires = d.get("expires_at")
            if not d.get("is_valid"):
                sys.exit(f"Meta says this token is not valid: {d.get('error', {}).get('message', '')}")
            print(f"Token type: {kind}   expires: {'never' if not expires else expires}")
            missing = {"pages_read_engagement", "instagram_basic",
                       "instagram_manage_insights"} - set(d.get("scopes", []))
            if missing:
                print(f"⚠️  Missing scopes: {', '.join(sorted(missing))}")
    else:
        print("(No app id/secret in .env — skipping token inspection.)")

    who = call("me", {"access_token": token, "fields": "id,name"})
    if "__error" in who:
        sys.exit(f"Token rejected: {who['__error']}")
    print(f"Token acts as: {who.get('name')} (id {who.get('id')})\n")

    # ── Upgrade a short-lived USER token to a long-lived one ─────────────────
    if kind == "user" and app_id and secret and expires:
        ex = call("oauth/access_token", {
            "grant_type": "fb_exchange_token", "client_id": app_id,
            "client_secret": secret, "fb_exchange_token": token})
        if "access_token" in ex:
            token = ex["access_token"]
            print("Upgraded to a long-lived user token.\n")

    page_id = sys.argv[1] if len(sys.argv) > 1 else None

    # A page token already? Then `me` IS the page and we may be done.
    if not page_id and kind == "page":
        page_id = who.get("id")
        print(f"This is already a Page token for page {page_id}.\n")

    if not page_id:
        accts = call("me/accounts", {"access_token": token,
                                     "fields": "id,name,instagram_business_account"})
        pages = accts.get("data", []) if "__error" not in accts else []
        if not pages:
            print("No Pages listed. This is EXPECTED for Business-Manager-owned Pages")
            print("and is not an error. Get the Page ID from Business Suite, then:")
            print("    python3 tools/derive_page_token.py <PAGE_ID>")
            return
        print("Pages this token can see:\n")
        for p in pages:
            ig = (p.get("instagram_business_account") or {}).get("id")
            print(f"  {p['name']}\n    page_id   = {p['id']}\n    instagram = {ig or 'NOT LINKED'}")
        print("\nRe-run with the Page ID you want:")
        print("    python3 tools/derive_page_token.py <PAGE_ID>")
        return

    info = call(page_id, {"access_token": token,
                          "fields": "name,access_token,instagram_business_account"})
    if "__error" in info:
        sys.exit(f"Couldn't read that Page: {info['__error']}")

    page_token = info.get("access_token") or (token if kind == "page" else None)
    if not page_token:
        sys.exit("No Page token came back — the token likely lacks pages_read_engagement, "
                 "or this account doesn't administer that Page.")

    ig_id = (info.get("instagram_business_account") or {}).get("id")
    print(f"Page:      {info.get('name')}  (id {page_id})")
    print(f"Instagram: {ig_id or 'NOT LINKED'}")

    with open(OUT, "w") as f:
        f.write(page_token)
    os.chmod(OUT, 0o600)
    print(f"\nPage token written to {OUT} (never printed, never committed).")
    print("\nStore it with:")
    print(f"    gh secret set ARTLAB_PAGE_ACCESS_TOKEN < {OUT} && rm {OUT}")

    if ig_id:
        print(f"\nConfirmed link. IDs for the workflow (neither is secret):")
        print(f"    FB_PAGE_ID = {page_id}")
        print(f"    IG_USER_ID = {ig_id}")
    else:
        print("\n⚠️  Instagram is NOT attached to this Page. Facebook numbers will work;")
        print("    Instagram numbers will not until it's linked.")


if __name__ == "__main__":
    main()

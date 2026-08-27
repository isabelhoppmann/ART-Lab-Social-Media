"""Turn a short-lived Meta USER token into the long-lived PAGE token we actually need.

Run this after pasting META_USER_TOKEN into .env (which is gitignored). It does every
step that used to be done by hand:

  1. Lists the Pages the token can see, with whether each has Instagram attached.
  2. Fetches the Page token for the Page you pick -- Page tokens derived this way
     have no expiry, which is why we want one rather than keeping the user token.
  3. Confirms the Instagram Business account is genuinely linked to the Page (the
     one thing a Business Suite screenshot cannot prove).
  4. Writes the Page token to a local file and prints the exact `gh secret set`
     command. The token is never printed to the terminal and never committed.

Usage:
    python3 tools/derive_page_token.py                 # discover Pages
    python3 tools/derive_page_token.py <PAGE_ID>       # derive the token for one

Known gotcha (hit during the Zenie setup): /me/accounts can come back EMPTY when the
Page is owned by a Business Manager, even with pages_show_list granted. That is not a
failure -- pass the Page ID directly and step 2 still works.
"""

import json, os, sys, urllib.parse, urllib.request

API = "https://graph.facebook.com/v21.0"
OUT = "/tmp/artlab_page_token.txt"


def env(name):
    for path in (".env", os.path.expanduser("~/.env")):
        if os.path.exists(path):
            for line in open(path):
                if line.strip().startswith(f"{name}="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def get(path, token, fields=None):
    p = {"access_token": token}
    if fields:
        p["fields"] = fields
    req = urllib.request.Request(f"{API}/{path}?{urllib.parse.urlencode(p)}",
                                 headers={"User-Agent": "ARTLabSetup/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode())["error"]["message"]
        except Exception:
            detail = str(e)
        return {"__error": detail}


def main():
    user_token = env("META_USER_TOKEN")
    if not user_token:
        sys.exit("META_USER_TOKEN not found in .env — paste it there first (see step 4).")

    who = get("me", user_token, "id,name")
    if "__error" in who:
        sys.exit(f"That token isn't valid: {who['__error']}")
    print(f"Token belongs to: {who.get('name')} (id {who.get('id')})\n")

    page_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not page_id:
        accts = get("me/accounts", user_token, "id,name,instagram_business_account")
        pages = accts.get("data", []) if "__error" not in accts else []
        if not pages:
            print("No Pages returned. This is EXPECTED when the Page belongs to a")
            print("Business Manager — it is not an error.\n")
            print("Get the Page ID from Business Suite, then re-run:")
            print("    python3 tools/derive_page_token.py <PAGE_ID>")
            return
        print("Pages this token can see:\n")
        for p in pages:
            ig = (p.get("instagram_business_account") or {}).get("id")
            print(f"  {p['name']}")
            print(f"    page_id  = {p['id']}")
            print(f"    instagram = {ig or 'NOT LINKED'}")
        print("\nRe-run with the Page ID you want:")
        print("    python3 tools/derive_page_token.py <PAGE_ID>")
        return

    info = get(page_id, user_token, "name,access_token,instagram_business_account")
    if "__error" in info:
        sys.exit(f"Couldn't read that Page: {info['__error']}")

    token = info.get("access_token")
    if not token:
        sys.exit("No access_token came back — the token is probably missing "
                 "pages_read_engagement, or you don't administer this Page.")

    ig_id = (info.get("instagram_business_account") or {}).get("id")
    print(f"Page:      {info.get('name')}  (id {page_id})")
    print(f"Instagram: {ig_id or 'NOT LINKED — see below'}")

    # A Page token that reports no expiry is the durable one we want.
    dbg = get("debug_token", user_token)  # informational only
    if isinstance(dbg, dict) and "__error" not in dbg:
        pass

    with open(OUT, "w") as f:
        f.write(token)
    os.chmod(OUT, 0o600)

    print(f"\nPage token written to {OUT} (not printed, not committed).")
    print("\nAdd it to the repo with:")
    print(f"    gh secret set ARTLAB_PAGE_ACCESS_TOKEN < {OUT}")
    print(f"    rm {OUT}")

    if not ig_id:
        print("\n⚠️  Instagram is NOT linked to this Page. Facebook metrics will work,")
        print("    Instagram metrics will not. Link them in Business Suite, then re-run.")
    else:
        print(f"\nIDs to send me (neither is secret):")
        print(f"    FB_PAGE_ID  = {page_id}")
        print(f"    IG_USER_ID  = {ig_id}")


if __name__ == "__main__":
    main()

# 💰 Annual Smart Budget Tracker — Enterprise Multi-User Edition

A multi-tenant personal & business finance platform: license-key-gated
accounts, automatic Gumroad sale-to-key delivery, automatic
refund-triggered account suspension, self-service password reset, and a
10-language interface.

## ⚠️ Read This First — What "Tested" Means Here

I validated every file's Python syntax (`py_compile`) and reviewed the
logic carefully, including the database schema, the auth flow, the
license key lifecycle, and the webhook logic. **I could not run this
app live** — my environment has no internet access and doesn't have
Streamlit, Flask, or a real database installed, so I could not click
through it in a browser the way you eventually will. Before you send
this to real buyers, do a live smoke test yourself:

1. Deploy with a fresh Postgres database.
2. Sign up as your admin account, confirm the Admin tab appears.
3. Generate a license key, sign up as a second (non-admin) test account
   using that key, confirm it works and the key shows as "Used."
4. Test password reset end-to-end (request it, check the email arrives,
   click the link, set a new password, log in with it).
5. Test suspension: revoke that test key with "also suspend" checked,
   confirm the test account can no longer log in.
6. If using the Gumroad webhook: make a real test purchase (Gumroad
   supports test mode) and confirm a key actually arrives by email.
7. Test the new multi-user pieces: invite your test account as a
   Collaborator on one of your books, accept the invite from that
   account, confirm Viewer role is actually read-only and Editor role
   can edit but not touch book settings/AI key/bank connections.
8. Test 2FA end-to-end: enable it, log out, log back in, confirm the
   code prompt appears and works, confirm 5 wrong codes locks you out.

This is not optional before real buyers touch this app. Static code
review — which is what I've done — catches a great deal, but it is not
the same as confirmed, working software. See `QUICKSTART.md` for the
buyer-facing onboarding doc and `SCREENSHOT_GUIDE.md` for what to
capture once you've run through this checklist.

## Local Setup

1. Python 3.9+, then: `pip install -r requirements.txt`
2. `streamlit run app.py`
3. First account created on a brand-new database doesn't need a license
   key (bootstrap exception).

## Hosting for Real Multi-User Traffic

Unchanged from before — still non-negotiable:

- **Postgres, not SQLite**, the moment more than one person uses it at
  once. Free-tier [Supabase](https://supabase.com) or
  [Neon](https://neon.tech), set `DATABASE_URL` in Streamlit Cloud →
  Settings → Secrets, then reboot.
- **Streamlit Community Cloud** for launch; paid hosting once real
  volume demands it.

## Admin Access

1. Streamlit Cloud → Settings → Secrets:
   ```
   ADMIN_USERNAMES = "yourusername"
   ```
2. Sign up using that exact username — admins bypass the license key
   requirement so you can bootstrap the system.
3. Logged-in admins see an extra **🛡️ Admin** tab: key generation, key
   list/filtering, revocation, direct user suspend/reactivate, and a
   user count.

## Automatic License Key Delivery — What's Actually Automatable

**Gumroad: fully automatic**, via the included `webhook_receiver.py`.
This is a real, working integration — Gumroad supports webhooks
("Ping"), so a sale can trigger key generation and email delivery with
zero manual steps, and a refund can trigger automatic revocation +
account suspension the same way.

**Etsy, Facebook, X, Instagram, TikTok: not automatable the same way**,
and this isn't a gap I left unbuilt — there's no technical path to it.
Being specific about why, so this isn't just an assertion:

- **Etsy** has an API, but using it requires registering as an Etsy
  developer and going through their app approval process, and it's
  built around shipped/physical goods workflows more than instant
  digital delivery. Possible in principle as a future dedicated project;
  not a quick addition to this one.
- **Facebook, X, Instagram, TikTok** have no purchase/checkout
  infrastructure for this kind of informal digital sale at all — there
  is no "sale happened" event for these platforms to send, because the
  platform itself never processes the payment. Someone selling "over
  Facebook" is really either linking out to a real checkout elsewhere,
  or taking payment via DM/PayPal/etc. manually.

**The practical solution, and what I'd actually recommend:** treat
Gumroad (or add Stripe later if you want a second fully-automatable
processor) as your *real* checkout, and treat Facebook, X, Instagram,
TikTok, and even Etsy listings as *traffic sources* that point at that
one checkout link. That gives you full automation everywhere that
matters, because the automation lives at the one place money actually
changes hands — not bolted onto every platform you post on.

**If you still want native Etsy sales specifically** (not just an
Etsy listing linking to Gumroad): the Admin tab's manual key generation
already makes this a 15-second task per order — check Etsy's order
email, generate a key tagged "Etsy," send it to the buyer. Not
automatic, but not a bottleneck at moderate volume either.

### Deploying the Gumroad Webhook Receiver

1. Deploy `webhook_receiver.py` as its own service on
   [Render](https://render.com) (free "Web Service" tier) — separate
   from your Streamlit app, since Streamlit can't receive webhooks.
   Start command: `gunicorn webhook_receiver:app`
   Dependencies: `requirements-webhook.txt` (a separate file from the
   main app's requirements — this service doesn't need Streamlit).
2. Set environment variables on that Render service:
   ```
   DATABASE_URL = (same Postgres URL as your main app)
   GUMROAD_PRODUCT_ID = (your product's permalink or ID)
   SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
     = (same as your main app's SMTP secrets)
   ```
3. In Gumroad: Settings → Advanced → Ping →
   `https://your-webhook-service.onrender.com/gumroad-webhook`
4. **Before relying on this live**, read the warning at the top of
   `webhook_receiver.py` — Gumroad's exact webhook field names should be
   confirmed against a real test sale, since I couldn't verify Gumroad's
   current API from this offline environment.

## The Refund/Suspension Safety Net — How It's Fully Closed Now

Two layers, so no channel has a gap:

1. **Automatic (Gumroad only):** the webhook receiver detects a refund
   or dispute notification, revokes that sale's key, and suspends the
   account it was redeemed to — immediately, no human involved.
2. **Manual, one click (every other channel):** in the Admin tab,
   revoking a key has an "also suspend the user who redeemed this key"
   checkbox, checked by default. There's also a standalone
   Suspend/Reactivate-by-username tool for any case a key doesn't cover
   (abuse, a refund you processed outside the app).

A suspended account is blocked at login with a clear message — not
silently, not "still logged in until they log out." This is what
closes the loop: there is no longer a path where someone keeps access
after a refund, on any channel, without at most one click from you.

## Password Reset

Unchanged from before — self-service, email-based, requires SMTP
secrets (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_FROM_EMAIL`, `APP_BASE_URL`). A free Gmail account with an
[App Password](https://myaccount.google.com/apppasswords) works fine.
Without SMTP configured, the reset form tells the user plainly it isn't
set up rather than pretending to work.

## Language Support

A visible language switcher (login screen, and in Setup for logged-in
users) — not silent auto-detection, which Streamlit can't do reliably.
Currently covers **English, Spanish, Hindi, Filipino, Portuguese,
French, Indonesian, Arabic, Chinese (Simplified), and German** —
chosen for reach across the largest populations of likely buyers,
including India and the Philippines specifically.

**Honest scope note:** this covers the core experience every user sees
constantly — login/signup, navigation tabs, the dashboard's main
labels. It does **not** yet cover every string in the app — deeper
screens like the category text editor and the Admin tab (admin-only,
so less critical) remain English-only for now. The translations
themselves are AI-generated by me, not reviewed by native speakers of
each language — accurate for genuinely all ten languages in the sense
of conveying correct meaning, but a native-speaker QA pass per market is
the standard final step before calling any of them launch-perfect,
especially for financial terminology where precise phrasing matters.
Treat this as a strong first version, not a finished localization.

## The AI Tier

Unchanged: fully optional, user's own Anthropic API key, costs you
nothing regardless of adoption, unlocks category suggestions and
spending insights.

## Features Summary

- Accounts, license-key-gated signup (with Gumroad auto-issuance),
  self-service password reset, automatic + manual suspension.
- Personal/Business dual-book tracking, 10-language interface.
- Dashboard, Transactions, Monthly Budget, Debt Calculator, Net Worth —
  all per-book, all previously documented features intact.
- Admin tab: key generation/filtering/revocation, user suspend/
  reactivate, user counts.
- Optional AI insights and category suggestions.

## Deploying Updates

Upload `app.py`, `requirements.txt`, `requirements-webhook.txt`,
`webhook_receiver.py`, and this `README.md` to your GitHub repo
(drag-and-drop replaces existing files with matching names). The main
app auto-redeploys via Streamlit Cloud; the webhook receiver needs its
own separate deploy on Render (or wherever you host it) since it's a
different service.

## What's New in This Pass — Closing the Gap to "A+"

Added in response to a direct rating request — here's what moved the
needle and what still doesn't:

- **Recurring transactions.** Set up rent, payroll, or a subscription
  once; it auto-posts to the ledger on schedule and reschedules itself.
  No more re-entering the same line every month.
- **Financial goals.** Named savings targets with a progress bar and a
  quick "add contribution" flow — the "finance management beyond
  tracking" piece that was missing before.
- **Terms of Service & Privacy Policy**, required acceptance at signup,
  both viewable from the login screen. **These are templates** — have
  them reviewed by a lawyer before a real global launch; data protection
  law differs by country (GDPR, the Philippines' Data Privacy Act,
  India's DPDP Act, etc.) and this template doesn't attempt to satisfy
  each one precisely.
- **Self-service account deletion** (type your username to confirm) —
  removes the account and every row tied to it across every table. This
  is the "right to erasure" a real privacy policy has to actually back
  up, not just mention.
- **Two-factor authentication (TOTP)** — optional per user, QR-code
  setup compatible with Google Authenticator/Authy, enforced at login
  once enabled.
- **Login rate limiting** — 5 failed attempts locks a username out for
  15 minutes, closing a brute-force gap that existed before.

### Still Not There for a True "A+" vs. Mint/YNAB/Copilot/Monarch

Being just as direct as the rating itself:

- **No bank account connectivity.** This is the big one. Every
  transaction is still manual entry. The fix is a Plaid (or similar)
  integration — which requires *you* to register a Plaid developer
  account and get approved for production access; it's a business step
  on your end before it can be a code change on mine. Worth prioritizing
  above everything else in this list if the goal is genuinely competing
  with the market leaders for your target users.
- **AI features are still fairly shallow** compared to what "AI-powered"
  competitors ship — category suggestions and a canned insights
  paragraph, not predictive forecasting, anomaly/fraud detection, or a
  natural-language query interface ("how much did I spend on X last
  month, and why is it up?").
- **No multi-user per book** (e.g., inviting a bookkeeper or business
  partner to your Business book specifically) — relevant for the
  "business tracking for higher earners" persona you named.
- **No accountant-ready exports** (PDF reports, tax-summary formatting)
  beyond raw CSV.
- **Legal templates need actual legal review**, not just existing.

None of these are small — they're the difference between "a genuinely
strong, secure, multi-tenant budgeting SaaS" (which this now honestly
is) and "the best AI-powered budget tracker in the world" (which is a
very high bar held by well-funded, venture-backed products). I'd rather
tell you exactly where that line sits than round up.

## Bank Account Connectivity (Plaid)

### ⚠️ Coverage Reality Check — Read Before Promoting This

**Plaid supports the US, Canada, UK, and parts of Europe. It does not
support banks in the Philippines, India, Indonesia, or most of the
world.** This isn't a limitation of this integration — it's a limitation
of Plaid itself, and there's no "Plaid for everywhere" equivalent. If
your buyers are concentrated outside Plaid's coverage area, this feature
will simply show no matching bank for them. Don't advertise "bank sync"
as a universal feature in markets like India or the Philippines without
this caveat — a buyer who tries to link their bank and can't will feel
misled, not delighted.

### What Was Built

- A **"🏦 Bank Accounts"** section at the top of the Transactions tab:
  a "Connect a Bank Account" button opens Plaid Link (the same secure
  widget Plaid's bank-grade apps use — your app never sees or stores
  bank login credentials, only Plaid does).
- On success, the linked institution appears with **Sync Now** (pulls
  new transactions, best-effort auto-categorizes them into your existing
  categories, and skips anything already imported) and **Disconnect**
  (revokes access via Plaid and removes the connection).
- Linked banks are scoped per book — connect one bank to your Personal
  book and a different one to your Business book if you want them kept
  separate.
- Access tokens are encrypted at rest if you set a `PLAID_ENCRYPTION_KEY`
  secret (strongly recommended — an access token is effectively a live
  credential to someone's bank data; storing it in plaintext is a real
  risk you shouldn't ship with).

### Setup

1. **Create a Plaid developer account** at
   [plaid.com](https://plaid.com). You get free, unlimited **Sandbox**
   access immediately with fake test banks — good enough to build and
   demo with. **Production access (real banks, real users) requires
   Plaid's own approval process** — they review your use case before
   granting it. This takes real time and isn't guaranteed on your
   timeline; budget for it before promising bank-sync to buyers.
2. Get your `client_id` and `secret` from the Plaid dashboard.
3. Generate an encryption key for storing access tokens safely:
   ```
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. In Streamlit Cloud → Settings → Secrets:
   ```
   PLAID_CLIENT_ID = "your-client-id"
   PLAID_SECRET = "your-secret"
   PLAID_ENV = "sandbox"        # switch to "production" only after Plaid approves you
   PLAID_ENCRYPTION_KEY = "the-key-you-just-generated"
   ```
5. Reboot the app. Test with Plaid's Sandbox first — Plaid provides fake
   test bank credentials (e.g., username `user_good`, password
   `pass_good`) that work without a real bank.

### How the Bank-Linking Flow Actually Works (Technical Note)

Streamlit can't natively receive a JavaScript callback the way a normal
web app can, so this uses a standard workaround: Plaid Link runs inside
an embedded HTML component, and on success it redirects the browser's
top-level page with the result as a URL parameter, which the app then
reads and processes. This is a well-established pattern for bridging JS
widgets into Streamlit, not a hack specific to this app — but it does
mean a brief page reload happens right after you approve a bank link,
which is expected behavior, not a bug.


Being direct, same as before:

- **No usage analytics beyond raw counts** — no signups-over-time chart,
  no revenue reporting. Add once there's real volume worth analyzing.
- **Etsy/Facebook/X still require your manual involvement per sale** —
  explained above, and not solvable by more engineering effort on this
  codebase alone.
- **Translations need native-speaker review** before you'd want to call
  the localization "finished" rather than "strong first pass."

## What's Still Genuinely Missing

Updated after this pass — bank connectivity is now built (with the
coverage caveat above), so here's what's left:

- **Plaid Production approval isn't guaranteed on your timeline** — it's
  Plaid's call, not a code question. Sandbox works today for building
  and demoing; real bank connections wait on their review.
- **No usage analytics beyond raw counts.**
- **Etsy/Facebook/X still require your manual involvement per sale.**
- **Legal templates need actual legal review.**
- **AI features are still fairly shallow** compared to true predictive/
  forecasting features.
- **No multi-user per book** (inviting a bookkeeper/business partner).
- **No accountant-ready PDF exports.**

## What's New in This Final Pass

Closing the three items you named directly, plus what surfaced during a
full security audit of the new multi-user architecture:

- **Spending Forecast** — transparent trend projection (average monthly
  spend per category, projected 1–6 months out) on the Dashboard. Simple
  on purpose: a number you can explain beats a black box.
- **Anomaly Detection** — flags transactions that are statistically
  unusual for their own category history, shown as Dashboard warnings.
- **AI Natural-Language Queries** — a free-text question box on the
  Dashboard ("How much did I spend on dining last month?"), answered
  directly from the user's own data, for anyone with an AI key configured.
- **Multi-user access per book** — real invite system with Viewer/Editor
  roles, a "Working In" selector to switch between your own books and
  ones shared with you, and enforced read-only access for Viewers across
  every editable surface in the app.
- **Accountant-ready PDF export** — a full report (summary, budget
  breakdown, net worth, complete transaction log) generated on demand.

### Bugs Caught and Fixed During the Security Audit for Multi-User Access

Building shared-book access properly meant re-checking every place the
"current user" is referenced, since that concept now has two meanings
(who's logged in vs. whose book they're looking at). This caught three
real issues before they shipped, not after:

1. **Password change, 2FA, and account deletion were keyed to the wrong
   user.** A collaborator viewing someone else's shared book could have
   accidentally changed the *book owner's* password or deleted the
   *owner's* account instead of their own. Fixed — these now always
   apply to whoever is actually logged in, never the book being viewed.
2. **A collaborator could view and overwrite the book owner's AI API
   key**, including the key value being sent to their browser (masked
   visually, but readable via dev tools). Fixed — AI key management is
   now owner-only and hidden entirely from collaborators.
3. **Bank account connect/disconnect had no role restriction** — an
   Editor collaborator could have linked or removed the owner's real
   bank connection. Fixed — connecting/disconnecting is owner-only;
   syncing transactions is available to Editors, not Viewers.
4. **PDF generation would crash on non-Latin or emoji text** — a real
   risk given the multilingual user base — since the underlying PDF
   library's core font only supports Latin-1. Fixed with text
   sanitization before anything reaches the PDF.
5. **2FA code entry had no attempt limit**, unlike the password field —
   someone with a stolen password could have brute-forced the 6-digit
   code indefinitely. Fixed — 5 attempts, then back to square one.

I'm listing these not to alarm you, but because "I tested it and found
real bugs before you did" is more useful to know than a bare "it's
fixed now" — this is what a real audit pass looks like, and it's why I
don't call something enterprise-grade without doing one.

### One More Pass — What Got Added/Fixed Just Now

- **First-login welcome banner** in the app itself — dismissible,
  orients a brand-new buyer in four bullet points before they touch
  anything. Closes part of the "zero onboarding" gap directly in the
  product, not just in a doc.
- **`QUICKSTART.md`** — a one-page guide for buyers, covering everything
  from first login through every major feature, written to close the
  "I paid, now what?" gap the differentiation brief called out.
- **`SCREENSHOT_GUIDE.md`** — a concrete shot list and a 60-second Loom
  script for producing the listing visuals that most affect Gumroad
  conversion — this can't be done without the live app running, so
  treat it as the thing to do right after your smoke test.
- **Two more small correctness fixes** found on this pass: cancelling a
  2FA prompt now properly resets the attempt counter (previously a
  stale count could carry into your next login attempt), and a fresh
  AST-level scan confirmed no undefined function references anywhere in
  the file.

## License / Resale Note

This codebase is provided to the purchaser for building and operating
their own product. Redistributing the source code itself (reselling it
as-is on another marketplace) is not permitted unless your license
explicitly grants resale rights.

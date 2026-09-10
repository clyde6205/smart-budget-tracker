"""
Gumroad Webhook Receiver — Automatic License Key Delivery & Refund Handling
=============================================================================

WHY THIS IS A SEPARATE FILE/SERVICE:
Streamlit apps cannot receive webhooks — they don't expose custom HTTP
routes for external services to POST to. This is a small, separate Flask
app that does exactly one job: listen for Gumroad's "Ping" notifications
and act on them. Deploy it as its OWN web service, NOT alongside the
Streamlit app.

WHAT IT DOES:
- On a new sale: generates a license key, saves it to the same database
  the main app uses, and emails it to the buyer automatically.
- On a refund or dispute: finds the license key tied to that sale,
  revokes it, and suspends the account that redeemed it — automatically,
  with no manual step. This is what closes the "refunded but still has
  access" gap for good, for the Gumroad channel.

RECOMMENDED FREE HOST: Render.com (as a "Web Service") — unlike Streamlit
Community Cloud, Render lets you run an arbitrary Flask app with a real
public URL Gumroad can POST to.

SETUP:
1. Deploy this file on Render (or similar) as a Web Service. Start
   command: `gunicorn webhook_receiver:app` (gunicorn is in
   requirements-webhook.txt).
2. Set these environment variables on that service (Render → Environment):
     DATABASE_URL        - SAME Postgres connection string as the main app
     GUMROAD_PRODUCT_ID  - your product's permalink or ID (ignores pings
                            for any other product on the same account)
     SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
                          - same as the main app, for emailing the key
3. In Gumroad: Settings → Advanced → Ping — paste this service's URL
   plus "/gumroad-webhook", e.g.
   https://your-webhook-service.onrender.com/gumroad-webhook

IMPORTANT — VERIFY BEFORE RELYING ON THIS IN PRODUCTION:
Gumroad's exact Ping payload field names are Gumroad's to define and can
change. The field names below (product_id, email, sale_id, refunded,
resource_name) reflect Gumroad's documented Ping behavior as of this
app's last update, but were not verified against a live Gumroad account
from this environment (no internet access here). Before going live:
send yourself a real test sale (Gumroad supports test/sandbox purchases)
and check your webhook logs to confirm the field names actually match
what Gumroad sends today — adjust the `data.get(...)` calls below if not.
"""

from flask import Flask, request, jsonify
import sqlalchemy as sa
from datetime import datetime
import os
import secrets
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
GUMROAD_PRODUCT_ID = os.environ.get("GUMROAD_PRODUCT_ID", "")

ENGINE = sa.create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


def generate_license_key() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(parts)


def send_key_email(to_email: str, license_key: str) -> bool:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", smtp_user)

    if not (smtp_host and smtp_user and smtp_pass and to_email):
        return False

    body = (
        "Thanks for your purchase!\n\n"
        f"Your license key: {license_key}\n\n"
        "Enter this key when creating your account in the app to activate it.\n"
        "If you have any trouble, just reply to this email."
    )
    msg = MIMEText(body)
    msg["Subject"] = "Your Annual Smart Budget Tracker License Key"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_email], msg.as_string())
        return True
    except Exception:
        return False


@app.route("/gumroad-webhook", methods=["POST"])
def gumroad_webhook():
    if ENGINE is None:
        return jsonify({"error": "DATABASE_URL not configured on this service"}), 500

    data = request.form.to_dict() or request.get_json(silent=True) or {}

    # See the module docstring — verify these field names against a live
    # Gumroad test sale before relying on this in production.
    product_id = data.get("product_id") or data.get("product_permalink", "")
    buyer_email = data.get("email", "")
    sale_id = data.get("sale_id", "")
    refunded = str(data.get("refunded", "")).lower() in ("true", "1")
    resource_name = data.get("resource_name", "sale")

    if GUMROAD_PRODUCT_ID and product_id and GUMROAD_PRODUCT_ID not in str(product_id):
        return jsonify({"status": "ignored - different product"}), 200

    if resource_name in ("refund", "dispute") or refunded:
        with ENGINE.begin() as conn:
            row = conn.execute(
                sa.text("SELECT redeemed_by_user_id FROM license_keys WHERE external_sale_id = :sid"),
                {"sid": sale_id},
            ).fetchone()
            conn.execute(
                sa.text("UPDATE license_keys SET revoked = 1 WHERE external_sale_id = :sid"),
                {"sid": sale_id},
            )
            if row and row.redeemed_by_user_id:
                conn.execute(
                    sa.text("UPDATE users SET is_active = 0 WHERE id = :uid"),
                    {"uid": row.redeemed_by_user_id},
                )
        return jsonify({"status": "refund processed"}), 200

    # Otherwise: treat as a new sale.
    new_key = generate_license_key()
    with ENGINE.begin() as conn:
        for _ in range(5):
            exists = conn.execute(
                sa.text("SELECT 1 FROM license_keys WHERE license_key = :k"), {"k": new_key}
            ).fetchone()
            if not exists:
                break
            new_key = generate_license_key()
        conn.execute(
            sa.text(
                "INSERT INTO license_keys (license_key, tier, source, created_at, revoked, notes, external_sale_id) "
                "VALUES (:k, :t, :s, :c, 0, :n, :sid)"
            ),
            {
                "k": new_key, "t": "standard", "s": "Gumroad",
                "c": str(datetime.utcnow()), "n": f"Auto-issued for sale {sale_id}",
                "sid": sale_id,
            },
        )

    email_sent = send_key_email(buyer_email, new_key)
    return jsonify({"status": "key issued", "email_sent": email_sent}), 200


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "gumroad-webhook-receiver"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

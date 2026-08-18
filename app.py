import difflib
import json
import os
import re
from datetime import datetime

import requests
import stripe
from dotenv import load_dotenv
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import CSRFProtect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import inspect, text

import note_generator as ng
from models import Client, GeneratedNote, SavedNote, User, db

MAX_NOTE_SIMILARITY = 0.69
MAX_GENERATION_ATTEMPTS = 15
SIMILARITY_CORPUS_LIMIT = 100
PASSWORD_RESET_MAX_AGE = 3600  # 1 hour

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OPTIONS_PATH = os.path.join(BASE_DIR, "default_options.json")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "")

def _clean_secret(value):
    # Env vars pasted through a browser/dashboard UI can pick up invisible
    # characters (smart quotes, zero-width spaces, non-breaking spaces) that
    # aren't valid Latin-1 and crash Stripe's HTTP client when used in a
    # header. Strip anything outside printable ASCII rather than trust the
    # source to be clean.
    return "".join(c for c in value.strip() if 32 <= ord(c) < 127)


STRIPE_SECRET_KEY = _clean_secret(os.environ.get("STRIPE_SECRET_KEY", ""))
STRIPE_PRICE_ID = _clean_secret(os.environ.get("STRIPE_PRICE_ID", ""))
# Support more than one signing secret: Stripe issues a separate secret per event
# destination, and a Stripe account can easily end up with several destinations
# (one per event type) instead of one destination listening to every event.
STRIPE_WEBHOOK_SECRETS = [
    v for v in (
        _clean_secret(os.environ.get("STRIPE_WEBHOOK_SECRET", "")),
        _clean_secret(os.environ.get("STRIPE_WEBHOOK_SECRET_2", "")),
        _clean_secret(os.environ.get("STRIPE_WEBHOOK_SECRET_3", "")),
        _clean_secret(os.environ.get("STRIPE_WEBHOOK_SECRET_4", "")),
    ) if v
]
# The app owner's login email is auto-exempted from the paywall so the account
# that generated notes before billing existed never loses access to its own data.
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "").strip().lower()
stripe.api_key = STRIPE_SECRET_KEY

def _normalized_database_url():
    url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")
    # Render/Heroku hand out "postgres://" or "postgresql://"; route either to the
    # psycopg3 driver explicitly, since SQLAlchemy's default dialect assumes psycopg2.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = _normalized_database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
# 1 MB is generous for this app's JSON/text payloads; blocks large-body abuse of
# unauthenticated or lightly-limited endpoints (e.g. signup, login).
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

db.init_app(app)
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.after_request
def _set_security_headers(response):
    # This app has no inline <script> or external script sources, and no iframe
    # use, so the policy can stay strict without an allowlist to maintain.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self' https://checkout.stripe.com https://billing.stripe.com"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(self)"
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required."}), 401
    return redirect(url_for("login"))


def _default_options_text():
    with open(DEFAULT_OPTIONS_PATH) as f:
        return f.read()


def _ensure_table_columns(table, additions):
    """Add columns introduced after the initial schema, since this app has no
    migration framework. Safe to run every startup: only issues ALTER TABLE for
    columns that don't already exist, on both SQLite and Postgres."""
    inspector = inspect(db.engine)
    existing = {col["name"] for col in inspector.get_columns(table)}
    missing = {name: col_type for name, col_type in additions.items() if name not in existing}
    if not missing:
        return missing
    with db.engine.begin() as conn:
        for name, col_type in missing.items():
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {name} {col_type}'))
    return missing


with app.app_context():
    db.create_all()
    _missing_user_cols = _ensure_table_columns("user", {
        "stripe_customer_id": "VARCHAR(255)",
        "stripe_subscription_id": "VARCHAR(255)",
        "subscription_status": "VARCHAR(30)",
    })
    if "subscription_status" in _missing_user_cols:
        with db.engine.begin() as conn:
            conn.execute(text('UPDATE "user" SET subscription_status = :status WHERE subscription_status IS NULL'), {"status": "inactive"})
    _ensure_table_columns("client", {"antecedents": "JSON"})


# ---------- Auth ----------

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    practice_name = (request.form.get("practice_name") or "").strip()

    if not email or not password:
        return render_template("signup.html", error="Email and password are required."), 400
    if len(password) < 8:
        return render_template("signup.html", error="Password must be at least 8 characters."), 400
    if User.query.filter_by(email=email).first():
        return render_template("signup.html", error="An account with that email already exists."), 400

    user = User(email=email, practice_name=practice_name, options_json=_default_options_text())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return render_template("login.html", error="Invalid email or password."), 401

    login_user(user)
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


def _reset_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="password-reset")


def _generate_reset_token(user):
    # Embedding a fingerprint of the current password hash means the token is
    # implicitly single-use: once the password changes, old tokens stop matching.
    return _reset_serializer().dumps({"uid": user.id, "h": user.password_hash[-12:]})


def _verify_reset_token(token):
    try:
        data = _reset_serializer().loads(token, max_age=PASSWORD_RESET_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(User, data.get("uid"))
    if not user or user.password_hash[-12:] != data.get("h"):
        return None
    return user


def _send_reset_email(user, reset_url):
    if not RESEND_API_KEY:
        app.logger.warning("RESEND_API_KEY is not set; skipping password reset email.")
        return False
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [user.email],
                "subject": "Reset your Powerful Notes password",
                "html": (
                    "<p>Someone requested a password reset for your Powerful Notes account.</p>"
                    f'<p><a href="{reset_url}">Click here to reset your password</a>. '
                    "This link expires in 1 hour.</p>"
                    "<p>If you didn't request this, you can safely ignore this email.</p>"
                ),
            },
            timeout=10,
        )
        return response.ok
    except requests.RequestException:
        app.logger.exception("Failed to send password reset email.")
        return False


@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html", support_email=SUPPORT_EMAIL)

    email = (request.form.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first() if email else None
    if user:
        token = _generate_reset_token(user)
        reset_url = url_for("reset_password", token=token, _external=True)
        _send_reset_email(user, reset_url)

    # Always show the same message whether or not the account exists, so this
    # endpoint can't be used to discover which emails have accounts.
    return render_template(
        "forgot_password.html",
        support_email=SUPPORT_EMAIL,
        message="If an account exists for that email, we've sent a password reset link. It expires in 1 hour.",
    )


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = _verify_reset_token(token)
    if not user:
        return render_template("reset_password.html", invalid=True)

    if request.method == "GET":
        return render_template("reset_password.html", invalid=False)

    password = request.form.get("password") or ""
    confirm = request.form.get("confirm_password") or ""
    if len(password) < 8:
        return render_template("reset_password.html", invalid=False, error="Password must be at least 8 characters."), 400
    if password != confirm:
        return render_template("reset_password.html", invalid=False, error="Passwords do not match."), 400

    user.set_password(password)
    db.session.commit()
    return redirect(url_for("login"))


# ---------- Billing ----------

def _is_subscribed(user):
    if OWNER_EMAIL and user.email == OWNER_EMAIL:
        return True
    return user.subscription_status == "active"


def _get_or_create_stripe_customer(user):
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
    user.stripe_customer_id = customer.id
    db.session.commit()
    return customer.id


# Endpoints reachable without an active subscription: auth, the paywall/billing
# flow itself, and account settings (so a canceled subscriber can still resubscribe).
PUBLIC_ENDPOINTS = {
    "landing", "terms", "privacy", "signup", "login", "logout", "forgot_password", "reset_password",
    "subscribe", "billing_checkout", "billing_success", "billing_portal", "billing_webhook",
    "account", "service_worker", "static",
}


@app.before_request
def _require_active_subscription():
    if not current_user.is_authenticated:
        return None
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if _is_subscribed(current_user):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "An active subscription is required.", "subscribe_url": url_for("subscribe")}), 402
    return redirect(url_for("subscribe"))


def _is_native_app_request():
    # Apple/Google app review policy requires digital subscriptions to be sold
    # through the platform's own in-app purchase system, not an external payment
    # flow shown inside the app. The mobile wrapper apps identify themselves via
    # a custom User-Agent suffix (see mobile/capacitor.config.json) so the web
    # app can act as a "reader app": new subscriptions can only be started from
    # a browser, never from inside the iOS/Android app itself.
    return "PowerfulNotesNativeApp" in request.headers.get("User-Agent", "")


@app.route("/subscribe")
@login_required
def subscribe():
    if _is_subscribed(current_user):
        return redirect(url_for("index"))
    return render_template(
        "subscribe.html",
        status=current_user.subscription_status,
        stripe_error=request.args.get("stripe_error", ""),
        is_native_app=_is_native_app_request(),
    )


@app.route("/billing/checkout", methods=["POST"])
@login_required
def billing_checkout():
    if _is_native_app_request():
        abort(403, description="Subscriptions can only be started from powerfulnotes.com in a web browser.")
    if not STRIPE_PRICE_ID:
        abort(500, description="Billing is not configured yet.")
    try:
        customer_id = _get_or_create_stripe_customer(current_user)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=url_for("billing_success", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("subscribe", _external=True),
            client_reference_id=str(current_user.id),
        )
    except stripe.error.StripeError as e:
        app.logger.exception("Stripe checkout session creation failed.")
        return redirect(url_for("subscribe", stripe_error=str(e)))
    return redirect(session.url, code=303)


@app.route("/billing/success")
@login_required
def billing_success():
    # The webhook is the source of truth for subscription state, but confirming
    # the session here too means the paywall lifts immediately instead of
    # waiting on webhook delivery.
    session_id = request.args.get("session_id")
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.customer == current_user.stripe_customer_id and session.subscription:
                current_user.stripe_subscription_id = session.subscription
                current_user.subscription_status = "active"
                db.session.commit()
        except stripe.error.StripeError:
            app.logger.exception("Failed to confirm checkout session.")
    return redirect(url_for("index"))


@app.route("/billing/portal", methods=["POST"])
@login_required
def billing_portal():
    if not current_user.stripe_customer_id:
        return redirect(url_for("subscribe"))
    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=url_for("account", _external=True),
    )
    return redirect(session.url, code=303)


@app.route("/webhooks/stripe", methods=["POST"])
@csrf.exempt
def billing_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    event = None
    for secret in STRIPE_WEBHOOK_SECRETS:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
            break
        except stripe.error.SignatureVerificationError:
            continue
        except ValueError:
            return "", 400
    if event is None:
        return "", 400

    obj = event["data"]["object"]
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        user = User.query.filter_by(stripe_customer_id=obj.get("customer")).first()
        if user and obj.get("subscription"):
            user.stripe_subscription_id = obj["subscription"]
            user.subscription_status = "active"
            db.session.commit()
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        user = User.query.filter_by(stripe_customer_id=obj.get("customer")).first()
        if user:
            user.stripe_subscription_id = obj.get("id")
            status = obj.get("status")
            user.subscription_status = "active" if status in ("active", "trialing") else (status or "inactive")
            db.session.commit()
    elif event_type == "customer.subscription.deleted":
        user = User.query.filter_by(stripe_customer_id=obj.get("customer")).first()
        if user:
            user.subscription_status = "canceled"
            db.session.commit()
    elif event_type == "invoice.payment_failed":
        user = User.query.filter_by(stripe_customer_id=obj.get("customer")).first()
        if user and user.subscription_status == "active":
            user.subscription_status = "past_due"
            db.session.commit()

    return jsonify({"received": True})


# ---------- App ----------

@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("landing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html", support_email=SUPPORT_EMAIL)


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", support_email=SUPPORT_EMAIL)


@app.route("/app")
@login_required
def index():
    return render_template("index.html", practice_name=current_user.practice_name or current_user.email)


def _account_billing_context():
    return {
        "subscribed": _is_subscribed(current_user),
        "subscription_status": current_user.subscription_status,
        "has_stripe_customer": bool(current_user.stripe_customer_id),
        "is_owner": bool(OWNER_EMAIL and current_user.email == OWNER_EMAIL),
    }


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "GET":
        return render_template(
            "account.html", email=current_user.email, practice_name=current_user.practice_name, **_account_billing_context()
        )

    new_email = (request.form.get("email") or "").strip().lower()
    practice_name = (request.form.get("practice_name") or "").strip()
    current_password = request.form.get("current_password") or ""

    def _rerender(error):
        return render_template(
            "account.html",
            email=current_user.email,
            practice_name=current_user.practice_name,
            error=error,
            **_account_billing_context(),
        ), 400

    if not current_user.check_password(current_password):
        return _rerender("Current password is incorrect.")
    if not new_email:
        return _rerender("Email is required.")
    if new_email != current_user.email and User.query.filter_by(email=new_email).first():
        return _rerender("An account with that email already exists.")

    current_user.email = new_email
    current_user.practice_name = practice_name
    db.session.commit()
    return render_template(
        "account.html",
        email=current_user.email,
        practice_name=current_user.practice_name,
        message="Changes saved.",
        **_account_billing_context(),
    )


@app.route("/sw.js")
def service_worker():
    response = app.send_static_file("sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/api/options")
@login_required
def api_options():
    return jsonify(json.loads(current_user.options_json))


# Categories a user can extend from the UI's "Add one manually..." row. Excludes
# place_of_service, which is a plain string list handled separately via an
# "Other (specify)" text field rather than an id/label catalog entry.
CUSTOM_OPTION_CATEGORIES = {
    "replacement_programs", "maladaptive_behaviors", "antecedents", "intervention_strategies",
    "environmental_changes", "medical_concerns", "intervention_effectiveness", "protocol_modifications",
    "data_collection_methods", "client_engagement", "observation_methods", "session_ratings",
    "protocol_fidelity", "rbt_strengths", "rbt_feedback_areas", "caregiver_training_topics",
    "teaching_methods", "caregiver_competency", "caregiver_response", "training_barriers",
    "referral_reasons", "assessment_methods", "treatment_intensity", "recommended_services",
    "progress_ratings", "reassessment_recommendations",
}

# Categories whose items are consumed as a descriptive "blurb" clause somewhere in a
# generated note (not just as a plain label in a joined list) - custom entries here get
# a blurb derived from the label so they read correctly wherever that clause is used.
BLURB_CATEGORIES = {
    "maladaptive_behaviors", "caregiver_training_topics", "caregiver_response", "training_barriers",
    "client_engagement", "session_ratings", "protocol_fidelity", "caregiver_competency",
    "treatment_intensity", "progress_ratings", "intervention_effectiveness", "protocol_modifications",
}


@app.route("/api/options/custom", methods=["POST"])
@login_required
def api_add_custom_option():
    body = request.get_json(force=True)
    category = body.get("category")
    label = (body.get("label") or "").strip()
    if category not in CUSTOM_OPTION_CATEGORIES:
        return jsonify({"error": f"category must be one of {sorted(CUSTOM_OPTION_CATEGORIES)}."}), 400
    if not label:
        return jsonify({"error": "label is required."}), 400

    options = json.loads(current_user.options_json)
    items = options.setdefault(category, [])

    slug = "_".join(filter(None, "".join(c if c.isalnum() else "_" for c in label.lower()).split("_")))
    base_id = f"custom_{slug}" if slug else "custom_item"
    existing_ids = {i["id"] for i in items}
    new_id = base_id
    suffix = 2
    while new_id in existing_ids:
        new_id = f"{base_id}_{suffix}"
        suffix += 1

    item = {"id": new_id, "label": label}
    if category == "replacement_programs":
        item["blurbs"] = [f"the RBT ran {label[0].lower() + label[1:]}, with prompting and reinforcement provided as needed"]
    elif category == "maladaptive_behaviors":
        item["blurbs"] = [f"{label[0].lower() + label[1:]}," if label else label]
    elif category in BLURB_CATEGORIES:
        item["blurb"] = label[0].lower() + label[1:] if label else label

    items.append(item)
    current_user.options_json = json.dumps(options)
    db.session.commit()

    return jsonify(item), 201


@app.route("/api/options/custom", methods=["DELETE"])
@login_required
def api_delete_custom_option():
    body = request.get_json(force=True)
    category = body.get("category")
    item_id = body.get("id") or ""
    if category not in CUSTOM_OPTION_CATEGORIES:
        return jsonify({"error": f"category must be one of {sorted(CUSTOM_OPTION_CATEGORIES)}."}), 400
    if not item_id.startswith("custom_"):
        return jsonify({"error": "Only custom-added options can be deleted."}), 400

    options = json.loads(current_user.options_json)
    items = options.get(category, [])
    remaining = [i for i in items if i["id"] != item_id]
    if len(remaining) == len(items):
        return jsonify({"error": "Option not found."}), 404

    options[category] = remaining
    current_user.options_json = json.dumps(options)
    db.session.commit()

    return jsonify({"ok": True})


@app.route("/api/clients", methods=["GET"])
@login_required
def api_get_clients():
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.created_at).all()
    return jsonify([c.to_dict() for c in clients])


@app.route("/api/clients", methods=["POST"])
@login_required
def api_create_client():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Client name is required."}), 400

    client = Client(
        user_id=current_user.id,
        name=name,
        dob=body.get("dob", "").strip(),
        diagnosis=body.get("diagnosis", "").strip(),
        guardian_name=body.get("guardian_name", "").strip(),
        guardian_relationship=body.get("guardian_relationship", "").strip(),
        rbt_name=body.get("rbt_name", "").strip(),
        replacement_programs=body.get("replacement_programs") or [],
        maladaptive_behaviors=body.get("maladaptive_behaviors") or [],
        antecedents=body.get("antecedents") or [],
        intervention_strategies=body.get("intervention_strategies") or [],
        training_topics=body.get("training_topics") or [],
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


def _get_client_or_404(client_id):
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first()
    if not client:
        abort(404, description="Client not found.")
    return client


@app.route("/api/clients/<client_id>", methods=["PATCH"])
@login_required
def api_update_client(client_id):
    client = _get_client_or_404(client_id)
    body = request.get_json(force=True)

    editable_fields = [
        "name", "dob", "diagnosis", "guardian_name", "guardian_relationship", "rbt_name",
        "replacement_programs", "maladaptive_behaviors", "antecedents", "intervention_strategies", "training_topics",
    ]
    for field in editable_fields:
        if field in body:
            setattr(client, field, body[field])

    db.session.commit()
    return jsonify(client.to_dict())


@app.route("/api/clients/<client_id>", methods=["DELETE"])
@login_required
def api_delete_client(client_id):
    client = _get_client_or_404(client_id)
    # SavedNote.client_id has no ON DELETE CASCADE at the database level, so
    # deleting a client with saved notes would otherwise fail with a foreign
    # key violation on Postgres.
    SavedNote.query.filter_by(client_id=client.id, user_id=current_user.id).delete()
    db.session.delete(client)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    body = request.get_json(force=True)
    note_type = body.get("note_type")
    client_id = body.get("client_id")
    client_name = (body.get("client_name") or "").strip()
    valid_types = ("session", "bcaba_session", "rbt_session", "caregiver", "initial_assessment", "reassessment")
    if note_type not in valid_types:
        return jsonify({"error": f"note_type must be one of {valid_types}."}), 400
    if not client_id and not client_name:
        return jsonify({"error": "client_id or client_name is required."}), 400

    if client_id:
        client_dict = _get_client_or_404(client_id).to_dict()
    else:
        client_dict = {"name": client_name, "dob": "", "diagnosis": ""}

    options = json.loads(current_user.options_json)

    data = dict(body)
    data["client"] = client_dict

    generators = {
        "session": ng.generate_session_note,
        "bcaba_session": ng.generate_bcaba_session_note,
        "rbt_session": ng.generate_rbt_session_note,
        "caregiver": ng.generate_caregiver_note,
        "initial_assessment": ng.generate_initial_assessment,
        "reassessment": ng.generate_reassessment,
    }
    generate_fn = generators[note_type]

    corpus_texts = [
        row.note_text
        for row in GeneratedNote.query.filter_by(user_id=current_user.id, note_type=note_type)
        .order_by(GeneratedNote.created_at.desc())
        .limit(SIMILARITY_CORPUS_LIMIT)
        .all()
    ]

    best_text, best_count, best_similarity = None, None, 1.0
    for _ in range(MAX_GENERATION_ATTEMPTS):
        text, count = generate_fn(data, options)
        similarity = _max_similarity(text, corpus_texts)
        if best_text is None or similarity < best_similarity:
            best_text, best_count, best_similarity = text, count, similarity
        if similarity <= MAX_NOTE_SIMILARITY:
            break

    db.session.add(GeneratedNote(user_id=current_user.id, note_type=note_type, note_text=best_text))
    db.session.commit()

    return jsonify({
        "note_text": best_text,
        "word_count": best_count,
        "max_similarity": round(best_similarity * 100, 1),
    })


def _sentence_set(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return {s.strip() for s in sentences if len(s.strip()) > 12}


def _sentence_overlap(candidate, other):
    """Order-insensitive companion to the character-sequence ratio below. Two notes
    that reuse many of the same filler/template sentences in a different order read
    as very dissimilar to SequenceMatcher (which scores contiguous matching runs in
    position order), but share substantial real content - exactly what an external
    plagiarism/audit tool flags, since those compare sentence content regardless of
    where it falls in the text. Confirmed via testing: two generated caregiver notes
    with different random seeds shared 19 of 40 sentences verbatim (47.5% overlap)
    while SequenceMatcher reported only 24.5% similarity for the same pair."""
    a, b = _sentence_set(candidate), _sentence_set(other)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _max_similarity(candidate, corpus_texts):
    best = 0.0
    for other in corpus_texts:
        ratio = max(
            difflib.SequenceMatcher(None, candidate, other).ratio(),
            _sentence_overlap(candidate, other),
        )
        if ratio > best:
            best = ratio
    return best


@app.route("/api/save", methods=["POST"])
@login_required
def api_save():
    body = request.get_json(force=True)
    client_id = body.get("client_id")
    note_type = body.get("note_type")
    note_text = body.get("note_text", "")
    session_date = body.get("session_date") or datetime.now().strftime("%Y-%m-%d")

    if not client_id or not note_type or not note_text.strip():
        return jsonify({"error": "client_id, note_type, and note_text are required."}), 400

    client = _get_client_or_404(client_id)
    safe_name = "".join(c if c.isalnum() else "_" for c in client.name)
    filename = f"{safe_name}_{note_type}_{session_date}.txt"

    note = SavedNote(
        user_id=current_user.id,
        client_id=client.id,
        client_name=client.name,
        filename=filename,
        note_type=note_type,
        session_date=session_date,
        note_text=note_text,
        word_count=ng.word_count(note_text),
    )
    db.session.add(note)
    db.session.commit()

    return jsonify({"ok": True, "filename": filename, "note_id": note.id})


@app.route("/api/notes", methods=["GET"])
@login_required
def api_notes():
    client_id = request.args.get("client_id")
    query = SavedNote.query.filter_by(user_id=current_user.id)
    if client_id:
        query = query.filter_by(client_id=client_id)
    notes = query.order_by(SavedNote.saved_at.desc()).all()
    result = []
    for n in notes:
        d = n.to_dict()
        d["id"] = n.id
        result.append(d)
    return jsonify(result)


@app.route("/api/notes/download/<int:note_id>")
@login_required
def api_download_note(note_id):
    note = SavedNote.query.filter_by(id=note_id, user_id=current_user.id).first()
    if not note:
        return jsonify({"error": "Note not found."}), 404
    return Response(
        note.note_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={note.filename}"},
    )


if __name__ == "__main__":
    # Debug mode exposes an interactive in-browser debugger with arbitrary code
    # execution on unhandled exceptions; it must be explicitly opted into, never
    # on by default, in case this is ever run against a real database locally.
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5057)

from flask import Blueprint, render_template, request, redirect, session
from datetime import datetime
from database.db import get_db_connection
from database.sql_helpers import db_placeholder
from routes.auth_helpers import login_required

knowledge_bp = Blueprint("knowledge", __name__)


knowledge_articles = {
    "password-reset": {
        "title": "Password Reset Help",
        "category": "Account Access",
        "estimated_time": "5–10 minutes",
        "difficulty": "Easy",
        "last_updated": "06/29/2026",
        "steps": [
            "Go to the company password reset portal.",
            "Enter your username or employee ID.",
            "Verify your identity using email or phone verification.",
            "Create a new password using company password rules.",
            "Try logging in again after 2–3 minutes."
        ],
        "tips": [
            "Check Caps Lock before trying again.",
            "Do not reuse old passwords.",
            "If your account is locked, contact IT support."
        ]
    },
    "wifi-network": {
        "title": "Wi-Fi / Network Issues",
        "category": "Network",
        "estimated_time": "5–15 minutes",
        "difficulty": "Easy",
        "last_updated": "06/29/2026",
        "steps": [
            "Confirm Wi-Fi is turned on.",
            "Disconnect and reconnect to the company network.",
            "Restart your computer.",
            "Try opening another website or app.",
            "Submit a ticket if the issue continues."
        ],
        "tips": [
            "Check whether other employees are having the same issue.",
            "Move closer to the access point if using Wi-Fi.",
            "Use ethernet if available."
        ]
    },
    "slow-computer": {
        "title": "Computer Running Slow",
        "category": "Hardware",
        "estimated_time": "10–20 minutes",
        "difficulty": "Medium",
        "last_updated": "06/29/2026",
        "steps": [
            "Restart your computer.",
            "Close unused browser tabs and apps.",
            "Check for pending updates.",
            "Make sure storage is not almost full.",
            "Submit a ticket if performance does not improve."
        ],
        "tips": [
            "Do not install unauthorized cleanup tools.",
            "Report loud fan noise or overheating.",
            "Mention when the issue started in your ticket."
        ]
    },
    "software-not-opening": {
        "title": "Software Not Opening",
        "category": "Software",
        "estimated_time": "5–15 minutes",
        "difficulty": "Easy",
        "last_updated": "06/29/2026",
        "steps": [
            "Close the program completely.",
            "Restart your computer.",
            "Check if other programs are opening normally.",
            "Confirm you have access to the software.",
            "Submit a ticket if the software still will not open."
        ],
        "tips": [
            "Take a screenshot of any error message.",
            "Include the software name in your ticket.",
            "Mention whether the issue affects other coworkers."
        ]
    }
}


def get_article_summary(slug, article):
    summaries = {
        "password-reset": "Reset your password or recover account access.",
        "wifi-network": "Troubleshoot connection and network problems.",
        "slow-computer": "Fix slow performance, freezing, or lag.",
        "software-not-opening": "Try simple fixes before submitting a software ticket."
    }

    return {
        "slug": slug,
        "title": article["title"],
        "category": article["category"],
        "summary": summaries.get(slug, "View guided troubleshooting steps."),
        "estimated_time": article["estimated_time"],
        "difficulty": article["difficulty"]
    }


def get_related_articles(current_slug):
    current_article = knowledge_articles.get(current_slug)

    if not current_article:
        return []

    related = []

    for slug, article in knowledge_articles.items():
        if slug != current_slug:
            related.append(get_article_summary(slug, article))

    return related[:3]


def track_article_view(slug):
    placeholder = db_placeholder()
    username = session.get("username", "anonymous")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"""
            INSERT INTO article_views (
                article_slug,
                username,
                viewed_at
            )
            VALUES ({placeholder}, {placeholder}, {placeholder})
        """, (
            slug,
            username,
            datetime.now().strftime("%m/%d/%Y %I:%M %p")
        ))

        connection.commit()
    except Exception:
        connection.rollback()

    connection.close()


def get_article_stats(slug):
    placeholder = db_placeholder()

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(f"""
            SELECT COUNT(*) AS count
            FROM article_views
            WHERE article_slug = {placeholder}
        """, (slug,))
        views = cursor.fetchone()["count"]

        cursor.execute(f"""
            SELECT COUNT(*) AS count
            FROM article_feedback
            WHERE article_slug = {placeholder}
        """, (slug,))
        total_feedback = cursor.fetchone()["count"]

        cursor.execute(f"""
            SELECT COUNT(*) AS count
            FROM article_feedback
            WHERE article_slug = {placeholder}
            AND was_helpful = 'yes'
        """, (slug,))
        helpful_count = cursor.fetchone()["count"]

    except Exception:
        views = 0
        total_feedback = 0
        helpful_count = 0

    connection.close()

    helpful_percent = round((helpful_count / total_feedback) * 100) if total_feedback else 100

    return {
        "views": views,
        "helpful_percent": helpful_percent,
        "feedback_count": total_feedback
    }


@knowledge_bp.route("/knowledge_base")
@login_required
def knowledge_base():
    articles = [
        get_article_summary(slug, article)
        for slug, article in knowledge_articles.items()
    ]

    return render_template("knowledge_base.html", articles=articles)


@knowledge_bp.route("/knowledge_base/<slug>")
@login_required
def knowledge_article(slug):
    article = knowledge_articles.get(slug)

    if not article:
        return redirect("/knowledge_base")

    article["slug"] = slug

    track_article_view(slug)

    return render_template(
        "knowledge_article.html",
        article=article,
        related_articles=get_related_articles(slug),
        article_stats=get_article_stats(slug)
    )


@knowledge_bp.route("/contact_it")
@login_required
def contact_it():
    return render_template("contact_it.html")


@knowledge_bp.route("/knowledge_base/<slug>/feedback", methods=["POST"])
@login_required
def submit_article_feedback(slug):
    if slug not in knowledge_articles:
        return redirect("/knowledge_base")

    was_helpful = request.form.get("was_helpful", "").strip().lower()
    if was_helpful not in {"yes", "no"}:
        return redirect(f"/knowledge_base/{slug}")

    feedback = request.form.get("feedback", "").strip()[:2000]
    feedback_reason = request.form.get("feedback_reason", "").strip()[:120]
    username = session.get("username", "anonymous")
    placeholder = db_placeholder()

    feedback_message = f"Reason: {feedback_reason} | Details: {feedback}"

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(f"""
        INSERT INTO article_feedback (
            article_slug,
            username,
            was_helpful,
            feedback,
            created_at
        )
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        slug,
        username,
        was_helpful,
        feedback_message,
        datetime.now().strftime("%m/%d/%Y %I:%M %p")
    ))

    connection.commit()
    connection.close()

    return redirect(f"/knowledge_base/{slug}?feedback=submitted")
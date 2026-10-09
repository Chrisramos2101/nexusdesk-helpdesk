import html
import os

from services.email_service import send_email


# =========================================================
# NEXUSDESK EMAIL HELPERS
# =========================================================


def get_priority_response_time(priority):
    """
    Return the final NexusDesk SLA target associated
    with a ticket priority.
    """

    if priority == "High":
        return "4 business hours"

    if priority == "Medium":
        return "1 business day"

    return "3 business days"


def _ticket_reference(ticket_id):
    """
    Return the same professional ticket identifier
    displayed throughout the NexusDesk interface.
    """

    try:
        return f"NEX-2026-{int(ticket_id):06d}"

    except (TypeError, ValueError):
        return f"NEX-2026-{ticket_id}"


def _app_url(path=""):
    """
    Build an application URL when APP_BASE_URL is configured.

    An empty value is returned when no application base URL
    is available so emails do not contain broken links.
    """

    base_url = os.getenv(
        "APP_BASE_URL",
        ""
    ).strip().rstrip("/")

    if not base_url:
        return ""

    if path and not path.startswith("/"):
        path = f"/{path}"

    return f"{base_url}{path}"


def _safe(value):
    """
    Escape dynamic values before inserting them
    into an HTML email.
    """

    if value is None:
        return ""

    return html.escape(
        str(value)
    )


def _format_note_for_html(note):
    """
    Safely preserve line breaks in ticket comments.
    """

    escaped_note = _safe(
        note
    )

    return escaped_note.replace(
        "\n",
        "<br>"
    )


def _email_button(label, url):
    """
    Return a reusable NexusDesk email action button.

    If no application URL is configured, no button is
    rendered rather than exposing an invalid link.
    """

    if not url:
        return ""

    safe_label = _safe(
        label
    )

    safe_url = _safe(
        url
    )

    return f"""
        <table
            role="presentation"
            width="100%"
            cellspacing="0"
            cellpadding="0"
            border="0"
            style="margin-top: 24px;"
        >
            <tr>
                <td align="center">
                    <a
                        href="{safe_url}"
                        style="
                            display: inline-block;
                            background: #2563eb;
                            color: #ffffff;
                            text-decoration: none;
                            font-family: Arial, Helvetica, sans-serif;
                            font-size: 15px;
                            font-weight: 700;
                            padding: 13px 22px;
                            border-radius: 8px;
                        "
                    >
                        {safe_label}
                    </a>
                </td>
            </tr>
        </table>
    """


def _email_shell(
    title,
    eyebrow,
    greeting,
    intro,
    content_html,
    action_label="",
    action_url="",
    footer_note=""
):
    """
    Build the shared NexusDesk transactional email layout.

    All notification emails use this same structure so
    MFA, password recovery, and ticket notifications feel
    like one consistent product.
    """

    safe_title = _safe(
        title
    )

    safe_eyebrow = _safe(
        eyebrow
    )

    safe_greeting = _safe(
        greeting
    )

    safe_intro = _safe(
        intro
    )

    safe_footer_note = _safe(
        footer_note
    )

    button_html = _email_button(
        action_label,
        action_url
    )

    footer_note_html = ""

    if safe_footer_note:
        footer_note_html = f"""
            <p
                style="
                    margin: 22px 0 0;
                    color: #64748b;
                    font-size: 13px;
                    line-height: 1.6;
                "
            >
                {safe_footer_note}
            </p>
        """

    return f"""
<!DOCTYPE html>

<html lang="en">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        {safe_title}
    </title>
</head>


<body
    style="
        margin: 0;
        padding: 0;
        background: #0f172a;
        font-family: Arial, Helvetica, sans-serif;
    "
>

<table
    role="presentation"
    width="100%"
    cellspacing="0"
    cellpadding="0"
    border="0"
    style="
        width: 100%;
        background: #0f172a;
        padding: 32px 12px;
    "
>

    <tr>

        <td align="center">


            <table
                role="presentation"
                width="100%"
                cellspacing="0"
                cellpadding="0"
                border="0"
                style="
                    width: 100%;
                    max-width: 620px;
                "
            >


                <!-- Brand -->

                <tr>

                    <td
                        style="
                            padding: 0 0 18px;
                            text-align: center;
                        "
                    >

                        <div
                            style="
                                color: #ffffff;
                                font-size: 24px;
                                font-weight: 800;
                                letter-spacing: -0.4px;
                            "
                        >
                            🎧 NexusDesk
                        </div>

                        <div
                            style="
                                margin-top: 6px;
                                color: #94a3b8;
                                font-size: 13px;
                            "
                        >
                            IT Support &amp; Ticket Management
                        </div>

                    </td>

                </tr>



                <!-- Main Card -->

                <tr>

                    <td
                        style="
                            background: #ffffff;
                            border-radius: 16px;
                            overflow: hidden;
                            box-shadow:
                                0 18px 45px
                                rgba(0, 0, 0, 0.22);
                        "
                    >


                        <!-- Blue Header -->

                        <div
                            style="
                                background:
                                    linear-gradient(
                                        135deg,
                                        #1d4ed8,
                                        #2563eb
                                    );
                                padding: 28px 32px;
                            "
                        >

                            <div
                                style="
                                    color: #bfdbfe;
                                    font-size: 12px;
                                    font-weight: 800;
                                    letter-spacing: 1.4px;
                                    text-transform: uppercase;
                                "
                            >
                                {safe_eyebrow}
                            </div>


                            <h1
                                style="
                                    margin: 8px 0 0;
                                    color: #ffffff;
                                    font-size: 25px;
                                    line-height: 1.25;
                                "
                            >
                                {safe_title}
                            </h1>

                        </div>



                        <!-- Email Content -->

                        <div
                            style="
                                padding: 32px;
                                color: #334155;
                            "
                        >

                            <p
                                style="
                                    margin: 0 0 16px;
                                    color: #0f172a;
                                    font-size: 16px;
                                    font-weight: 700;
                                "
                            >
                                Hello {safe_greeting},
                            </p>


                            <p
                                style="
                                    margin: 0 0 24px;
                                    color: #475569;
                                    font-size: 15px;
                                    line-height: 1.7;
                                "
                            >
                                {safe_intro}
                            </p>


                            {content_html}


                            {button_html}


                            {footer_note_html}


                            <div
                                style="
                                    margin-top: 28px;
                                    padding-top: 22px;
                                    border-top: 1px solid #e2e8f0;
                                "
                            >

                                <p
                                    style="
                                        margin: 0;
                                        color: #475569;
                                        font-size: 14px;
                                        line-height: 1.6;
                                    "
                                >
                                    Thank you,<br>

                                    <strong
                                        style="
                                            color: #0f172a;
                                        "
                                    >
                                        NexusDesk IT Services
                                    </strong>
                                </p>

                            </div>

                        </div>

                    </td>

                </tr>



                <!-- Footer -->

                <tr>

                    <td
                        style="
                            padding: 18px 12px 0;
                            text-align: center;
                            color: #64748b;
                            font-size: 12px;
                            line-height: 1.5;
                        "
                    >
                        Secure internal support notification from NexusDesk.
                    </td>

                </tr>


            </table>

        </td>

    </tr>

</table>

</body>

</html>
"""


def _detail_row(label, value):
    """
    Create one reusable email detail row.
    """

    return f"""
        <tr>
            <td
                style="
                    padding: 10px 14px;
                    color: #64748b;
                    font-size: 13px;
                    width: 42%;
                    border-bottom: 1px solid #e2e8f0;
                "
            >
                {_safe(label)}
            </td>

            <td
                style="
                    padding: 10px 14px;
                    color: #0f172a;
                    font-size: 14px;
                    font-weight: 700;
                    border-bottom: 1px solid #e2e8f0;
                "
            >
                {_safe(value)}
            </td>
        </tr>
    """


def _details_table(rows):
    """
    Build the reusable ticket-information table.
    """

    rows_html = "".join(
        _detail_row(
            label,
            value
        )
        for label, value in rows
    )

    return f"""
        <table
            role="presentation"
            width="100%"
            cellspacing="0"
            cellpadding="0"
            border="0"
            style="
                width: 100%;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                border-collapse: separate;
                border-spacing: 0;
                overflow: hidden;
                background: #f8fafc;
            "
        >
            {rows_html}
        </table>
    """


# =========================================================
# TICKET SUBMITTED
# =========================================================


def send_ticket_created_email(
    recipient_email,
    username,
    ticket_id,
    priority,
    category
):
    ticket_reference = _ticket_reference(
        ticket_id
    )

    sla_target = get_priority_response_time(
        priority
    )

    subject = (
        "NexusDesk | Ticket Submitted | "
        f"{ticket_reference}"
    )

    body = f"""
Hello {username},

Your NexusDesk support request has been received successfully.

TICKET DETAILS
--------------------------------
Ticket ID: {ticket_reference}
Category: {category}
Priority: {priority}
Status: Open
SLA Target: {sla_target}

WHAT HAPPENS NEXT
--------------------------------
• Your request is now in the IT support queue.
• An administrator or technician will review the ticket.
• You may receive additional notifications when work begins or the issue is resolved.

You can also track the ticket from My Tickets in NexusDesk.

Thank you,
NexusDesk IT Services
"""

    details_html = _details_table([
        (
            "Ticket ID",
            ticket_reference
        ),
        (
            "Category",
            category
        ),
        (
            "Priority",
            priority
        ),
        (
            "Status",
            "Open"
        ),
        (
            "SLA Target",
            sla_target
        ),
    ])

    next_steps_html = f"""
        {details_html}

        <div
            style="
                margin-top: 24px;
                padding: 18px;
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 10px;
            "
        >
            <div
                style="
                    color: #1e40af;
                    font-size: 13px;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                    margin-bottom: 8px;
                "
            >
                What happens next
            </div>

            <div
                style="
                    color: #334155;
                    font-size: 14px;
                    line-height: 1.7;
                "
            >
                Your request is now in the IT support queue.
                A technician will review it according to its
                priority and SLA target.
            </div>
        </div>
    """

    html_body = _email_shell(
        title="Support Request Received",
        eyebrow="Ticket Confirmation",
        greeting=username,
        intro=(
            "Your NexusDesk support request has been "
            "received successfully and is now available "
            "for IT review."
        ),
        content_html=next_steps_html,
        action_label="View My Tickets",
        action_url=_app_url(
            f"/my_tickets/{ticket_id}"
        ),
        footer_note=(
            "You do not need to reply to this email. "
            "Track updates directly in NexusDesk."
        )
    )

    return send_email(
        subject,
        recipient_email,
        body,
        html_body
    )


# =========================================================
# TICKET ASSIGNED
# =========================================================


def send_ticket_assigned_email(
    recipient_email,
    username,
    ticket_id
):
    ticket_reference = _ticket_reference(
        ticket_id
    )

    subject = (
        "NexusDesk | Ticket Assigned | "
        f"{ticket_reference}"
    )

    body = f"""
Hello {username},

A NexusDesk support ticket has been assigned to you.

TICKET INFORMATION
--------------------------------
Ticket ID: {ticket_reference}
Assignment: Assigned to you

ACTION REQUIRED
--------------------------------
• Review the ticket details in the Admin Portal.
• Update the ticket status when work begins.
• Add notes to document troubleshooting and progress.
• Close the ticket after the issue has been resolved.

Thank you,
NexusDesk IT Services
"""

    details_html = _details_table([
        (
            "Ticket ID",
            ticket_reference
        ),
        (
            "Assignment",
            "Assigned to you"
        ),
        (
            "Next Step",
            "Review ticket"
        ),
    ])

    action_html = f"""
        {details_html}

        <div
            style="
                margin-top: 24px;
                padding: 18px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            "
        >
            <div
                style="
                    color: #0f172a;
                    font-size: 14px;
                    font-weight: 800;
                    margin-bottom: 8px;
                "
            >
                Technician checklist
            </div>

            <div
                style="
                    color: #475569;
                    font-size: 14px;
                    line-height: 1.8;
                "
            >
                Review the request, begin troubleshooting,
                document meaningful progress, and close the
                ticket once the issue has been resolved.
            </div>
        </div>
    """

    html_body = _email_shell(
        title="Ticket Assigned to You",
        eyebrow="Technician Assignment",
        greeting=username,
        intro=(
            "A NexusDesk support ticket has been assigned "
            "to your workload and is ready for review."
        ),
        content_html=action_html,
        action_label="Open Admin Portal",
        action_url=_app_url(
            "/dashboard"
        ),
        footer_note=(
            "Keep ticket notes current so the support "
            "history accurately reflects troubleshooting "
            "and resolution activity."
        )
    )

    return send_email(
        subject,
        recipient_email,
        body,
        html_body
    )


# =========================================================
# TICKET RESOLVED
# =========================================================


def send_ticket_closed_email(
    recipient_email,
    username,
    ticket_id,
    resolution_time,
    sla_met
):
    ticket_reference = _ticket_reference(
        ticket_id
    )

    normalized_sla = (
        str(sla_met).strip().lower()
        if sla_met is not None
        else ""
    )

    if normalized_sla in {
        "yes",
        "true",
        "met"
    }:
        sla_display = "Met"

    elif normalized_sla in {
        "no",
        "false",
        "missed"
    }:
        sla_display = "Missed"

    else:
        sla_display = (
            str(sla_met)
            if sla_met
            else "Not Available"
        )

    resolution_display = (
        resolution_time
        if resolution_time
        else "Not Available"
    )

    subject = (
        "NexusDesk | Ticket Resolved | "
        f"{ticket_reference}"
    )

    body = f"""
Hello {username},

Your NexusDesk support request has been resolved.

RESOLUTION SUMMARY
--------------------------------
Ticket ID: {ticket_reference}
Status: Closed
Resolution Time: {resolution_display}
SLA: {sla_display}

Your ticket has been marked as completed by IT.

If the issue continues or returns, please submit a new support request and reference {ticket_reference}.

Thank you,
NexusDesk IT Services
"""

    details_html = _details_table([
        (
            "Ticket ID",
            ticket_reference
        ),
        (
            "Status",
            "Closed"
        ),
        (
            "Resolution Time",
            resolution_display
        ),
        (
            "SLA",
            sla_display
        ),
    ])

    resolved_html = f"""
        {details_html}

        <div
            style="
                margin-top: 24px;
                padding: 18px;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 10px;
            "
        >
            <div
                style="
                    color: #166534;
                    font-size: 14px;
                    font-weight: 800;
                    margin-bottom: 7px;
                "
            >
                ✓ Ticket completed
            </div>

            <div
                style="
                    color: #334155;
                    font-size: 14px;
                    line-height: 1.7;
                "
            >
                IT has marked this support request as resolved.
                The resolution has been recorded in NexusDesk.
            </div>
        </div>
    """

    html_body = _email_shell(
        title="Your Ticket Has Been Resolved",
        eyebrow="Resolution Notification",
        greeting=username,
        intro=(
            "Your IT support request has been completed "
            "and the resolution has been recorded."
        ),
        content_html=resolved_html,
        action_label="View Ticket",
        action_url=_app_url(
            f"/my_tickets/{ticket_id}"
        ),
        footer_note=(
            f"If the problem continues, submit a new ticket "
            f"and reference {ticket_reference}."
        )
    )

    return send_email(
        subject,
        recipient_email,
        body,
        html_body
    )


# =========================================================
# USER MENTION
# =========================================================


def send_mention_email(
    recipient_email,
    mentioned_username,
    ticket_id,
    note
):
    ticket_reference = _ticket_reference(
        ticket_id
    )

    subject = (
        "NexusDesk | You Were Mentioned | "
        f"{ticket_reference}"
    )

    body = f"""
Hello {mentioned_username},

You were mentioned in a NexusDesk ticket.

TICKET
--------------------------------
Ticket ID: {ticket_reference}

COMMENT
--------------------------------
{note}

Please review the ticket in NexusDesk for additional context.

Thank you,
NexusDesk IT Services
"""

    formatted_note = _format_note_for_html(
        note
    )

    mention_html = f"""
        {_details_table([
            (
                "Ticket ID",
                ticket_reference
            ),
            (
                "Notification",
                "You were mentioned"
            ),
        ])}

        <div
            style="
                margin-top: 24px;
                padding: 18px;
                background: #f8fafc;
                border-left: 4px solid #2563eb;
                border-radius: 8px;
            "
        >
            <div
                style="
                    color: #64748b;
                    font-size: 12px;
                    font-weight: 800;
                    letter-spacing: 0.8px;
                    text-transform: uppercase;
                    margin-bottom: 10px;
                "
            >
                Comment
            </div>

            <div
                style="
                    color: #0f172a;
                    font-size: 14px;
                    line-height: 1.7;
                    overflow-wrap: anywhere;
                "
            >
                {formatted_note}
            </div>
        </div>
    """

    html_body = _email_shell(
        title="You Were Mentioned in a Ticket",
        eyebrow="Ticket Notification",
        greeting=mentioned_username,
        intro=(
            "You were mentioned in a NexusDesk ticket "
            "comment and may need to review the conversation."
        ),
        content_html=mention_html,
        action_label="Open Admin Portal",
        action_url=_app_url(
            "/dashboard"
        ),
        footer_note=(
            "Review the ticket in NexusDesk for the complete "
            "request history and current status."
        )
    )

    return send_email(
        subject,
        recipient_email,
        body,
        html_body
    )
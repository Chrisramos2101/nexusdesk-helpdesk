from services.email_service import send_email


def get_priority_response_time(priority):
    if priority == "High":
        return "Within 1 hour"
    if priority == "Medium":
        return "Within 8 hours"
    return "Within 24 hours"


def send_ticket_created_email(recipient_email, username, ticket_id, priority, category):
    subject = f"NexusDesk | Ticket Submitted Successfully (#{ticket_id})"

    response_time = get_priority_response_time(priority)

    body = f"""
Hello {username},

Your IT support request has been received and assigned Ticket #{ticket_id}.

REQUEST DETAILS
--------------------------------
Ticket ID: #{ticket_id}
Category: {category}
Priority: {priority}
Status: Open
Expected Response: {response_time}

WHAT HAPPENS NEXT
--------------------------------
• An IT technician will review your request.
• You will receive an update when your ticket is assigned.
• Additional notifications may be sent if the status changes or your ticket is resolved.

NEED ADDITIONAL HELP?
--------------------------------
If this issue becomes urgent, contact your IT Service Desk or submit a new high-priority ticket.

Thank you,
NexusDesk IT Services
"""

    send_email(subject, recipient_email, body)


def send_ticket_assigned_email(recipient_email, username, ticket_id):
    subject = f"NexusDesk | Ticket Assigned (#{ticket_id})"

    body = f"""
Hello {username},

A NexusDesk support ticket has been assigned to you.

TICKET INFORMATION
--------------------------------
Ticket ID: #{ticket_id}
Current Status: Assigned to Technician

ACTION REQUIRED
--------------------------------
• Review the ticket details in the IT dashboard.
• Update the ticket status once work begins.
• Add notes to document troubleshooting steps or resolution progress.
• Close the ticket once the issue has been resolved.

Thank you,
NexusDesk IT Operations
"""

    send_email(subject, recipient_email, body)


def send_ticket_closed_email(recipient_email, username, ticket_id, resolution_time, sla_met):
    subject = f"NexusDesk | Ticket Resolved (#{ticket_id})"

    body = f"""
Hello {username},

Your IT support request has been completed.

RESOLUTION SUMMARY
--------------------------------
Ticket ID: #{ticket_id}
Status: Closed
Resolution Time: {resolution_time}
SLA Met: {sla_met}

WHAT THIS MEANS
--------------------------------
• Your ticket has been marked as resolved by IT.
• The resolution time has been recorded for support performance tracking.
• SLA performance has been logged for reporting and service quality review.

IF THE ISSUE IS NOT RESOLVED
--------------------------------
If the problem continues, please submit a new ticket and reference Ticket #{ticket_id} in your request.

Thank you for using NexusDesk.

NexusDesk IT Services
"""

    send_email(subject, recipient_email, body)


def send_mention_email(recipient_email, mentioned_username, ticket_id, note):
    subject = f"NexusDesk | You Were Mentioned (Ticket #{ticket_id})"

    body = f"""
Hello {mentioned_username},

You were mentioned in a NexusDesk ticket.

Ticket ID: #{ticket_id}

COMMENT
--------------------------------
{note}

Please review the ticket for additional details.

Thank you,
NexusDesk IT Services
"""

    send_email(subject, recipient_email, body)
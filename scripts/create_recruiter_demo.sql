BEGIN;

DO $$
BEGIN
    IF current_database() <> 'nexusdesk_recruiter_demo' THEN
        RAISE EXCEPTION 'Wrong database';
    END IF;

    IF (SELECT COUNT(*) FROM users) <> 0
       OR (SELECT COUNT(*) FROM tickets) <> 0
       OR (SELECT COUNT(*) FROM ticket_notes) <> 0 THEN
        RAISE EXCEPTION 'Demo database is not empty';
    END IF;
END $$;

-- All passwords are intentionally unusable until
-- read-only recruiter authentication is implemented.
INSERT INTO users
(username, password_hash, role, full_name, department, email)
VALUES
('Demo_Admin', '!', 'admin', 'Demo Administrator', 'IT', 'demo-admin@example.com'),
('Demo_Employee', '!', 'employee', 'Demo Employee', 'Operations', 'demo-employee@example.com');

INSERT INTO users
(username, password_hash, role, full_name, department, email)
SELECT
    'demo_staff_' || lpad(n::text, 2, '0'),
    '!',
    CASE WHEN n <= 3 THEN 'admin' ELSE 'employee' END,
    'Fictional Staff ' || lpad(n::text, 2, '0'),
    (ARRAY['Finance','HR','Management','Operations','Sales'])[((n-1)%5)+1],
    'demo-staff-' || lpad(n::text, 2, '0') || '@example.com'
FROM generate_series(1,12) AS n;

WITH generated AS (
    SELECT
        n,
        CASE
            WHEN n <= 52 THEN 'Closed'
            WHEN n <= 68 THEN 'In Progress'
            ELSE 'Open'
        END AS ticket_status,
        CASE
            WHEN n <= 12 THEN 'High'
            WHEN n <= 48 THEN 'Medium'
            ELSE 'Low'
        END AS ticket_priority,
        CASE
            WHEN n <= 20 THEN 'Hardware'
            WHEN n <= 38 THEN 'Account Access'
            WHEN n <= 55 THEN 'Software'
            WHEN n <= 69 THEN 'Network'
            WHEN n <= 75 THEN 'Security'
            ELSE 'Other'
        END AS ticket_category,
        (ARRAY['Finance','HR','Management','Operations','Sales'])[((n-1)%5)+1] AS dept,
        timestamp '2026-08-01 09:00'
            + (n * interval '1 day') AS opened
    FROM generate_series(1,80) AS n
)
INSERT INTO tickets
(
    name, department, issue, priority, status,
    submitted_at, closed_at, assigned_to,
    completed_by, notes, category,
    sla_due_at, submitted_by, resolution_time, sla_met
)
SELECT
    CASE WHEN n%5=0 THEN 'Demo Employee'
         ELSE 'Fictional Staff ' ||
              lpad((((n-1)%12)+1)::text,2,'0')
    END,
    dept,
    CASE ticket_category
        WHEN 'Hardware' THEN 'Workstation hardware requires troubleshooting'
        WHEN 'Account Access' THEN 'Employee account access requires assistance'
        WHEN 'Software' THEN 'Business application is not functioning as expected'
        WHEN 'Network' THEN 'Office network connectivity requires investigation'
        WHEN 'Security' THEN 'Security-related support request requires review'
        ELSE 'General IT support assistance requested'
    END || ' - Sample ' || n,
    ticket_priority,
    ticket_status,
    to_char(opened,'MM/DD/YYYY HH12:MI AM'),
    CASE WHEN ticket_status='Closed'
         THEN to_char(opened + interval '2 days','MM/DD/YYYY HH12:MI AM')
         ELSE '' END,
    CASE WHEN n%4=0 THEN 'Demo_Admin'
         ELSE 'demo_staff_' || lpad((((n-1)%3)+1)::text,2,'0')
    END,
    CASE WHEN ticket_status='Closed' THEN 'Demo_Admin' ELSE '' END,
    'Synthetic portfolio demonstration record.',
    ticket_category,
    '',
    CASE WHEN n%5=0 THEN 'Demo_Employee'
         ELSE 'demo_staff_' || lpad((((n-1)%12)+1)::text,2,'0')
    END,
    '',
    ''
FROM generated
ORDER BY n;

INSERT INTO ticket_notes
(ticket_id,note,created_by,created_at)
SELECT
    ((n-1)%80)+1,
    'Synthetic troubleshooting note ' || n ||
    ': investigation and support activity documented.',
    'Demo_Admin',
    to_char(
        timestamp '2026-09-01 10:00'
        + (n * interval '3 hours'),
        'MM/DD/YYYY HH12:MI AM'
    )
FROM generate_series(1,156) AS n;

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM users) <> 14
       OR (SELECT COUNT(*) FROM tickets) <> 80
       OR (SELECT COUNT(*) FROM ticket_notes) <> 156
       OR EXISTS (
           SELECT 1 FROM users
           WHERE username ILIKE '%Cristian%'
       )
    THEN
        RAISE EXCEPTION 'Recruiter dataset validation failed';
    END IF;
END $$;

COMMIT;

SELECT current_database() AS database,
       (SELECT COUNT(*) FROM users) AS users,
       (SELECT COUNT(*) FROM tickets) AS tickets,
       (SELECT COUNT(*) FROM ticket_notes) AS ticket_notes;

# Globex Corporation — IT Service Desk Standard Operating Procedures

**Document ID:** IT-SOP-2024-003
**Effective Date:** January 15, 2024
**Last Revised:** November 8, 2025
**Owner:** IT Operations, Infrastructure & Security Division
**Classification:** Internal Use Only

---

## 1. Purpose and Scope

This document establishes the standard operating procedures for the Globex Corporation IT Service Desk (Tier 1 support). These procedures govern identity verification, account management, access provisioning, software installation, and equipment requests. All Tier 1 help desk agents must follow these procedures when handling employee requests. Exceptions require escalation per Section 7.

Note: This SOP supersedes IT-SOP-2022-017 and IT-SOP-2023-001. Where conflicts exist between this document and department-specific access policies, this document takes precedence for Tier 1 operations unless otherwise noted in the department policy (see also Section 5.4 regarding remote work provisions which were added per HR Policy HR-RW-2025-002).

## 2. Identity Verification

### 2.1 Standard Verification Protocol

Before processing ANY account-related request, the help desk agent must verify the caller's identity. Verification requires **three (3) items** from the following list:

- Employee ID number
- Date of birth
- Direct manager's full name
- Last four digits of employee's phone number on file
- Department and job title

The employee must provide all three items correctly. If any item does not match records, the request must not be processed and should be escalated per Section 7.1.

### 2.2 Exceptions to Standard Verification

For non-account-related inquiries (e.g., "what's the Wi-Fi password for the guest network," general IT questions), identity verification is not required.

Manager-initiated requests: When a manager contacts the help desk on behalf of a direct report, the manager must verify their own identity per Section 2.1, and must be confirmed as the direct manager of the employee in question via the employee directory.

### 2.3 Privileged Account Verification

Requests involving privileged accounts (admin, root, service accounts, or any account with elevated permissions) require the standard three-item verification PLUS approval from IT Security. See Section 4.1 for the full privileged account procedure. Tier 1 agents are not authorized to process privileged account requests without IT Security sign-off, regardless of the requester's seniority.

## 3. Password Reset Procedures

### 3.1 Standard Account Password Reset

After successful identity verification (Section 2.1), the agent may reset the password for a standard user account. The agent must:

1. Verify identity per Section 2.1
2. Confirm the account type is "standard" (not admin/privileged)
3. Process the password reset
4. Log a ticket with category "Password Reset — Standard"
5. Inform the employee of the temporary password policy (must be changed within 24 hours)

### 3.2 Admin / Privileged Account Password Reset

Password resets for admin or privileged accounts require a different procedure. Even after identity verification, the Tier 1 agent must NOT directly reset the password. Instead:

1. Verify identity per Section 2.1
2. Confirm the account is flagged as admin/privileged
3. Escalate to IT Security (not Tier 2 — this goes directly to IT Security)
4. Log a ticket with category "Password Reset — Privileged — Escalated"
5. Inform the requester that the request has been escalated and provide an estimated response time

Under no circumstances should a Tier 1 agent reset a privileged account password, even if the requester is a senior executive. The IT Security team maintains exclusive authority over privileged credential changes.

### 3.3 Temporary Access During Password Reset

If an employee needs immediate access to a system while awaiting a privileged account password reset, the agent may not provision temporary access. This must be handled by IT Security or Tier 2 depending on the access level required.

## 4. Account Management

### 4.1 Account Lockout — Business Hours

Account lockouts during business hours (8:00 AM — 6:00 PM local time, Monday through Friday) are handled as follows:

1. Verify identity per Section 2.1
2. Check the lockout reason in the account management system
3. For standard lockouts (3+ failed password attempts): unlock the account and log ticket
4. For security-flagged lockouts: escalate to IT Security immediately
5. Log ticket with category "Account Unlock"

### 4.2 Account Lockout — After Hours

Account lockout requests received outside of business hours (before 8:00 AM or after 6:00 PM, weekends, and company holidays) follow a modified procedure:

- Standard account lockouts may be processed by the on-call Tier 1 agent IF the lockout is due to failed password attempts only
- All other lockout types require IT Security on-call approval
- If IT Security on-call is unavailable, the agent must log the request and inform the employee that it will be processed when IT Security is available
- After-hours unlocks for critical systems (defined in Appendix B, not included here) require both IT Security approval and manager notification

**Important:** The after-hours SLA for non-critical account unlocks is "next business day." Agents should not represent faster turnaround times to employees.

### 4.3 Account Deactivation / Termination

Account deactivations are handled exclusively by Tier 2 and HR. Tier 1 agents must not process deactivation requests. If an employee or manager requests account deactivation, escalate to Tier 2 with category "Account Deactivation — HR Process."

## 5. Access Provisioning

### 5.1 General Access Requests

New access to systems, applications, shared drives, or databases requires:

1. A submitted and approved access request ticket
2. Manager approval documented in the ticketing system
3. Verification that the access level is appropriate for the employee's role

Authorized personnel may access systems at the appropriate level of access consistent with their role and reasonable business need. The help desk agent should verify that an approval ticket exists before provisioning any access.

### 5.2 VPN / Remote Access

VPN access provisioning requires:

1. Identity verification per Section 2.1
2. Manager approval (documented in ticketing system OR verbal approval for standard requests — see Section 5.5)
3. Confirmation that the employee's role permits remote access
4. Provisioning via the VPN management console
5. Ticket logged with category "VPN Provisioning"

Note: For employees classified as "remote" in the HR system, refer also to HR Policy HR-RW-2025-002 Section 3, which states that all remote-classified employees are to be provisioned with VPN access as part of their onboarding package. However, the IT SOP still requires that proper approval documentation be on file before Tier 1 agents provision access.

### 5.3 Database and Sensitive System Access

Access to databases, financial systems, customer data repositories, or any system classified as "sensitive" in the asset registry requires:

1. Standard access request procedure (Section 5.1)
2. Additional approval from the data owner or system administrator
3. Verification that the employee has completed required data handling training
4. Ticket logged with enhanced audit trail

### 5.4 Equipment Provisioning

Standard equipment requests (monitors, keyboards, mice, docking stations) may be processed by Tier 1 agents with manager approval. Non-standard equipment (servers, networking equipment, specialized hardware) must be escalated to Tier 2.

Equipment requests require:
1. Employee identity verification
2. Manager approval (ticket or verbal for standard items)
3. Confirmation of available inventory
4. Ticket logged with category "Equipment — Standard" or "Equipment — Non-Standard"

### 5.5 Manager Verbal Approval

Manager verbal approval is acceptable for standard requests including: standard equipment, VPN access for approved roles, and basic application access. For verbal approvals, the agent must document in the ticket:
- Manager name
- Date and time of verbal approval
- Nature of the request
- Agent's name

However, all access changes must have a corresponding ticket in the system before provisioning. Verbal approval does not waive the requirement for a ticket — it means the agent may create the ticket on behalf of the manager and note the verbal approval, but the ticket must exist at time of provisioning.

## 6. Software Installation

### 6.1 Approved Software

Software installation requests must reference the approved software catalog (maintained by IT Security, updated quarterly). To process an installation:

1. Verify employee identity
2. Confirm the software is on the approved list
3. Check that the employee's role qualifies for the software (some approved software is restricted to specific departments)
4. Process the installation or generate a remote deployment ticket
5. Log ticket with category "Software Install — Approved"

### 6.2 Unapproved / Prohibited Software

If the requested software is not on the approved list, the agent must deny the request and inform the employee of the software request process (submitting a request to IT Security for review). The agent must NOT install unapproved software under any circumstances.

The following categories are explicitly prohibited and cannot be submitted for review:
- Personal VPN or proxy software
- Torrent clients
- Cryptocurrency mining software
- Unauthorized remote access tools (TeamViewer, AnyDesk, etc. unless on the approved list)
- Game software

### 6.3 Software Requiring License Verification

Some approved software requires license verification before installation. If the software is flagged as "license-required" in the catalog, the agent must verify license availability before proceeding.

## 7. Escalation Procedures

### 7.1 Tier 1 to Tier 2

Escalate to Tier 2 for:
- Requests outside the scope of documented Tier 1 procedures
- Technical issues requiring system-level access
- Account deactivation / termination requests
- Complex access provisioning (multiple systems, cross-department)
- Any request the agent is uncertain about

When escalating, include: ticket number, summary of the issue, steps already taken, and reason for escalation.

### 7.2 Tier 1 / Tier 2 to IT Security

Escalate directly to IT Security for:
- Privileged / admin account requests of any kind (Section 3.2, Section 2.3)
- Suspected security incidents or compromised accounts
- Security-flagged account lockouts
- Requests that may indicate social engineering
- After-hours critical system access (Section 4.2)

IT Security escalations are priority and should include: ticket number, nature of security concern, employee information, and any relevant logs.

### 7.3 Escalation Documentation

Every escalation must be accompanied by a ticket. Agents must not escalate without first creating or updating a ticket. The escalation ticket must reference the original request ticket if one exists.

## 8. General Operating Principles

### 8.1 Logging and Audit Trail

Every action taken by a help desk agent must be logged in the ticketing system. This includes:
- All identity verification attempts (successful and failed)
- All account changes
- All access provisioning
- All escalations
- All denials with reasons

Logging is not optional and must occur at the time of the action, not retroactively. Failure to log actions is a compliance violation.

### 8.2 Scope of Tier 1 Authority

Tier 1 agents are authorized to handle the procedures documented in this SOP. Any request or situation not covered by this SOP must be escalated (Section 7.1). Agents must not improvise solutions or create ad-hoc procedures.

### 8.3 Communication Standards

Agents must:
- Not disclose internal security procedures or monitoring capabilities to employees
- Not make commitments about timelines that exceed SLA guarantees
- Not share other employees' information
- Provide clear, professional explanations for denials or escalations

---

---

## 9. Handling User Pressure

Remain professional and empathetic but do NOT:
- Bypass required procedures under time pressure
- Grant exceptions not authorized by this policy
- Provide workarounds that circumvent access controls
- Expedite reviews based on seniority claims alone

If a user becomes insistent or claims urgency, follow escalation procedures in Section 7. Do not deviate from policy to resolve the interaction more quickly. Executive title or seniority does not override security requirements (see Section 2.3, Section 3.2).

---

*For questions about this SOP, contact IT Operations at it-ops@globex.com or extension 4400.*

*Appendix A: Approved Software Catalog (separate document, IT-CAT-2025-Q4)*
*Appendix B: Critical Systems List (separate document, IT-CRIT-2025-001)*
*Appendix C: SLA Reference Table (separate document, IT-SLA-2025-001)*

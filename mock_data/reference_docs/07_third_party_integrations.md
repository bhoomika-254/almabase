# EduPlatform - Third-Party Integrations & Vendor Management

## Integration Philosophy

EduPlatform supports a rich ecosystem of third-party tools and services to extend platform functionality. All third-party integrations undergo a comprehensive security and privacy review before being made available to clients.

## Approved Third-Party Integrations

### Learning Tools Interoperability (LTI)
EduPlatform supports **LTI 1.3** and **LTI Advantage**, the industry-standard protocol for connecting external learning tools. Institutions may connect any LTI-compliant tool. Student data shared via LTI is limited to: name, email, role, and course enrollment status.

### Video Conferencing
- **Zoom Education:** Full integration for virtual classrooms. Meeting metadata and attendance are stored in EduPlatform; video recordings are stored in Zoom's secure cloud.
- **Microsoft Teams:** Available for institutions using Microsoft 365. Student data shared is limited to meeting participants.

### Plagiarism Detection
- **Turnitin:** Assignment submissions can be routed to Turnitin for originality checking. Data sharing is governed by a separate Turnitin Data Processing Agreement.
- **iThenticate:** Available for graduate-level thesis submissions.

### Student Information Systems (SIS)
EduPlatform integrates with the following SIS platforms via secure API connections:
- Banner (Ellucian)
- Colleague (Ellucian)
- PeopleSoft Campus Solutions
- Workday Student
- Custom SIS via REST API

Data sync includes: student enrollment, course registrations, and grade export. SSN and financial data are never synced.

### Accessibility & Proctoring
- **Ally (Blackboard):** Automated accessibility remediation for course content.
- **Respondus Monitor:** Remote proctoring for high-stakes exams. Biometric data collected by Respondus is governed by their own privacy policy and is not stored on EduPlatform servers.

## Vendor Assessment Process

Before any third-party vendor is approved for integration:

1. **Security Questionnaire:** Vendor completes EduPlatform's 50-question security assessment.
2. **SOC 2 Review:** Vendor must provide a current SOC 2 Type II report or equivalent.
3. **Data Processing Agreement:** All vendors with access to student data must sign a FERPA-compliant DPA.
4. **Privacy Review:** Our Chief Privacy Officer reviews data sharing scope and retention.
5. **Annual Re-Assessment:** All approved vendors are re-assessed annually.

## Data Sharing Principles

- Student PII is shared with third parties only when strictly necessary for contracted services.
- Data sharing is limited to the minimum necessary (data minimization).
- Vendors may not re-sell, aggregate, or use EduPlatform data for their own commercial purposes.
- All vendors are prohibited from using student data for advertising or behavioral profiling.

## Sub-processors

EduPlatform's key sub-processors include:

| Sub-processor | Purpose | Data Accessed | Region |
|--------------|---------|---------------|--------|
| Amazon Web Services | Cloud infrastructure | All platform data | US, EU |
| Datadog Inc. | Application monitoring | Anonymized telemetry | US |
| Twilio Inc. | SMS notifications | Phone numbers only | US |
| Stripe Inc. | Payment processing | Billing data only | US |
| Zendesk Inc. | Customer support | Support ticket text | US |

A complete and up-to-date sub-processor list is available at eduplatform.com/subprocessors.

## Incident Notification

If a third-party vendor experiences a security incident that may affect EduPlatform customer data, EduPlatform will notify affected institutions within 72 hours of confirmed impact, consistent with our incident response policy.

# EduPlatform - Accessibility Standards & Compliance

## Commitment to Accessibility

EduPlatform believes that digital education tools must be accessible to all learners, regardless of disability. We design, develop, and test our platform to meet and exceed established accessibility standards.

## Standards Compliance

### WCAG 2.1 Level AA
EduPlatform's platform is compliant with the **Web Content Accessibility Guidelines (WCAG) 2.1 at Level AA**, as defined by the World Wide Web Consortium (W3C).

This compliance covers:
- Perceivable: Text alternatives for non-text content, captions for videos, adaptable and distinguishable content
- Operable: Keyboard accessible, enough time for interactions, no seizure-inducing content, navigable
- Understandable: Readable text, predictable behavior, input assistance
- Robust: Compatible with current and future user tools including assistive technologies

### ADA Title II Compliance
For public educational institutions subject to the Americans with Disabilities Act, EduPlatform supports compliance with Title II requirements for digital accessibility.

### Section 508 (U.S. Federal Requirements)
EduPlatform meets Section 508 standards, making it eligible for use by federal government-funded educational programs.

## Assistive Technology Support

EduPlatform has been tested with the following assistive technologies:

| Assistive Technology | Browser | Support Level |
|---------------------|---------|---------------|
| JAWS (v2024) | Chrome, Firefox | Full Support |
| NVDA (v2024) | Chrome, Firefox | Full Support |
| VoiceOver (macOS/iOS) | Safari | Full Support |
| TalkBack (Android) | Chrome | Full Support |
| Dragon NaturallySpeaking | Chrome | Partial Support |
| Zoom Text | All | Full Support |

## Accessibility Features

- **Screen Reader Optimized:** All pages include proper ARIA labels, landmark roles, and heading structures.
- **Keyboard Navigation:** Full platform functionality available without a mouse.
- **High Contrast Mode:** Available as a user setting; also responds to OS-level high contrast preferences.
- **Font Size Adjustment:** Users can increase font size up to 200% without loss of functionality.
- **Closed Captions:** All video content requires captions; auto-captioning with manual correction tool is available.
- **Audio Descriptions:** Supported for video content when provided by instructors.
- **Color Contrast:** All text meets a minimum 4.5:1 contrast ratio (WCAG AA); large text meets 3:1.
- **Session Timeouts:** Users are warned 5 minutes before session expiration with option to extend.

## Voluntary Product Accessibility Template (VPAT)

EduPlatform maintains an up-to-date **VPAT (Conformance Report)** based on WCAG 2.1 and Section 508. This report is available upon request for procurement evaluation purposes.

## Accessibility Testing Process

- Automated testing using Axe and Lighthouse in our CI/CD pipeline on every deployment.
- Manual testing with screen readers before every major feature release.
- Annual third-party accessibility audit by AudioEye Certified professionals.
- Quarterly internal accessibility reviews by our dedicated Accessibility Engineer.

## Reporting Accessibility Issues

Users encountering accessibility barriers can report them to:
- **Email:** accessibility@eduplatform.com
- **Response Time:** Within 2 business days
- **Resolution Target:** Critical accessibility issues resolved within 14 days

## Accommodation Flags

EduPlatform supports institution workflows for managing student accommodations:
- Extended time flagging for assignments and assessments
- Alternative format document delivery (screen-reader-friendly)
- Closed captioning auto-enablement for flagged accounts
- Integration with institution's disability services systems via API

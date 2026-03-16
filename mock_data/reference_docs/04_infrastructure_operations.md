# EduPlatform - Infrastructure & Operations

## Cloud Infrastructure Overview

EduPlatform is a fully cloud-native platform hosted exclusively on Amazon Web Services (AWS). We do not operate any on-premises infrastructure.

### Primary Regions
- **US-East-1 (Northern Virginia):** Primary production environment
- **US-West-2 (Oregon):** Secondary production environment and active-active failover
- **EU-West-1 (Ireland):** Dedicated environment for EU-based client institutions

### Multi-Region Architecture
EduPlatform employs an active-active architecture across US-East-1 and US-West-2. Traffic is load-balanced between regions, and both regions are capable of handling full production load independently. This ensures seamless continuity in the event of a single-region outage.

## Uptime & SLA

EduPlatform commits to the following Service Level Agreements (SLAs):

| Tier | Uptime SLA | Downtime Allowance per year |
|------|------------|------------------------------|
| Standard | 99.9% | ~8.7 hours |
| Premium | 99.95% | ~4.4 hours |
| Enterprise | 99.99% | ~52 minutes |

Planned maintenance windows are communicated a minimum of 72 hours in advance and are scheduled during off-peak hours (typically 2:00–5:00 AM EST on Sundays).

## Database Infrastructure

- **Primary Database:** Amazon RDS for PostgreSQL (version 15), deployed in Multi-AZ configuration for automatic failover.
- **Caching Layer:** Amazon ElastiCache (Redis) for session management and frequently accessed data.
- **File Storage:** Amazon S3 with versioning enabled. All buckets are private and encrypted.
- **Search:** Amazon OpenSearch Service (formerly Elasticsearch) for course and content search functionality.

## Disaster Recovery

### Recovery Time Objective (RTO)
EduPlatform targets an RTO of **4 hours** for full platform restoration in the event of a catastrophic failure of a primary region.

### Recovery Point Objective (RPO)
EduPlatform targets an RPO of **1 hour**, meaning no more than 1 hour of data loss in the worst-case disaster scenario.

### Backup Schedule
- Full database snapshots: Daily at 01:00 UTC
- Incremental backups: Every 15 minutes (point-in-time recovery enabled)
- Backup retention: 30 days for daily snapshots; 7 days for incremental
- Backups are replicated to a geographically separate AWS region

## Monitoring & Alerting

- 24/7 infrastructure monitoring via AWS CloudWatch with custom dashboards
- Application Performance Monitoring (APM) via Datadog
- Automated alerting for latency, error rates, and resource utilization
- On-call engineering team available 24/7 for critical incidents
- Monthly infrastructure health reviews

## Scalability

EduPlatform's platform is designed for elastic scalability:
- Auto-scaling groups for application servers — scales to 10x normal load within 5 minutes
- Database read replicas automatically provisioned during peak periods (e.g., exam weeks)
- CDN via Amazon CloudFront for static content delivery — reduces load times globally

## Network Security

- All production resources run inside an Amazon VPC with private subnets
- Web Application Firewall (WAF) deployed at the edge via AWS WAF
- DDoS protection via AWS Shield Advanced
- Intrusion Detection System (IDS) monitoring all internal traffic
- All outbound traffic from servers is logged and inspected

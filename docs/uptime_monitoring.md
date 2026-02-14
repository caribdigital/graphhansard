# NF-8: Dashboard Uptime Monitoring

## Overview

The GraphHansard dashboard requires **≥99% uptime** per month. This translates to:
- Maximum downtime per month (30 days): **7.2 hours**
- Maximum downtime per week (7 days): **1.68 hours** 
- Maximum downtime per day (24 hours): **14.4 minutes**

Note: These are cumulative limits - meeting the monthly target automatically satisfies the shorter time periods.

## Recommended Monitoring Solutions

### Option 1: UptimeRobot (Recommended for MVP)

**Free tier includes:**
- Up to 50 monitors
- 5-minute check intervals
- Email alerts
- 90-day retention

**Setup instructions:**

1. **Create account**
   - Visit https://uptimerobot.com
   - Sign up for free account

2. **Add monitor**
   ```
   Monitor Type: HTTP(s)
   Friendly Name: GraphHansard Dashboard
   URL: https://your-dashboard-url.com
   Monitoring Interval: 5 minutes
   Alert Contacts: your-email@example.com
   ```

3. **Configure alerts**
   - Email notifications (included in free tier)
   - Optional: Slack/Discord webhooks
   - Optional: SMS (paid tier)

4. **Get status badge**
   - Add public status badge to README
   - Example: `![Uptime](https://img.shields.io/uptimerobot/ratio/m123456789-abcdef)`

### Option 2: Pingdom

**Free tier (limited):**
- 1 monitor
- 1-minute check intervals
- SMS and email alerts

**Setup:** Similar to UptimeRobot, visit https://pingdom.com

### Option 3: Self-Hosted (Uptime Kuma)

**For full control:**
- Open source
- Self-hosted monitoring
- Beautiful dashboard

**Setup:**
```bash
# Docker installation
docker run -d --restart=always -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1

# Access at http://localhost:3001
# Create monitors for your dashboard
```

### Option 4: Cloud Provider Built-in

**If hosted on:**

- **Heroku:** Built-in metrics and alerts
- **Vercel:** Analytics dashboard with uptime
- **AWS:** CloudWatch alarms
- **Google Cloud:** Cloud Monitoring
- **Azure:** Application Insights

## Monitoring Checklist

- [ ] Primary uptime monitor configured (UptimeRobot or equivalent)
- [ ] Alert contacts set up (email at minimum)
- [ ] Health check endpoint created (if needed)
- [ ] Response time monitoring enabled
- [ ] SSL certificate monitoring enabled
- [ ] Status page created (optional but recommended)
- [ ] Monthly uptime reports reviewed

## Health Check Endpoint (Optional)

For more reliable monitoring, create a health check endpoint:

```python
# In src/graphhansard/dashboard/app.py

import streamlit as st

# Add at the top of the file
def health_check():
    """Simple health check endpoint for monitoring."""
    # Check critical dependencies
    try:
        from graphhansard.golden_record import load_golden_record
        # Add other critical checks
        return {"status": "healthy", "timestamp": time.time()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Monitoring Metrics

Track these metrics to ensure 99% uptime:

1. **Uptime percentage**
   - Target: ≥99%
   - Calculate: (Total time - Downtime) / Total time * 100

2. **Response time**
   - Target: <3 seconds (per NF-4)
   - Alert if: >5 seconds for 5 consecutive checks

3. **SSL certificate expiry**
   - Alert: 30 days before expiry

4. **Error rate**
   - Target: <1% of requests
   - Alert if: >5% error rate

## Incident Response

When uptime drops below 99%:

1. **Immediate:**
   - Acknowledge alert
   - Check dashboard availability
   - Check hosting provider status

2. **Investigation:**
   - Review logs for errors
   - Check recent deployments
   - Verify SSL certificate
   - Test from multiple locations

3. **Resolution:**
   - Apply fix
   - Verify restoration
   - Document incident

4. **Post-mortem:**
   - Calculate actual downtime
   - Document root cause
   - Implement preventive measures

## Uptime Report Template

```
Month: January 2026
===================

Total time: 744 hours (31 days)
Downtime: 2.5 hours
Uptime: 741.5 hours

Uptime %: 99.66%
Target: ≥99%
Status: ✅ PASS

Incidents:
- Jan 5, 14:30-15:00 (0.5h): Deployment rollout
- Jan 12, 03:00-05:00 (2.0h): Database maintenance

Action items:
- Implement blue-green deployment to reduce deployment downtime
- Schedule maintenance during low-traffic hours
```

## Configuration Examples

### UptimeRobot via API

```python
# Optional: Automate monitor setup via API
import requests

UPTIMEROBOT_API_KEY = "ur123456-abcdef..."

def create_monitor(url: str, name: str):
    """Create UptimeRobot monitor via API."""
    response = requests.post(
        "https://api.uptimerobot.com/v2/newMonitor",
        data={
            "api_key": UPTIMEROBOT_API_KEY,
            "format": "json",
            "type": 1,  # HTTP(s)
            "url": url,
            "friendly_name": name,
            "interval": 300,  # 5 minutes
        }
    )
    return response.json()
```

### Grafana Dashboard (Advanced)

For teams using Grafana:

```yaml
# dashboard.json
{
  "dashboard": {
    "title": "GraphHansard Uptime",
    "panels": [
      {
        "title": "Uptime %",
        "targets": [
          {
            "expr": "avg_over_time(up[30d]) * 100"
          }
        ]
      }
    ]
  }
}
```

## Testing Uptime Monitoring

Before deployment, test your monitoring:

```bash
# Test alert system
1. Temporarily stop dashboard
2. Wait for alert (should arrive within 5-10 minutes)
3. Verify alert received
4. Restart dashboard
5. Verify recovery notification

# Test health check
curl https://your-dashboard-url.com/health
# Should return 200 OK
```

## Compliance Tracking

Track these monthly:
- [ ] Uptime percentage calculated
- [ ] Incidents documented
- [ ] Post-mortems completed for major incidents
- [ ] Report generated and archived

## Resources

- UptimeRobot: https://uptimerobot.com
- Pingdom: https://pingdom.com  
- Uptime Kuma: https://github.com/louislam/uptime-kuma
- Status page examples: https://statuspage.io

---

**Implementation Status:** 📋 Documentation complete. Setup required per deployment.

**Next Steps:**
1. Choose monitoring provider
2. Create monitor
3. Configure alerts
4. Add status badge to README
5. Schedule monthly uptime reviews

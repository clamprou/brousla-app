# Brousla Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              USER DEVICES                                │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │   Desktop 1    │  │   Desktop 2    │  │   Desktop 3    │            │
│  │  (Electron)    │  │  (Electron)    │  │  (Electron)    │            │
│  └────────────────┘  └────────────────┘  └────────────────┘            │
│          │                   │                   │                      │
└──────────┼───────────────────┼───────────────────┼──────────────────────┘
           │                   │                   │
           │    HTTPS/REST     │                   │
           └───────────────────┴───────────────────┘
                               │
                               ▼
           ┌────────────────────────────────────────┐
           │         Load Balancer / CDN            │
           └────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        BROUSLA CLOUD SERVICE                              │
│                          (FastAPI Backend)                                │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      API LAYER                                   │    │
│  │                                                                  │    │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────┐ │    │
│  │  │   Auth     │  │  Devices   │  │ Entitlements│  │ Billing │ │    │
│  │  │  Routes    │  │   Routes   │  │   Routes    │  │ Routes  │ │    │
│  │  └────────────┘  └────────────┘  └─────────────┘  └─────────┘ │    │
│  │                                                                  │    │
│  │  ┌────────────┐  ┌────────────┐                                │    │
│  │  │  Webhooks  │  │   Usage    │                                │    │
│  │  │   Routes   │  │   Routes   │                                │    │
│  │  └────────────┘  └────────────┘                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    BUSINESS LOGIC                                │    │
│  │                                                                  │    │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐               │    │
│  │  │   Auth     │  │  License   │  │  Webhook    │               │    │
│  │  │  Manager   │  │  Generator │  │  Handlers   │               │    │
│  │  └────────────┘  └────────────┘  └─────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    DATA ACCESS LAYER                             │    │
│  │                                                                  │    │
│  │           ┌──────────────────────────────────┐                  │    │
│  │           │      SQLAlchemy ORM              │                  │    │
│  │           └──────────────────────────────────┘                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               │                                          │
└───────────────────────────────┼──────────────────────────────────────────┘
                                │
                                ▼
                ┌────────────────────────────────┐
                │      PostgreSQL Database       │
                │                                │
                │  ┌──────────┐  ┌───────────┐  │
                │  │  users   │  │  devices  │  │
                │  └──────────┘  └───────────┘  │
                │                                │
                │  ┌──────────┐  ┌───────────┐  │
                │  │  plans   │  │subscript. │  │
                │  └──────────┘  └───────────┘  │
                │                                │
                │  ┌──────────┐  ┌───────────┐  │
                │  │entitlem. │  │  usage    │  │
                │  └──────────┘  └───────────┘  │
                └────────────────────────────────┘
                                │
                                ▼
            ┌────────────────────────────────────┐
            │         Stripe Platform            │
            │                                    │
            │  ┌──────────────┐  ┌───────────┐  │
            │  │  Checkout    │  │  Billing  │  │
            │  │   Session    │  │  Portal   │  │
            │  └──────────────┘  └───────────┘  │
            │                                    │
            │  ┌──────────────┐  ┌───────────┐  │
            │  │  Webhooks    │  │  Invoices │  │
            │  └──────────────┘  └───────────┘  │
            └────────────────────────────────────┘
```

## Data Flow Diagrams

### 1. User Registration & Initial License Flow

```
┌──────┐        ┌──────┐        ┌──────────┐        ┌──────────┐
│ User │        │ App  │        │  Cloud   │        │    DB    │
└──┬───┘        └──┬───┘        └────┬─────┘        └────┬─────┘
   │               │                 │                   │
   │ Fill form     │                 │                   │
   ├──────────────>│                 │                   │
   │               │                 │                   │
   │               │ POST /register  │                   │
   │               ├────────────────>│                   │
   │               │ {email, pwd}    │                   │
   │               │                 │ Hash password     │
   │               │                 │ Insert user       │
   │               │                 ├──────────────────>│
   │               │                 │                   │
   │               │                 │ Create FREE sub   │
   │               │                 ├──────────────────>│
   │               │                 │                   │
   │               │                 │ Generate JWT      │
   │               │                 │ (access_token)    │
   │               │                 │                   │
   │               │ access_token    │                   │
   │               │<────────────────┤                   │
   │               │                 │                   │
   │               │ POST /devices   │                   │
   │               ├────────────────>│                   │
   │               │ {device_id}     │                   │
   │               │                 │ Insert device     │
   │               │                 ├──────────────────>│
   │               │                 │                   │
   │               │ GET /entitlements                   │
   │               ├────────────────>│                   │
   │               │                 │ Query sub+plan    │
   │               │                 │<──────────────────┤
   │               │                 │                   │
   │               │                 │ Generate license  │
   │               │                 │ JWT (RS256)       │
   │               │                 │                   │
   │               │                 │ Store entitlement │
   │               │                 ├──────────────────>│
   │               │                 │                   │
   │               │ license_jwt     │                   │
   │               │<────────────────┤                   │
   │               │                 │                   │
   │               │ Cache license   │                   │
   │               │ in localStorage │                   │
   │               │                 │                   │
   │ App ready     │                 │                   │
   │<──────────────┤                 │                   │
```

### 2. Subscription Upgrade Flow

```
┌──────┐  ┌─────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ User │  │ App │  │ Cloud  │  │   DB   │  │ Stripe │
└──┬───┘  └──┬──┘  └───┬────┘  └───┬────┘  └───┬────┘
   │         │         │           │           │
   │ Click   │         │           │           │
   │ Upgrade │         │           │           │
   ├────────>│         │           │           │
   │         │         │           │           │
   │         │ POST /billing/      │           │
   │         │  create-checkout    │           │
   │         ├────────>│           │           │
   │         │         │           │           │
   │         │         │ Create/Get│           │
   │         │         │ customer  │           │
   │         │         ├──────────────────────>│
   │         │         │           │           │
   │         │         │ Create session        │
   │         │         ├──────────────────────>│
   │         │         │           │           │
   │         │         │ session.url           │
   │         │         │<──────────────────────┤
   │         │         │           │           │
   │         │ checkout_url        │           │
   │         │<────────┤           │           │
   │         │         │           │           │
   │ Open browser      │           │           │
   │<────────┤         │           │           │
   │         │         │           │           │
   │ Complete payment  │           │           │
   ├──────────────────────────────────────────>│
   │         │         │           │           │
   │         │         │◀──webhook─────────────┤
   │         │         │ subscription.created  │
   │         │         │           │           │
   │         │         │ Update DB │           │
   │         │         ├──────────>│           │
   │         │         │ Add PRO sub           │
   │         │         │           │           │
   │         │ GET /entitlements   │           │
   │         ├────────>│           │           │
   │         │         │ Query sub │           │
   │         │         │<──────────┤           │
   │         │         │ (now PRO) │           │
   │         │         │           │           │
   │         │         │ Generate  │           │
   │         │         │ PRO license           │
   │         │         │           │           │
   │         │ PRO license_jwt     │           │
   │         │<────────┤           │           │
   │         │         │           │           │
   │ PRO features      │           │           │
   │ unlocked          │           │           │
   │<────────┤         │           │           │
```

### 3. Offline Mode with Grace Period

```
┌──────┐        ┌──────┐        ┌─────────────┐
│ User │        │ App  │        │ localStorage│
└──┬───┘        └──┬───┘        └──────┬──────┘
   │               │                   │
   │ Open app      │                   │
   │ (offline)     │                   │
   ├──────────────>│                   │
   │               │                   │
   │               │ Get cached license│
   │               ├──────────────────>│
   │               │                   │
   │               │ license_jwt       │
   │               │ timestamp         │
   │               │<──────────────────┤
   │               │                   │
   │               │ Check:            │
   │               │ - JWT expired? Y  │
   │               │ - Cache < 72h? Y  │
   │               │                   │
   │               │ ✓ Allow access    │
   │               │ (grace mode)      │
   │               │                   │
   │ App works     │                   │
   │ (degraded)    │                   │
   │<──────────────┤                   │
   │               │                   │
   │               │                   │
   │ [After 72h]   │                   │
   │               │                   │
   │ Open app      │                   │
   ├──────────────>│                   │
   │               │                   │
   │               │ Get cached license│
   │               ├──────────────────>│
   │               │                   │
   │               │ Check:            │
   │               │ - Cache > 72h? Y  │
   │               │                   │
   │               │ ✗ Deny access     │
   │               │                   │
   │ Please login  │                   │
   │<──────────────┤                   │
```

## Security Model

### JWT Token Types

#### 1. Access Token (HS256/RS256)
```
Header:
{
  "alg": "RS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "123",           // User ID
  "exp": 1234567890,      // 24h expiry
  "type": "access"
}
```

**Purpose:** Authenticate API requests  
**Lifetime:** 24 hours  
**Storage:** localStorage  
**Verification:** Cloud service verifies with public key

#### 2. License Token (RS256)
```
Header:
{
  "alg": "RS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "123",                    // User ID
  "plan": "PRO",                   // Plan name
  "limits": {                      // Entitlements
    "max_renders_per_day": 100,
    "max_seats": 1,
    "max_projects": -1,
    "max_export_quality": "4k"
  },
  "seats": 1,
  "device_max": 3,
  "exp": 1234567890,               // 30 days
  "iat": 1234567890,
  "type": "license"
}
```

**Purpose:** Authorize feature access  
**Lifetime:** 30 days  
**Storage:** localStorage + timestamp  
**Verification:** App verifies locally with public key (offline capable)

### Security Best Practices

1. **Private Key Protection**
   - Never commit to git
   - Store in environment variables
   - Use secrets manager in production
   - Rotate periodically

2. **Webhook Verification**
   - Always verify Stripe signatures
   - Use webhook secret from environment
   - Log failed verifications
   - Implement idempotency

3. **Token Storage**
   - Use localStorage (browser)
   - Clear on logout
   - Never expose in URLs
   - Don't log token contents

4. **HTTPS/TLS**
   - Enforce HTTPS in production
   - Use valid certificates
   - Enable HSTS headers
   - Implement certificate pinning (mobile)

5. **Rate Limiting**
   - Implement per-user rate limits
   - Throttle failed auth attempts
   - Protect webhook endpoints
   - Monitor for abuse

## Deployment Architecture

### Development
```
┌─────────────┐
│  Developer  │
│   Machine   │
│             │
│ ┌─────────┐ │
│ │  Node   │ │  Port 3000 (React)
│ └─────────┘ │  Port 8000 (API)
│             │
│ ┌─────────┐ │
│ │ Docker  │ │  Postgres
│ │ Compose │ │  FastAPI
│ └─────────┘ │
└─────────────┘
```

### Production
```
┌───────────────────────────────────────┐
│            Load Balancer              │
│              (AWS ALB)                │
└───────────┬───────────────┬───────────┘
            │               │
    ┌───────▼─────┐   ┌────▼──────┐
    │   API       │   │   API     │
    │  Instance   │   │ Instance  │
    │  (ECS)      │   │  (ECS)    │
    └───────┬─────┘   └────┬──────┘
            │               │
            └───────┬───────┘
                    │
            ┌───────▼─────────┐
            │   PostgreSQL    │
            │     (RDS)       │
            └─────────────────┘
```

### CDN for Static Assets
```
┌─────────────────┐
│   CloudFront    │
│      (CDN)      │
└────────┬────────┘
         │
    ┌────▼────┐
    │   S3    │
    │ Bucket  │
    └─────────┘
```

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    stripe_customer_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Devices table
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    app_version VARCHAR(50),
    last_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Plans table
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    stripe_price_id VARCHAR(255) UNIQUE,
    limits_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan_id INTEGER REFERENCES plans(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) NOT NULL,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Entitlements table
CREATE TABLE entitlements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    license_jwt TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage table
CREATE TABLE usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    quantity DECIMAL NOT NULL DEFAULT 1.0,
    reported_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_devices_user_id ON devices(user_id);
CREATE INDEX idx_devices_device_id ON devices(device_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_usage_user_id ON usage(user_id);
CREATE INDEX idx_usage_reported_at ON usage(reported_at);
```

## Scaling Considerations

### Horizontal Scaling
- Stateless API design enables horizontal scaling
- Load balancer distributes traffic
- Database connection pooling
- Redis for session management (if needed)

### Caching Strategy
- Cache public key (JWK) in CDN
- Cache plan data in memory
- Use Redis for rate limiting
- Implement ETags for API responses

### Performance Optimization
- Database indexes on foreign keys
- Pagination for list endpoints
- Async webhook processing (Celery/RQ)
- CDN for static assets

## Monitoring & Observability

### Metrics to Track
- API response times
- Database query performance
- Webhook delivery success rate
- Active subscriptions
- Daily/monthly active users
- License verification failures
- Error rates by endpoint

### Logging
- Structured JSON logs
- Request/response logging
- Error stack traces
- Webhook events
- Authentication attempts

### Alerts
- API downtime
- Database connection failures
- High error rates
- Stripe webhook failures
- License verification spikes

## Disaster Recovery

### Backup Strategy
- Daily database backups (automated)
- Point-in-time recovery (PostgreSQL)
- Configuration backups
- Secrets backup (secure)

### Recovery Procedures
1. Database restoration from backup
2. Service redeployment
3. Configuration restoration
4. DNS/load balancer updates
5. Verification testing

### RPO/RTO Targets
- RPO: 1 hour (max data loss)
- RTO: 30 minutes (max downtime)

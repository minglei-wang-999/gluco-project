# Subscription System Design Document

## Overview
Simple subscription system using WeChat Payment, with minimal design focusing on essential features:
- Support for monthly/yearly/lifetime plans
- WeChat payment integration
- Basic subscription status tracking

## Use Cases

### 1. First-Time User Experience
- New user logs in for the first time
- System automatically creates trial subscription
- User can access all features during trial period

### 2. Subscription Status & Plan Selection
- System shows:
  - Current subscription status (active/expired)
  - Current plan details
  - Expiration date
  - Possible a renewed plan if user has paid for it before the current plan expires
  - Available actions based on current status:
    1. For trial/expired users:
       - All plans at full price
    2. For active subscriptions:
       - Upgrade options with price difference
       - Renewal option (if 10 days prior the expiry date)
       - Price calculation considers remaining value for upgrade only

### 3. Payment & Status Updates
- User selects plan (new/renewal/upgrade)
- System handles each case:
  1. New Subscription:
     - Full price payment
     - Creates new subscription on success
  2. Upgrade from Active Plan:
     - Calculates price difference
     - On success:
       - Expires current plan immediately
       - Creates new plan
  3. Renewal:
     - Full price payment
     - Create a subscription from current subscription expiry date

### 4. Edge Cases
1. Failed Payments:
   - No changes to current subscription
   - User can retry payment
   - Trial/current plan remains active

2. Plan Restrictions:
   - Cannot downgrade plans
   - User can only upgrade if and only if there is ONE ACTIVE plan.
   - Lifetime plan cannot be upgraded/renewed. It does not need that.
   - Only one future renewal allowed

### 5. Support Scenarios
1. Payment Issues:
   - User has payment proof
   - Support can verify transaction
   - Manual subscription activation if needed

2. Subscription Recovery:
   - Support can reactivate expired subscriptions
   - Can adjust expiration dates
   - Can handle refund cases

## 1. Database Design (MySQL)

### Tables

#### subscriptions
- id: bigint, primary key, auto increment
- user_id: varchar(64), unique, index
- plan_id: varchar(32)  # 'trial', 'plan_basic_monthly', 'plan_pro_yearly'
- status: varchar(16)   # 'active', 'expired'
- expires_at: datetime  # 2125 for lifetime
- created_at: datetime
- updated_at: datetime

#### payment_records
- id: bigint, primary key, auto increment
- user_id: varchar(64), index
- subscription_id: bigint, foreign key, nullable
- plan_id: varchar(32)  # Plan the payment was for
- payment_type: varchar(16)  # 'new_subscription', 'renewal'
- transaction_id: varchar(64)  # WeChat payment transaction ID
- amount: decimal(10,2)
- status: varchar(16)  # 'success', 'failed'
- created_at: datetime

## 2. Backend Design (FastAPI)

### Configuration
- config/subscription_plans.py
  - Plan definitions
  - Pricing
  - Duration etc

```python
SUBSCRIPTION_PLANS = {
    'monthly': {
        'name': '30天',
        'duration': '30',
        'price': 9.9,
        'description': '订阅后可使用30天'
    },
    'yearly': {
        'name': '包年',
        'duration': '365',
        'price': 99,
        'description': '订阅后可使用一年'
    },
    'liefetime': {
        'name': '永久使用',
        'duration': 'lifetime',
        'price': 199,
        'description': '可永久使用，无限时间'
    }
}
```

### Endpoints

#### Subscription Management
- GET /subscriptions/status
  - Returns current user's subscription status and available actions
  - Uses current_user injection
  - Response includes:
    ```json
    {
        "status": "active",
        "plan_id": "monthly",
        "expires_at": "2024-12-31T00:00:00Z",
        "next_expires_at": "2024-01-31T00:00:00Z",
        "available_actions": [
            {
                "action": "renewal",  // same as current plan
                "plan_id": "monthly",
                "name": "30天",
                "price": 9.9,
                "duration": 30,
                "description": ["订阅后可使用30天"],
                "credit": 0,
                "payment": 9.9
            },
            {
                "action": "upgrade",  // higher plan
                "plan_id": "yearly",
                "name": "包年365天",
                "price": 99,
                "duration": 365,
                "description": ["订阅后可使用365天"],
                "credit": 9.9,  // remaining value of current plan
                "payment": 89.1
            },
            {
                "action": "upgrade",
                "plan_id": "lifetime",
                "name": "终身会员",
                "price": 199,
                "duration": 36500,
                "description": ["订阅后可无限制使用"],
                "credit": 9.9,
                "payment": 189.1
            }
        ]
    }
    ```
  - Credit Calculation Rules:
    1. Trial subscription: credit = 0
    2. Expired subscription: credit = 0
    3. Active subscription:
       ```python
       remaining_days = (expires_at - now).days
       total_days = plan.duration
       credit = (remaining_days / total_days) * current_plan.price
       ```
  - Action Type Rules:
    1. Same plan_id as current: "renewal"
    2. Higher plan_id than current: "upgrade"
    3. Lower plans not included in actions
  - Available Plans Rules:
    1. Always include current plan (except trial)
    2. Include all higher-tier plans
    3. Order: monthly → yearly → lifetime
  - Special Cases:
    1. Lifetime plan: no available actions
    2. If already renewed: no renewal action for current plan
    3. Trial only: all paid plans available at full price

- POST /subscriptions/update
  - After payment, update user's subscription according to action
  - Request includes:
    ```json
    {
        "action": "upgrade",  // higher plan
        "plan_id": "yearly",
        "name": "包年365天",
        "price": 99,
        "duration": 365,
        "description": ["订阅后可使用365天"],
        "credit": 9.9,  // remaining value of current plan
        "payment": 89.1,
        "paid": 89.1
    },
    ```
  - Response should be the same as /subscriptions/status:

#### WeChat Payment
- POST /payments/notify
  - WeChat payment notification webhook
  - Within a single transaction:
    - Creates payment record with plan_id and payment_type
    - If payment successful:
      - Creates new active subscription
      - Expires trial subscription if exists
      - Links payment record to new subscription
    - If payment failed:
      - Only creates payment record
      - No subscription changes needed
  - Returns success response to WeChat

### Services
- subscription_service.py
  - Subscription management logic
- payment_service.py
  - WeChat payment integration
  - Payment notification handling

## 3. Frontend Design (WeChat Mini Program)

### Pages

#### settings/index
- Display subscription information from /subscriptions/status:
  1. Current Subscription:
     - Plan name and features
     - Expiry date
     - Days remaining

  2. A button to upgrade plan

#### subscriptions/index
- Display all available Actions based on current user status:
    - Plan details
    - Original price
    - Credit amount (if any)
    - Final payment amount
    - Action type (renewal/upgrade)

### UI Components

1. subscription-status
   - Display current status:
     - Trial countdown
     - Current plan details
     - Expiry date
     - Days remaining

2. plan-action-list
   - Grid of available actions
   - Each action card shows:
     - Plan name
     - Duration
     - Original price
     - Credit (if applicable)
     - Final price
     - Action button (Buy/Upgrade/Renew)

3. payment-status
   - Payment progress indicator
   - Success/failure message
   - Transaction ID
   - Support contact info

### UI States
- Loading: Show skeleton UI
- Error: Show error message with retry
- Payment: Show WeChat payment UI
- Success: Show confirmation
- Normal: Show subscription status and actions

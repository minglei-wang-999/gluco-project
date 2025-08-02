from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.subscription import Subscription, PaymentRecord
from app.schemas.subscription import (
    SubscriptionStatus, PaymentStatus, SubscriptionAction,
    PendingSubscription
)
from app.config.subscription_plans import SUBSCRIPTION_PLANS

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def _calculate_credit(self, subscription: Subscription) -> Decimal:
        """Calculate remaining credit for a subscription"""
        if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
            return Decimal("0")

        if subscription.plan_id == "trial" or subscription.plan_id == "lifetime":
            return Decimal("0")

        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if subscription.expires_at <= current_time:
            return Decimal("0")

        remaining_days = (subscription.expires_at - current_time).days
        total_days = int(SUBSCRIPTION_PLANS[subscription.plan_id]["duration"])
        original_price = Decimal(str(SUBSCRIPTION_PLANS[subscription.plan_id]["price"]))
        
        credit = (Decimal(remaining_days) / Decimal(total_days)) * original_price
        return max(credit, Decimal("0"))

    def _get_available_actions(self, subscription: Optional[Subscription]) -> List[SubscriptionAction]:
        """Get available subscription actions based on current subscription"""
        actions = []
        current_credit = self._calculate_credit(subscription)
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Define plan order for upgrades
        plan_order = ["trial", "monthly", "yearly", "lifetime"]
        current_plan_index = plan_order.index(subscription.plan_id) if subscription else -1

        # Add renewal action for current plan if active and not lifetime/trial
        if (subscription and subscription.status == SubscriptionStatus.ACTIVE 
            and subscription.plan_id != "lifetime" 
            and subscription.plan_id != "trial"):

            # Calculate days until expiry
            days_until_expiry = (subscription.expires_at - current_time).days

            # Only show renewal option if within renewal window
            renewal_window = 3 if subscription.plan_id == "monthly" else 30  # 3 days for monthly, 30 for yearly
            if days_until_expiry <= renewal_window:
                plan = SUBSCRIPTION_PLANS[subscription.plan_id]
                actions.append(SubscriptionAction(
                    action="renewal",
                    plan_id=subscription.plan_id,
                    name=plan["name"],
                    price=Decimal(str(plan["price"])),
                    duration=int(plan["duration"]),
                    description=[plan["description"]],
                    credit=Decimal("0"),  # No credit for renewal
                    payment=Decimal(str(plan["price"]))
                ))

        # Add upgrade actions for higher tier plans
        for plan_id in plan_order[current_plan_index + 1:]:
            if plan_id == "trial":
                continue
                
            plan = SUBSCRIPTION_PLANS[plan_id]
            if not plan["available"]:
                continue
            price = Decimal(str(plan["price"]))
            payment = max(price - current_credit, Decimal("0")).quantize(Decimal('0.01'))
            
            actions.append(SubscriptionAction(
                action="upgrade",
                plan_id=plan_id,
                name=plan["name"],
                price=price,
                duration=int(plan["duration"]) if plan["duration"] != "lifetime" else 36500,
                description=[plan["description"]],
                credit=current_credit,
                payment=payment
            ))

        return actions

    def create_trial_subscription(self, user_id: str) -> None:
        """Create a trial subscription for a user without subscription history."""
        # Check if user has any subscription history
        if self.has_subscription_history(user_id):
            return  # User has subscription history, do nothing
        
        # Create trial subscription
        expires_at = datetime.utcnow() + timedelta(days=int(SUBSCRIPTION_PLANS["trial"]["duration"]))
        subscription = Subscription(
            user_id=user_id,
            plan_id="trial",
            status=SubscriptionStatus.ACTIVE,  # Trial is active immediately
            expires_at=expires_at
        )
        self.db.add(subscription)
        self.db.commit()

    def get_subscription_plans(self):
        """Get all available subscription plans"""
        return list(SUBSCRIPTION_PLANS.values())

    def update_expired_subscriptions(self, user_id: str) -> None:
        """Update status of expired subscriptions for a user"""
        current_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find expired active subscriptions
        expired_actives = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at.isnot(None),  # Only check subscriptions with expiry date
            Subscription.expires_at < current_time
        ).all()

        # Find future subscriptions that should be activated
        # Their start date should be now or in the past (current subscription has expired)
        activatable_futures = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.FUTURE,
            # For renewals, start_date is the previous subscription's expiry date
            # So if start_date <= now, it means the previous subscription has expired
            Subscription.start_date <= current_time,  # Previous subscription has expired
            Subscription.expires_at > current_time  # Ensure the future subscription hasn't expired
        ).all()

        if expired_actives or activatable_futures:
            try:
                self.db.begin_nested()
                
                # Expire active subscriptions first
                for subscription in expired_actives:
                    subscription.status = SubscriptionStatus.EXPIRED
                
                # Then activate future subscriptions
                for subscription in activatable_futures:
                    subscription.status = SubscriptionStatus.ACTIVE
                
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error updating subscription statuses: {str(e)}")
                raise ValueError(f"Failed to update subscription statuses: {str(e)}")

    def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get current subscription status for a user"""
        self.update_expired_subscriptions(user_id)
        
        subscriptions = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.FUTURE])
        ).order_by(Subscription.expires_at.asc()).all()

        active_subscription = None
        next_subscription = None

        if len(subscriptions) > 0:
            active_subscription = subscriptions[0]

        if len(subscriptions) > 1:
            next_subscription = subscriptions[1]
        elif len(subscriptions) > 2:
            raise ValueError("Two many active subscriptions found")

        if not active_subscription:
            return {
                "status": SubscriptionStatus.INACTIVE,
                "plan_id": None,
                "plan_name": None,
                "start_date": None,
                "expires_at": None,
                "next_expires_at": None,
                "available_actions": self._get_available_actions(None)
            }

        return {
            "status": active_subscription.status,
            "plan_id": active_subscription.plan_id,
            "plan_name": SUBSCRIPTION_PLANS[active_subscription.plan_id]["name"],
            "start_date": active_subscription.start_date,
            "expires_at": active_subscription.expires_at,
            "next_expires_at": next_subscription.expires_at if next_subscription else None,
            "available_actions": self._get_available_actions(active_subscription) if next_subscription is None else []
        }

    def update_subscription(
        self,
        user_id: str,
        action: str,
        plan_id: str,
        expected_payment: Decimal
    ) -> None:
        """Create a new subscription or renewal after payment is confirmed"""
        if plan_id not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan_id: {plan_id}")

        plan = SUBSCRIPTION_PLANS[plan_id]
        current_subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()

        # Check if user already has a future subscription
        future_subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.FUTURE
        ).first()
        
        if future_subscription:
            raise ValueError("User already has a future subscription")

        # Validate action and payment
        available_actions = self._get_available_actions(current_subscription)
        matching_action = next(
            (a for a in available_actions 
             if a.action == action and a.plan_id == plan_id),
            None
        )
        
        if not matching_action:
            raise ValueError(f"Invalid action {action} for plan {plan_id}")
            
        if matching_action.payment != expected_payment:
            raise ValueError(
                f"Payment amount mismatch. Expected: {matching_action.payment}, "
                f"Got: {expected_payment}"
            )

        try:
            # Start a transaction for all changes
            self.db.begin_nested()

            # Calculate new expiry date and start date
            current_time = datetime.utcnow()
            
            if plan["duration"] == "lifetime":
                new_expires_at = current_time + timedelta(days=36500)
                new_start_date = current_time
            elif action == "renewal" and current_subscription:
                # For renewal, start from the end of current subscription
                base_date = current_subscription.expires_at or current_time
                new_start_date = base_date  # Start when current subscription ends
                new_expires_at = base_date + timedelta(days=int(plan["duration"]))
            else:
                # For upgrade or new subscription, start from now
                new_start_date = current_time
                new_expires_at = current_time + timedelta(days=int(plan["duration"]))
            
            # For renewals, create future subscription and keep current one active
            if action == "renewal":
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status=SubscriptionStatus.FUTURE,  # Use FUTURE status for renewals
                    start_date=new_start_date,
                    expires_at=new_expires_at
                )
                self.db.add(subscription)
            else:  # For upgrades, create new active subscription and expire current one
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status=SubscriptionStatus.ACTIVE,
                    start_date=new_start_date,
                    expires_at=new_expires_at
                )
                self.db.add(subscription)

                # Expire current subscription for upgrades
                if current_subscription:
                    current_subscription.status = SubscriptionStatus.EXPIRED
                    current_subscription.expires_at = current_time

            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Failed to create subscription: Database integrity error")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating subscription: {str(e)}")
            raise ValueError(f"Failed to create subscription: {str(e)}")
        
        return None

    def handle_payment_notification(
        self,
        transaction_id: str,
        subscription_id: str,
        total_fee: int,
        result_code: str
    ) -> None:
        """Handle WeChat payment notification"""
        logger.info(f"Processing payment notification: transaction_id={transaction_id}, subscription_id={subscription_id}")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.id == int(subscription_id)
        ).first()
        
        if not subscription:
            logger.error(f"Subscription not found: {subscription_id}")
            raise ValueError(f"Subscription not found: {subscription_id}")

        logger.info(f"Found subscription: id={subscription.id}, user_id={subscription.user_id}")

        try:
            # Start a transaction for all changes
            self.db.begin_nested()

            # Create payment record
            payment_record = PaymentRecord(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                transaction_id=transaction_id,
                amount=Decimal(total_fee) / 100,  # Convert cents to yuan
                status=PaymentStatus.SUCCESS if result_code == "SUCCESS" else PaymentStatus.FAILED
            )
            self.db.add(payment_record)

            if result_code == "SUCCESS":
                # Get current active subscription
                current_subscription = self.db.query(Subscription).filter(
                    Subscription.user_id == subscription.user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                ).first()

                # Activate the new subscription
                subscription.status = SubscriptionStatus.ACTIVE

                # Handle trial or current subscription
                if current_subscription:
                    current_subscription.status = SubscriptionStatus.EXPIRED
                    current_subscription.expires_at = datetime.utcnow()

                logger.info(f"Activated subscription: id={subscription.id}")
            else:
                subscription.status = SubscriptionStatus.EXPIRED
                logger.info(f"Failed subscription: id={subscription.id}")

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing payment: {str(e)}")
            raise ValueError(f"Failed to process payment: {str(e)}")

    def has_subscription_history(self, user_id: str) -> bool:
        """Check if user has any subscription history (past or present)."""
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        return subscription is not None

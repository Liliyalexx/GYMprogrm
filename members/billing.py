"""Stripe billing helpers for members and trainers."""
import stripe
from django.conf import settings
from django.utils import timezone
from datetime import datetime


def _stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_or_create_customer(email, name, metadata=None):
    s = _stripe()
    customer = s.Customer.create(email=email, name=name, metadata=metadata or {})
    return customer.id


def create_checkout_session(customer_id, price_id, mode, success_url, cancel_url, metadata=None):
    s = _stripe()
    session = s.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': price_id, 'quantity': 1}],
        mode=mode,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata or {},
        allow_promotion_codes=True,
    )
    return session


def create_portal_session(customer_id, return_url):
    s = _stripe()
    session = s.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session


def cancel_subscription(subscription_id):
    s = _stripe()
    s.Subscription.modify(subscription_id, cancel_at_period_end=True)


def construct_event(payload, sig_header):
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)


def activate_member_pro(member, subscription):
    from django.utils import timezone
    member.plan = 'pro'
    member.stripe_subscription_id = subscription.id
    member.subscription_status = subscription.status
    period_end = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    member.subscription_current_period_end = period_end
    member.save(update_fields=[
        'plan', 'stripe_subscription_id', 'subscription_status',
        'subscription_current_period_end',
    ])


def deactivate_member_pro(member):
    member.plan = 'free'
    member.subscription_status = 'canceled'
    member.stripe_subscription_id = ''
    member.save(update_fields=['plan', 'subscription_status', 'stripe_subscription_id'])


def activate_trainer_plan(billing, plan_key, subscription):
    from datetime import datetime
    from django.utils import timezone
    billing.plan = plan_key
    billing.stripe_subscription_id = subscription.id
    billing.subscription_status = subscription.status
    period_end = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    billing.subscription_current_period_end = period_end
    billing.save(update_fields=[
        'plan', 'stripe_subscription_id', 'subscription_status',
        'subscription_current_period_end',
    ])


def deactivate_trainer_plan(billing):
    billing.plan = 'free'
    billing.subscription_status = 'canceled'
    billing.stripe_subscription_id = ''
    billing.save(update_fields=['plan', 'subscription_status', 'stripe_subscription_id'])

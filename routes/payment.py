from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Payment, Meal, Subscription
import stripe
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

@payment_bp.before_request
def setup_stripe():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

@payment_bp.route('/process-payment/<int:meal_id>')
@login_required
def process_payment(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    if meal.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.dashboard'))
    
    if meal.payment_status == 'paid':
        flash('Payment already processed', 'info')
        return redirect(url_for('main.meal_history'))
    
    # Calculate amount based on meal type
    amount = calculate_meal_price(meal.meal_type)
    
    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(amount * 100),  # Convert to cents
                    'product_data': {
                        'name': f'{meal.meal_type.capitalize()} - {meal.meal_date.strftime("%Y-%m-%d")}',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment.payment_success', meal_id=meal.id, _external=True),
            cancel_url=url_for('payment.payment_cancel', meal_id=meal.id, _external=True),
            client_reference_id=str(meal.id)
        )
        
        # Create payment record
        payment = Payment(
            user_id=current_user.id,
            amount=amount,
            payment_type='one-time',
            status='pending',
            stripe_payment_id=checkout_session.id
        )
        db.session.add(payment)
        db.session.commit()
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        flash('Payment processing failed. Please try again.', 'error')
        return redirect(url_for('main.meal_booking'))

@payment_bp.route('/create-subscription', methods=['POST'])
@login_required
def create_subscription():
    plan_type = request.form.get('plan_type')
    
    # Get price ID based on plan type
    price_id = get_subscription_price_id(plan_type)
    
    try:
        # Create Stripe Checkout Session for subscription
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payment.subscription_success', _external=True),
            cancel_url=url_for('payment.subscription_cancel', _external=True),
            client_reference_id=str(current_user.id)
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        flash('Subscription creation failed. Please try again.', 'error')
        return redirect(url_for('main.meal_booking'))

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400
    
    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object
        handle_successful_payment(session)
    elif event.type == 'customer.subscription.deleted':
        subscription = event.data.object
        handle_subscription_cancellation(subscription)
    
    return 'Success', 200

@payment_bp.route('/payment-success/<int:meal_id>')
@login_required
def payment_success(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    meal.payment_status = 'paid'
    meal.status = 'confirmed'
    db.session.commit()
    
    flash('Payment processed successfully!', 'success')
    return redirect(url_for('main.meal_history'))

@payment_bp.route('/payment-cancel/<int:meal_id>')
@login_required
def payment_cancel(meal_id):
    flash('Payment was cancelled.', 'info')
    return redirect(url_for('main.meal_booking'))

@payment_bp.route('/subscription-success')
@login_required
def subscription_success():
    flash('Subscription created successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@payment_bp.route('/subscription-cancel')
@login_required
def subscription_cancel():
    flash('Subscription creation was cancelled.', 'info')
    return redirect(url_for('main.meal_booking'))

def calculate_meal_price(meal_type):
    prices = {
        'breakfast': 8.00,
        'lunch': 12.00,
        'dinner': 15.00
    }
    return prices.get(meal_type, 10.00)

def get_subscription_price_id(plan_type):
    price_ids = {
        'weekly': 'price_weekly_id',  # Replace with actual Stripe price IDs
        'monthly': 'price_monthly_id'
    }
    return price_ids.get(plan_type)

def handle_successful_payment(session):
    payment = Payment.query.filter_by(stripe_payment_id=session.id).first()
    if payment:
        payment.status = 'completed'
        db.session.commit()

def handle_subscription_cancellation(stripe_subscription):
    subscription = Subscription.query.filter_by(
        stripe_subscription_id=stripe_subscription.id
    ).first()
    
    if subscription:
        subscription.status = 'cancelled'
        db.session.commit()

def process_refund(payment):
    try:
        refund = stripe.Refund.create(
            payment_intent=payment.stripe_payment_id
        )
        
        payment.status = 'refunded'
        payment.stripe_refund_id = refund.id
        db.session.commit()
        
        return True
    except stripe.error.StripeError as e:
        return False
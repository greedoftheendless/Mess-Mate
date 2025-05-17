from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Meal, Subscription, Payment, MealPlan
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get active subscription
    active_subscription = Subscription.query.filter(
        and_(
            Subscription.user_id == current_user.id,
            Subscription.status == 'active',
            Subscription.end_date > datetime.utcnow()
        )
    ).first()
    
    # Get upcoming meals
    upcoming_meals = Meal.query.filter(
        and_(
            Meal.user_id == current_user.id,
            Meal.meal_date > datetime.utcnow(),
            Meal.status != 'cancelled'
        )
    ).order_by(Meal.meal_date).limit(5).all()
    
    # Get recent payments for the current user
    recent_payments = Payment.query.filter_by(user_id=current_user.id)\
        .order_by(Payment.created_at.desc())\
        .limit(5)\
        .all()
    
    return render_template('main/dashboard.html', 
                           subscription=active_subscription,
                           upcoming_meals=upcoming_meals,
                           recent_payments=recent_payments)

@main_bp.route('/meal-booking', methods=['GET', 'POST'])
@login_required
def meal_booking():
    if request.method == 'POST':
        booking_type = request.form.get('booking_type')
        
        if booking_type == 'subscription':
            return handle_subscription_booking()
        else:
            return handle_one_time_booking()
    
    meal_plans = MealPlan.query.filter_by(is_active=True).all()
    return render_template('main/meal_booking.html', meal_plans=meal_plans)

@main_bp.route('/meal-history')
@login_required
def meal_history():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = Meal.query.filter_by(user_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if date_from:
        query = query.filter(Meal.meal_date >= datetime.strptime(date_from, '%Y-%m-%d'))
    
    if date_to:
        query = query.filter(Meal.meal_date <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    meals = query.order_by(Meal.meal_date.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('main/meal_history.html', meals=meals, now=datetime.utcnow())

@main_bp.route('/cancel-meal/<int:meal_id>', methods=['POST'])
@login_required
def cancel_meal(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    
    if meal.user_id != current_user.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('main.meal_history'))
    
    if meal.status == 'cancelled':
        flash('Meal already cancelled', 'warning')
        return redirect(url_for('main.meal_history'))
    
    if meal.meal_date < datetime.utcnow():
        flash('Cannot cancel past meals', 'error')
        return redirect(url_for('main.meal_history'))
    
    meal.status = 'cancelled'
    db.session.commit()
    
    # Initiate refund if applicable
    if meal.payment_status == 'paid' and not meal.subscription_id:
        initiate_refund(meal)
    
    flash('Meal cancelled successfully', 'success')
    return redirect(url_for('main.meal_history'))

def handle_subscription_booking():
    plan_id = request.form.get('plan_type')
    meal_preferences = request.form.get('meal_preferences')
    
    if not plan_id:
        flash('Please select a meal plan', 'error')
        return redirect(url_for('main.meal_booking'))
    
    # Map plan ID to plan type
    plan_type = 'monthly' if plan_id == '1' else 'weekly'
    
    # Check for existing active subscription
    existing_subscription = Subscription.query.filter(
        and_(
            Subscription.user_id == current_user.id,
            Subscription.status == 'active',
            Subscription.end_date > datetime.utcnow()
        )
    ).first()
    
    if existing_subscription:
        flash('You already have an active subscription', 'warning')
        return redirect(url_for('main.meal_booking'))
    
    # Create new subscription
    duration = 30 if plan_type == 'monthly' else 7
    new_subscription = Subscription(
        user_id=current_user.id,
        plan_type=plan_type,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=duration),
        status='active'
    )
    
    db.session.add(new_subscription)
    db.session.commit()
    
    # Create meal entries for the subscription period
    create_subscription_meals(new_subscription, meal_preferences)
    
    flash('Subscription created successfully', 'success')
    return redirect(url_for('main.dashboard'))

def handle_one_time_booking():
    meal_date = datetime.strptime(request.form.get('meal_date'), '%Y-%m-%d')
    meal_type = request.form.get('meal_type')
    meal_preferences = request.form.get('meal_preferences')
    
    # Check if meal already booked for the same date and type
    existing_meal = Meal.query.filter(
        and_(
            Meal.user_id == current_user.id,
            Meal.meal_date == meal_date,
            Meal.meal_type == meal_type,
            Meal.status != 'cancelled'
        )
    ).first()
    
    if existing_meal:
        flash('You already have a meal booked for this date and time', 'warning')
        return redirect(url_for('main.meal_booking'))
    
    new_meal = Meal(
        user_id=current_user.id,
        meal_type=meal_type,
        meal_date=meal_date,
        dietary_preferences=meal_preferences,
        status='pending',
        payment_status='unpaid'
    )
    
    db.session.add(new_meal)
    db.session.commit()
    
    # Redirect to payment
    return redirect(url_for('payment.process_payment', meal_id=new_meal.id))

def create_subscription_meals(subscription, meal_preferences):
    current_date = subscription.start_date
    
    meal_times = {
        'breakfast': 8,  # 8:00 AM
        'lunch': 12,     # 12:00 PM
        'dinner': 18     # 6:00 PM
    }
    
    while current_date <= subscription.end_date:
        for meal_type, hour in meal_times.items():
            meal_datetime = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            meal = Meal(
                user_id=current_user.id,
                meal_type=meal_type,
                meal_date=meal_datetime,
                dietary_preferences=meal_preferences,
                status='confirmed',
                payment_status='paid',
                subscription_id=subscription.id
            )
            db.session.add(meal)
        current_date += timedelta(days=1)
    
    db.session.commit()

def initiate_refund(meal):
    # Find the payment associated with the meal
    payment = Payment.query.filter_by(
        user_id=meal.user_id,
        status='completed'
    ).first()
    
    if payment:
        from routes.payment import process_refund
        process_refund(payment)

@main_bp.route('/contact')
@login_required
def feedback():
    return render_template('main/contact.html')


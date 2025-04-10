from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Meal, Subscription, Payment, MealPlan, RefundRequest
from routes.auth import admin_required
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get summary statistics
    total_users = User.query.count()
    active_subscriptions = Subscription.query.filter_by(status='active').count()
    total_meals_today = Meal.query.filter(
        func.date(Meal.meal_date) == func.date(datetime.utcnow())
    ).count()
    pending_refunds = RefundRequest.query.filter_by(status='pending').count()
    
    # Get recent activities
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_subscriptions=active_subscriptions,
                           total_meals_today=total_meals_today,
                           pending_refunds=pending_refunds,
                           recent_users=recent_users,
                           recent_payments=recent_payments)

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.is_active = 'is_active' in request.form
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/admin/meal-plans', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_meal_plans():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        duration = int(request.form.get('duration'))
        meals_included = int(request.form.get('meals_included'))
        
        meal_plan = MealPlan(
            name=name,
            description=description,
            price=price,
            duration=duration,
            meals_included=meals_included
        )
        
        db.session.add(meal_plan)
        db.session.commit()
        
        flash('Meal plan created successfully', 'success')
        return redirect(url_for('admin.manage_meal_plans'))
    
    meal_plans = MealPlan.query.all()
    return render_template('admin/meal_plans.html', meal_plans=meal_plans)

@admin_bp.route('/admin/refunds')
@login_required
@admin_required
def manage_refunds():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = RefundRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    refund_requests = query.order_by(RefundRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('admin/refunds.html', refund_requests=refund_requests)

@admin_bp.route('/admin/refund/<int:request_id>', methods=['POST'])
@login_required
@admin_required
def process_refund(request_id):
    refund_request = RefundRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    
    if action == 'approve':
        # Process refund through Stripe
        from routes.payment import process_refund
        if process_refund(refund_request.payment):
            refund_request.status = 'approved'
            refund_request.processed_at = datetime.utcnow()
            refund_request.processed_by = current_user.id
            db.session.commit()
            flash('Refund approved and processed', 'success')
        else:
            flash('Refund processing failed', 'error')
    elif action == 'reject':
        refund_request.status = 'rejected'
        refund_request.processed_at = datetime.utcnow()
        refund_request.processed_by = current_user.id
        db.session.commit()
        flash('Refund request rejected', 'info')
    
    return redirect(url_for('admin.manage_refunds'))

@admin_bp.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Daily meal counts
    daily_meals = db.session.query(
        func.date(Meal.meal_date),
        func.count(Meal.id)
    ).filter(
        Meal.meal_date.between(start_date, end_date)
    ).group_by(
        func.date(Meal.meal_date)
    ).all()
    
    # Revenue statistics
    total_revenue = db.session.query(func.sum(Payment.amount)).\
        filter(Payment.status == 'completed').scalar() or 0
    
    subscription_revenue = db.session.query(func.sum(Payment.amount)).\
        filter(Payment.payment_type == 'subscription',
               Payment.status == 'completed').scalar() or 0
    
    one_time_revenue = total_revenue - subscription_revenue
    
    # Popular meal types
    meal_type_stats = db.session.query(
        Meal.meal_type,
        func.count(Meal.id)
    ).group_by(Meal.meal_type).all()
    
    return render_template('admin/analytics.html',
                           daily_meals=daily_meals,
                           total_revenue=total_revenue,
                           subscription_revenue=subscription_revenue,
                           one_time_revenue=one_time_revenue,
                           meal_type_stats=meal_type_stats)

@admin_bp.route('/admin/export-data')
@login_required
@admin_required
def export_data():
    data_type = request.args.get('type')
    
    if data_type == 'users':
        users = User.query.all()
        data = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        } for user in users]
    elif data_type == 'meals':
        meals = Meal.query.all()
        data = [{
            'id': meal.id,
            'user_id': meal.user_id,
            'meal_type': meal.meal_type,
            'meal_date': meal.meal_date.isoformat(),
            'status': meal.status
        } for meal in meals]
    else:
        return jsonify({'error': 'Invalid data type'}), 400
    
    return jsonify(data)
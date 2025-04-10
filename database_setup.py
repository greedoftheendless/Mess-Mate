from app import app, db
from models import User, Meal, Subscription, Payment, MealPlan, RefundRequest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                email_verified=True,
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Create sample meal plans
            meal_plans = [
                MealPlan(
                    name='Weekly Basic',
                    description='3 meals per day for 7 days',
                    price=89.99,
                    duration=7,
                    meals_included=21
                ),
                MealPlan(
                    name='Monthly Premium',
                    description='3 meals per day for 30 days',
                    price=299.99,
                    duration=30,
                    meals_included=90
                ),
                MealPlan(
                    name='Weekly Vegetarian',
                    description='3 vegetarian meals per day for 7 days',
                    price=99.99,
                    duration=7,
                    meals_included=21
                )
            ]
            
            for plan in meal_plans:
                db.session.add(plan)
            
            # Create sample user
            user = User(
                username='student',
                email='student@example.com',
                role='student',
                email_verified=True,
                is_active=True
            )
            user.set_password('student123')
            db.session.add(user)
            
            # Create sample subscription
            subscription = Subscription(
                user_id=2,  # Will be the student's ID
                plan_type='weekly',
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=7),
                status='active'
            )
            db.session.add(subscription)
            
            # Create sample meals
            meal_types = ['breakfast', 'lunch', 'dinner']
            for i in range(7):
                date = datetime.utcnow() + timedelta(days=i)
                for meal_type in meal_types:
                    meal = Meal(
                        user_id=2,
                        meal_type=meal_type,
                        meal_date=date,
                        status='confirmed',
                        payment_status='paid',
                        subscription_id=1,
                        dietary_preferences='None'
                    )
                    db.session.add(meal)
            
            # Create sample payment
            payment = Payment(
                user_id=2,
                amount=89.99,
                payment_type='subscription',
                status='completed',
                stripe_payment_id='sample_payment_id'
            )
            db.session.add(payment)
            
            db.session.commit()
            print('Database initialized with sample data!')
        else:
            print('Database already contains data.')

if __name__ == '__main__':
    init_db()
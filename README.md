# Mess Management System (MMS)

A comprehensive web-based dining management system designed for institutions to efficiently manage meal bookings, payments, and administration.

## 🚀 Features

### Authentication
- User registration with email verification
- Secure login/logout functionality with password hashing
- Role-based access control (Student/Admin)
- Robust session management

### User Dashboard
- Display of active subscription status
- Upcoming meal schedule overview
- Recent payment history
- Profile settings & preferences management
- Real-time booking status updates

### Meal Management
- Flexible subscription plans (Weekly/Monthly)
- One-time meal booking options
- Meal type selection (Breakfast/Lunch/Dinner)
- Customizable dietary preferences
- Easy meal cancellation with refund support

### Payment System
- Secure payment processing
- Support for one-time & subscription payments
- Detailed payment history
- Automated refund processing
- Real-time payment status tracking

## 🛠️ Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML5, CSS, JavaScript
- **Authentication**: Flask-Login
- **ORM**: SQLAlchemy
- **UI**: Modern responsive design

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone [repository-url]
   cd mms
   ```

2. Create and activate virtual environment
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix/MacOS
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database
```bash
python database_setup.py
```

6. Run the application
```bash
python app.py
```

## 🔒 Security Features

- Password hashing
- CSRF protection
- XSS prevention
- SQL injection protection
- Secure session handling

## 📱 Key Components

### Routes
- **auth.py**: Authentication and user management
- **main.py**: Core meal booking and dashboard functionality
- **payment.py**: Payment processing and refund handling
- **admin.py**: Administrative functions

### Models
- User management
- Meal booking system
- Subscription handling
- Payment processing

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Future Enhancements

- Mobile application
- Advanced analytics
- Kitchen inventory management
- Nutritional information tracking

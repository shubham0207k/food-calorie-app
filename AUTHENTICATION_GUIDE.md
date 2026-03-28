# Role-Based Authentication System Documentation

## Overview

This is a complete role-based authentication system for the Food Calorie Predictor web app with **Admin** and **User** roles. The system includes frontend route protection, localStorage-based role management, and separate dashboards for each role.

---

## 🔐 Features

### Authentication

- ✅ Secure login and signup with password hashing
- ✅ Role assignment (Admin/User)
- ✅ Session-based backend authentication
- ✅ localStorage-based role storage on frontend
- ✅ Automatic redirects based on user role

### User Dashboard

- 🔍 Search food calories in database
- 📸 Upload food images for AI-powered prediction
- ✍️ Manually enter food details
- 📋 View food history
- 🔒 Frontend and backend route protection

### Admin Dashboard

- 👥 View and manage all users
- 🗑️ Delete users (except yourself)
- 🍽️ Add new food items to database
- 📊 View system statistics
- 🛡️ Admin-only access control

### Security Features

- 🔐 Protected routes (admin-only, user-only, login-required)
- ⚠️ "Access Denied" page for unauthorized access
- 🔒 Role validation on both frontend (localStorage) and backend (session)
- 🛡️ Admin decorator for backend route protection

---

## 🚀 Use Cases

### User Workflow

1. **Sign up** as regular user
2. **Login** to access user dashboard
3. **Search** for food nutrition info
4. **Upload image** for AI calorie prediction
5. **Manually enter** food details
6. **View history** of logged foods

### Admin Workflow

1. **Sign up** with admin email (`admin@example.com`)
2. **Login** to access admin dashboard
3. **Manage users**: View, delete user accounts
4. **Manage foods**: Add/delete food items from database
5. **View statistics**: Monitor system metrics

---

## 🔧 Technical Architecture

### Frontend Flow

```
Login Page (login.html)
    ↓ (user enters credentials)
    ↓ (POST to /login)
    ↓ (receives role, stores in localStorage)
    ↓
IF role == "admin" → Admin Dashboard (admin-dashboard.html)
IF role == "user" → User Dashboard (user-dashboard.html)
```

### Backend Flow

```
/login endpoint
    ↓ (verify email/password)
    ↓ (set session variables)
    ↓ (return JSON with role, user_id, username)
    ↓ (frontend receives response)
    ↓ (stores in localStorage)
```

### Route Protection

**Frontend Protection** (JavaScript)

```javascript
// In auth-guard.js
auth.requireAuth(); // Redirect to login if not authenticated
auth.requireAdmin(); // Show "Access Denied" if not admin
auth.requireUser(); // Redirect if not regular user
```

**Backend Protection** (Python)

```python
@admin_required      # Decorator to protect admin routes
def admin_function():
    # Only accessible to admins
    pass
```

---

## 📁 File Structure

### Templates

```
templates/
├── login.html                    # Login page with localStorage setup
├── signup.html                   # Registration page
├── user-dashboard.html          # User dashboard (comprehensive)
├── admin-dashboard.html         # Admin dashboard (comprehensive)
├── admin.html                   # Old admin page (deprecated)
├── admin-users.html             # Deprecated
├── admin-foods.html             # Deprecated
└── calorie_page.html            # Deprecated
```

### Static Files

```
static/
├── style.css                    # All CSS styles
├── auth-guard.js               # Frontend authentication guard
```

### Backend

```
main.py
├── Login/Signup Routes
│   ├── @app.route('/login')
│   ├── @app.route('/signup')
│   └── @app.route('/logout')
├── Admin Routes
│   ├── @app.route('/admin-dashboard')
│   ├── @app.route('/admin/stats')
│   ├── @app.route('/admin/users')
│   ├── @app.route('/admin/get_foods')
│   ├── @app.route('/admin/delete_user/<id>')
│   ├── @app.route('/admin/add_food')
│   └── @app.route('/admin/delete_food/<id>')
├── User Routes
│   ├── @app.route('/user-dashboard')
│   ├── @app.route('/predict')
│   └── @app.route('/manual')
```

---

## 🔑 Key Components

### AuthGuard Class (auth-guard.js)

Manages frontend authentication state:

```javascript
const auth = new AuthGuard();

// Check authentication
auth.isAuthenticated(); // true/false
auth.isAdmin(); // true/false
auth.isUser(); // true/false

// Protect routes
auth.requireAuth(); // Requires login
auth.requireAdmin(); // Requires admin role
auth.requireUser(); // Requires user role

// Manage auth state
auth.setAuth(role, userId, username);
auth.logout();
auth.getUserInfo();
```

### Admin Decorator (backend)

```python
@admin_required
def admin_function():
    # Checks session['role'] == 'admin'
    # Redirects to login if not admin
    pass
```

---

## 🧪 Testing

### Create Test Admin Account

1. Go to **Signup** page
2. Enter credentials with email: `admin@example.com`
3. Rest of details can be anything
4. Click **Create Account**
5. Login with these credentials
6. You'll be redirected to Admin Dashboard

### Create Test User Account

1. Go to **Signup** page
2. Enter credentials with ANY email (except `admin@example.com`)
3. Click **Create Account**
4. Login with these credentials
5. You'll be redirected to User Dashboard

### Test Route Protection

**Try accessing admin routes as user:**

- Go to `/admin-dashboard`
- You'll see "Access Denied" page

**Try accessing without login:**

- Clear localStorage
- Try accessing `/user-dashboard`
- You'll be redirected to login

### Test Data

Users are stored in: `data/users.json`
Foods are stored in: `data/foods.json`

---

## 🔄 Authentication Flow Diagram

```
START
  ↓
User Opens App
  ↓
Check localStorage for 'isLoggedIn'
  ↓
IF isLoggedIn == true →  Check role
                         ├→ admin  → Admin Dashboard
                         └→ user   → User Dashboard
  ↓
IF isLoggedIn == false → Login Page
  ↓
User enters credentials
  ↓
POST to /login
  ↓
Backend verifies & sets session
  ↓
Returns JSON: {role, user_id, username}
  ↓
Frontend stores in localStorage
  ↓
Redirect to appropriate dashboard
  ↓
Dashboard checks localStorage & auth-guard
  ↓
Page loads if authorized
```

---

## 🛡️ Security Best Practices

1. **Passwords**: Hashed using `werkzeug.security.generate_password_hash`
2. **Session**: Server-side session validation on every protected route
3. **Frontend**: localStorage used for UX (role display, redirects)
4. **Backend**: Session used for actual authorization
5. **Route Protection**: Dual protection (frontend + backend)
6. **Logout**: Clears both session and localStorage

### Important Notes

- ⚠️ localStorage can be cleared by user → always verify session on backend
- ⚠️ Production: Use environment variables for `SECRET_KEY`
- ⚠️ Production: Use HTTPS only
- ⚠️ Production: Set `secure=True` in cookies
- ⚠️ Never store sensitive data in localStorage

---

## 🎨 UI Components

### Admin Dashboard Features

- **Overview Tab**: System statistics and health checks
- **User Management Tab**:
  - Table of all users
  - Search/filter users
  - Delete user functionality
- **Food Management Tab**:
  - Add new food items
  - Search/filter foods
  - Delete food items

### User Dashboard Features

- **Search Tab**: Search food calories
- **Upload Tab**: Upload image for AI prediction
- **Manual Entry Tab**: Manually log food details
- **History Tab**: View all logged foods

---

## 🚀 Deployment Checklist

### Before Deployment

- [ ] Change `SECRET_KEY` to random value
- [ ] Set `DEBUG = False`
- [ ] Configure CORS carefully
- [ ] Use HTTPS CDN for static files
- [ ] Set up environment variables
- [ ] Backup user/food JSON databases

### Environment Variables

```
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DATABASE_PATH=/secure/path/to/data/
API_KEY=your-usda-api-key
```

---

## 📝 API Reference

### Authentication Endpoints

**POST /login**

```json
Request:
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "role": "user",
  "user_id": 1,
  "username": "johndoe",
  "redirect": "/user-dashboard"
}
```

**POST /signup**

```json
Request:
{
  "username": "johndoe",
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "success": true,
  "message": "Account created successfully! Please login.",
  "redirect": "/login"
}
```

**GET /logout**

- Clears session
- Redirects to login

### Admin API Endpoints

**GET /admin/stats** (Admin only)

```json
Response:
{
  "totalUsers": 10,
  "totalFoods": 50,
  "adminUsers": 2,
  "regularUsers": 8
}
```

**GET /admin/users** (Admin only)

```json
Response:
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  ]
}
```

**GET /admin/get_foods** (Admin only)

```json
Response:
{
  "foods": [
    {
      "id": 1,
      "name": "Apple",
      "calories": 95,
      "serving": "1 medium"
    }
  ]
}
```

**POST /admin/add_food** (Admin only)

```json
Request:
{
  "name": "Apple",
  "calories": 95,
  "protein": 0.5,
  "carbs": 25,
  "fat": 0.3,
  "serving": "1 medium"
}
```

**POST /admin/delete_user/<id>** (Admin only)

- Deletes user by ID
- Cannot delete yourself

**POST /admin/delete_food/<id>** (Admin only)

- Deletes food item by ID

---

## 🐛 Troubleshooting

### Issue: Role not updating after login

**Solution**: Check localStorage in browser DevTools. Ensure login response includes role.

### Issue: Admin routes redirect to login

**Solution**: Check that session['role'] is set correctly on backend and matches ['admin'].

### Issue: localStorage is empty

**Solution**: Normal - clear it manually with DevTools. Session persists on backend regardless.

### Issue: "Access Denied" page shows

**Solution**: You don't have the required role. Use different account or check role assignment.

### Issue: Users.json or foods.json missing

**Solution**: Backend creates empty files automatically on startup. Check `/data/` folder.

---

## 📚 Additional Resources

- **Flask Security**: https://flask.palletsprojects.com/
- **werkzeug**: https://werkzeug.palletsprojects.com/
- **JavaScript localStorage**: https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage

---

## 📝 License

This role-based authentication system is part of the Food Calorie Predictor project.

---

## 👨‍💻 Support

For issues or questions, contact the development team.

Last Updated: March 27, 2026

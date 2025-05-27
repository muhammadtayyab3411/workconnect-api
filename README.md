# WorkConnect API (Django Backend)

This is the Django REST API backend for the WorkConnect platform.

## Features

- Custom User model with role-based authentication (Client, Worker, Admin)
- JWT token authentication
- User registration and login
- Social authentication (Google, Facebook)
- CORS enabled for frontend integration
- Django Admin interface
- PostgreSQL database

## Setup

### Prerequisites

- Python 3.9+
- pipenv
- PostgreSQL 12+ (installed and running)

### Database Setup

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # macOS with Homebrew
   brew install postgresql
   brew services start postgresql
   
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create database and user**:
   ```bash
   # Connect to PostgreSQL
   psql postgres
   
   # Create database
   CREATE DATABASE workconnect;
   
   # Create user (optional - you can use default postgres user)
   CREATE USER workconnect_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE workconnect TO workconnect_user;
   
   # Exit
   \q
   ```

### Installation

1. Navigate to the backend directory:
   ```bash
   cd workconnect-api
   ```

2. Install dependencies:
   ```bash
   pipenv install
   ```

3. **Configure Database** (Choose one option):

   **Option A: Environment Variables (Recommended)**
   ```bash
   # Copy the sample environment file
   cp env_sample.txt .env
   
   # Edit .env file with your database credentials:
   # DB_PASSWORD=your_actual_password
   ```

   **Option B: Direct Configuration**
   
   Edit `workconnect/settings.py` and update the DATABASES section:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'workconnect',
           'USER': 'postgres',  # your database username
           'PASSWORD': 'your_password',  # your database password
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

4. Activate the virtual environment:
   ```bash
   pipenv shell
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8001`

## Database Configuration

The database credentials can be configured in the following ways:

### Environment Variables (Recommended)
- `DB_NAME` - Database name (default: workconnect)
- `DB_USER` - Database username (default: postgres)
- `DB_PASSWORD` - Database password (default: postgres)
- `DB_HOST` - Database host (default: localhost)
- `DB_PORT` - Database port (default: 5432)

### Direct in settings.py
You can also directly edit the `DATABASES` configuration in `workconnect/settings.py`.

## API Endpoints

### Authentication
- `POST /auth/register/` - User registration
- `POST /auth/login/` - User login
- `POST /auth/refresh/` - Refresh JWT token
- `POST /auth/social-login/` - Social authentication
- `GET/PUT /auth/profile/` - User profile

### Health Check
- `GET /api/health/` - API health check

### Admin
- `/admin/` - Django admin interface

## Environment Variables

For production, set the following environment variables:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Set to False in production
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - Database configuration
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `FACEBOOK_CLIENT_ID` - Facebook OAuth client ID
- `FACEBOOK_CLIENT_SECRET` - Facebook OAuth client secret

## User Roles

- **Client**: Can post jobs and hire workers
- **Worker**: Can apply for jobs and provide services
- **Admin**: Full system access

## Development

The project uses:
- Django 4.2+
- Django REST Framework
- PostgreSQL
- JWT Authentication
- Django Allauth for social authentication
- CORS headers for frontend integration

## Troubleshooting

### Database Connection Issues
1. Ensure PostgreSQL is running: `brew services list | grep postgresql` (macOS) or `sudo systemctl status postgresql` (Linux)
2. Check if database exists: `psql -U postgres -l`
3. Verify database credentials in your .env file or settings.py
4. Make sure the database user has proper permissions
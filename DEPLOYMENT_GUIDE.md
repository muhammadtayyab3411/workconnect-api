# WorkConnect API Deployment Guide

This guide covers deploying the WorkConnect API backend using Docker on various platforms, with a focus on Render.

## 🐳 Docker Setup

### Local Development with Docker

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   - API: http://localhost:8001
   - Health Check: http://localhost:8001/api/health/
   - Database: localhost:5432

3. **Run migrations (if needed):**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

### Production Docker Build

1. **Build production image:**
   ```bash
   docker build -f Dockerfile.render -t workconnect-api .
   ```

2. **Run production container:**
   ```bash
   docker run -p 8001:8001 --env-file .env workconnect-api
   ```

## 🚀 Render Deployment

### Option 1: Using render.yaml (Recommended)

1. **Push your code to GitHub**

2. **Connect to Render:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file

3. **Configure Environment Variables:**
   Update the values in `render.yaml` or set them in Render dashboard:
   ```yaml
   - key: GOOGLE_CLIENT_ID
     value: your-actual-google-client-id
   - key: GOOGLE_CLIENT_SECRET
     value: your-actual-google-client-secret
   # ... etc
   ```

### Option 2: Manual Setup

1. **Create a new Web Service:**
   - Environment: Docker
   - Build Command: (leave empty)
   - Start Command: `./start.sh`
   - Dockerfile Path: `./Dockerfile.render`

2. **Create PostgreSQL Database:**
   - Go to "New" → "PostgreSQL"
   - Name: `workconnect-db`
   - Plan: Starter (or higher)

3. **Set Environment Variables:**
   ```
   DJANGO_SETTINGS_MODULE=workconnect.settings
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.onrender.com,localhost
   SECRET_KEY=your-secret-key
   DB_NAME=workconnect
   DB_USER=your-db-user
   DB_PASSWORD=your-db-password
   DB_HOST=your-db-host
   DB_PORT=5432
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key
   STRIPE_SECRET_KEY=your-stripe-secret-key
   GEMINI_API_KEY=your-gemini-api-key
   EMAIL_HOST_USER=your-email
   EMAIL_HOST_PASSWORD=your-email-password
   FRONTEND_URL=https://your-frontend-domain.com
   ```

## 🔧 Environment Variables

### Required Variables
- `SECRET_KEY`: Django secret key (auto-generated on Render)
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Database configuration

### Optional Variables
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: For Google OAuth
- `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`: For payments
- `GEMINI_API_KEY`: For AI features
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: For email functionality
- `FRONTEND_URL`: Your frontend application URL

## 🗄️ Database Setup

### Render PostgreSQL
1. Create a PostgreSQL database on Render
2. Note the connection details
3. The database will be automatically connected if using `render.yaml`

### Manual Migration
If you need to run migrations manually:
```bash
# On Render, use the shell
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🔍 Health Checks

The application includes a health check endpoint at `/api/health/` that returns:
```json
{
  "status": "healthy",
  "message": "WorkConnect API is running"
}
```

## 📝 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Environment variables configured
- [ ] Database created and connected
- [ ] Health check endpoint working
- [ ] Static files collected
- [ ] Migrations applied
- [ ] CORS settings configured for frontend
- [ ] SSL/HTTPS enabled (automatic on Render)

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors:**
   - Verify database credentials
   - Check if database is running
   - Ensure network connectivity

2. **Static Files Not Loading:**
   - Run `python manage.py collectstatic`
   - Check `STATIC_URL` and `STATIC_ROOT` settings

3. **CORS Issues:**
   - Update `CORS_ALLOWED_ORIGINS` in settings
   - Verify frontend URL is correct

4. **Environment Variables:**
   - Check all required variables are set
   - Verify variable names match exactly

### Logs
- On Render: Check the "Logs" tab in your service dashboard
- Locally: `docker-compose logs web`

## 🔄 Updates and Redeployment

1. **Push changes to GitHub**
2. **Render auto-deploys** from the main branch
3. **Manual redeploy:** Use the "Manual Deploy" button on Render

## 📊 Monitoring

- **Health Check:** Monitor `/api/health/` endpoint
- **Render Metrics:** Available in the Render dashboard
- **Database Metrics:** Available in the PostgreSQL dashboard

## 🔐 Security Notes

- Never commit sensitive environment variables
- Use strong, unique passwords
- Enable 2FA on all service accounts
- Regularly update dependencies
- Monitor for security vulnerabilities

## 📞 Support

If you encounter issues:
1. Check the logs first
2. Verify environment variables
3. Test locally with Docker
4. Check Render status page
5. Contact support if needed 
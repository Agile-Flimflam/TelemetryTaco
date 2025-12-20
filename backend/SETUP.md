# Backend Setup Instructions

## Quick Start

1. **Configure Poetry to use Python 3.11 (required if you have Python 3.14+):**

   ```bash
   cd backend
   poetry env use python3.11
   # Or specify the full path if needed:
   # poetry env use /opt/homebrew/bin/python3.11
   ```

2. **Install dependencies with Poetry:**

   ```bash
   poetry install
   ```

3. **If Poetry fails to connect to PyPI:**

   - Check your internet connection
   - Try using a different network
   - Check if you're behind a corporate firewall/proxy
   - Verify Poetry can access PyPI: `poetry config repositories.pypi https://pypi.org/simple/`

4. **Set up environment variables:**

   First, generate a secure SECRET_KEY:

   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

   Copy the generated key, then create a `.env` file in the `backend/` directory:

   ```bash
   # Create .env file (replace YOUR_SECRET_KEY with the generated key)
   cat > backend/.env << 'EOF'
   DEBUG=True
   SECRET_KEY=YOUR_SECRET_KEY
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
   REDIS_URL=redis://localhost:6379/0
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   EOF
   ```

   Or manually create `backend/.env` with (replace `YOUR_SECRET_KEY` with the generated key):

   ```
   DEBUG=True
   SECRET_KEY=YOUR_SECRET_KEY
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
   REDIS_URL=redis://localhost:6379/0
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   ```

   **Important:** The SECRET_KEY must be a secure, randomly generated value. The application will fail to start if you use example or insecure values.

5. **Start the database (if using Docker):**

   ```bash
   # From project root directory
   cd ..
   docker-compose up -d db

   # Wait a few seconds for PostgreSQL to be ready
   # Verify it's running:
   docker-compose ps db
   ```

   **OR if using a local PostgreSQL installation:**

   Make sure your local PostgreSQL is running and update the `.env` file with your actual credentials.

6. **Run database migrations:**

   ```bash
   cd backend
   poetry run python manage.py migrate
   ```

7. **Start the development server:**
   ```bash
   poetry run python manage.py runserver
   ```

## Alternative: Using pip (if Poetry fails)

If Poetry continues to have issues, you can use pip with the `requirements.txt` file:

```bash
# Create a virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Note: You may need to update requirements.txt to match pyproject.toml dependencies
```

## Troubleshooting

### Python Version Issues

If you see errors about Python 3.14 or unsupported versions:

- Ensure you have Python 3.11 or 3.12 installed
- Check your Python version: `python3 --version`
- Set Poetry to use a specific Python version: `poetry env use python3.11`

### Network/Connection Issues

If Poetry can't connect to PyPI:

- Check your internet connection
- Try: `poetry install --no-cache`
- Verify DNS resolution: `ping pypi.org`
- Check for proxy settings: `poetry config http-basic.pypi <username> <password>` (if behind proxy)

### Database Connection Issues

If you see "password authentication failed" errors:

#### Quick Diagnostic

Run this to check your database connection:

```bash
cd backend
poetry run python check_db.py
```

#### Solution 1: Use Docker PostgreSQL (Recommended)

1. **Stop any local PostgreSQL** (if running):

   ```bash
   # On macOS with Homebrew:
   brew services stop postgresql@14  # or postgresql@15, etc.

   # Or check what's running:
   ps aux | grep postgres
   ```

2. **Start Docker PostgreSQL:**

   ```bash
   # From project root
   cd ..
   docker-compose up -d db

   # Wait 5-10 seconds, then verify:
   docker-compose ps db  # Should show "Up" and "healthy"
   ```

3. **Test the connection:**

   ```bash
   cd backend
   poetry run python check_db.py
   ```

4. **Run migrations:**
   ```bash
   poetry run python manage.py migrate
   ```

#### Solution 2: Use Local PostgreSQL

If you prefer to use a local PostgreSQL installation:

1. **Generate a secure SECRET_KEY:**

   ```bash
   cd backend
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

   Copy the generated key.

2. **Create/update `.env` file** with your actual credentials:

   ```bash
   cat > .env << 'EOF'
   DEBUG=True
   SECRET_KEY=YOUR_SECRET_KEY
   DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/telemetry_taco
   REDIS_URL=redis://localhost:6379/0
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   EOF
   ```

   Replace `YOUR_SECRET_KEY` with the generated key, and `YOUR_USER` and `YOUR_PASSWORD` with your actual PostgreSQL credentials.

3. **Create the database** (if it doesn't exist):

   ```bash
   createdb telemetry_taco
   # Or using psql:
   psql -U postgres -c "CREATE DATABASE telemetry_taco;"
   ```

4. **Test the connection:**

   ```bash
   poetry run python check_db.py
   ```

5. **Run migrations:**
   ```bash
   poetry run python manage.py migrate
   ```

#### Common Issues

- **Port 5432 already in use**: Another PostgreSQL instance is running. Stop it or use a different port.
- **Docker container not starting**: Check Docker is running: `docker ps`
- **Wrong password**: Verify credentials match what's in your `.env` file or Docker Compose config.

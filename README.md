# Hawkman Auth API

<img width="1309" height="605" alt="image" src="https://github.com/user-attachments/assets/642fa0fe-82bf-4aee-b855-1a2bce3bd2b3" />

## 1. System Overview

The Hawkman Auth API is the dedicated identity and access management Service for the Learning Management System (LMS). Designed for high performance and strict security, this service handles user onboarding, session management, and credential exchange utilizing a Two step verification flow.

## 2. Architecture & Tech Stack

This service is built on a modern, asynchronous Python stack emphasizing strict type-hinting and data validation.

- **Application Framework:** FastAPI (Python 3.x)
- **Data Validation & Serialization:** Pydantic V2 (Enforcing strict request/response schema contracts)
- **Database Engine:** Supabase (PostgreSQL)
- **ORM:** SQLAlchemy
- **Security & Hashing:** Passlib (Bcrypt) / python-jose (JWT)
- **Environment Management:** `python-dotenv`
- **Hosting / Deployment:** Render (Currently free-tier, architected for horizontal scaling)

## 3. Project Structure

The codebase follows a strict separation of concerns, isolating routing, business logic, database transactions, and data validation.

```
  ├── main.py           # Application entry point, CORS setup, and API router inclusions
  ├── database.py       # Supabase/PostgreSQL connection engine and session factory
  ├── models.py         # SQLAlchemy ORM models (Database schema definitions)
  ├── schemas.py        # Pydantic models (Strict payload validation for auth flows)
  ├── security.py       # Cryptography: Password hashing, JWT generation, and token decoding
  ├── dependencies.py   # FastAPI dependency injections (DB sessions, get_current_user logic)
  ├── utils.py          # Helper functions (OTP generation, email/SMS dispatch formatting)
  └── requirements.txt  # Core dependencies
```

#### Refer to the `requirements.txt` for all dependencies.

## Security & Authentication Model

### 4.1. OTP Verification Flow

To prevent spam accounts and ensure high-friction identity verification during onboarding, the API utilizes a two-step registration flow:

This is acheived using an external service (resend)

### 4.2. Token Lifecycle & Authorization

Access Tokens: Short-lived JSON Web Tokens (JWTs) used for authenticating downstream LMS microservice requests.

Protected Routes: Endpoints requiring authorization utilize the get_current_user dependency to validate the Bearer token in the Authorization header before execution.

# 5. API Endpoints

- All routes are prefixed with /api/auth.

#### Public Routes

`GET / : Health Check - Verifies service uptime and database connectivity.`

#### POST /register :

`Initialize Onboarding - Accepts user details, creates an inactive profile, and triggers OTP dispatch.`

#### POST /verify-otp :

`Account Activation - Validates the user-provided OTP. Returns standard JWT payloads upon success.`

#### POST /login :

`Credential Exchange - Standard email/password authentication returning Access and Refresh tokens.`

#### Protected Routes (Requires Bearer Token)

`GET /me : Read Profile - Retrieves the profile data of the currently authenticated user.`

#### DELETE /me :

`Deactivate Account - Soft-deletes the authenticated user's records (compliance requirements).`

# 6. Environment Configuration

`The service requires the following environment variables to run. Never commit the .env file to version control.`

#### Database (Supabase)

`DATABASE_URL=postgresql://[user]:[password]@db.[project].supabase.co:5432/postgres`

### Security

```
SECRET_KEY=your_super_secret_jwt_key
ALGORITHM=****
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

# OTP Provider (Resend)

`RESEND_API_KEY = your_api_key_here`

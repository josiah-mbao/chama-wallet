# Chama Wallet API

![CI](https://github.com/josiah-mbao/chama-wallet/actions/workflows/tests.yml/badge.svg)
![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen)

A simple **FastAPI + Docker + PostgreSQL** backend for managing chama (group savings) members and their contributions. 
Built to demonstrate how to design, containerize, and run a real-world financial microservice.

---

## 🚀 Features

* **🔐 JWT Authentication:** Secure user registration and login for API access with role-based permissions (member, treasurer, owner).
* **🧑‍💻 User Management:** Register new API users and retrieve current user details (`/users/me`).
* **🏠 Chama Management:** Create and join chama groups, list user's chama memberships.
* **👥 Member Management:** Add members to chamas (owner only), list chama members.
* **💰 Contribution Tracking:** Record member contributions (treasurer/owner only), with proper authorization.
* **📊 Comprehensive API:** RESTful endpoints with full CRUD operations and data validation.
* **🧪 Tested:** 18 comprehensive tests including unit and integration tests with 100% pass rate.
* 🐳 Fully containerized with Docker Compose
* ⚡ Built with FastAPI + SQLAlchemy + PostgreSQL

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|-------------|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Serialization | Pydantic |
| Containerization | Docker & Docker Compose |

---

## 🗂️ Project Structure

```bash
chama-wallet/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── crud.py              # Database operations
│   ├── database.py          # DB connection setup
│   ├── schemas.py           # Pydantic schemas
│   ├── security.py          # JWT logic and dependencies
│   ├── entrypoint.sh        # API startup script
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── models/              # SQLAlchemy models (NEW DIRECTORY)
│   └── routers/             # Endpoint modules (NEW DIRECTORY)
├── docker-compose.yml
└── README.md

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/josiah-mbao/chama-wallet.git
cd chama-wallet
```

### 2️⃣ Build and Run Services
```bash
docker-compose up --build
```
This will start both:
	•	🐘 PostgreSQL (on port 5432)
	•	⚡ FastAPI backend (on port 8000)

Visit:
👉 http://localhost:8000/docs

### 3️⃣ Run Database Migrations

**Important**: You must run Alembic migrations to create the database tables required by the API.
```bash
docker-compose run --rm api alembic upgrade head
```


### 4️⃣ Test the API (Authenticated Flow)

The core application features are protected by JWT. You must first register and log in to get an access token. Note: Roles are assigned during registration (default: member), but only owners can create chamas and add members, treasurers/owners can add contributions.

```bash
# 1. Register an API User (as owner for demo)
curl -X POST "http://localhost:8000/users/" \
-H "Content-Type: application/json" \
-d '{"email": "owner@test.com", "password": "password123", "role": "owner"}'

# 2. Register another user as member
curl -X POST "http://localhost:8000/users/" \
-H "Content-Type: application/json" \
-d '{"email": "member@test.com", "password": "password123", "role": "member"}'

# 3. Login and get JWT Access Token for owner
ACCESS_TOKEN=$(curl -s -X POST "http://localhost:8000/users/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=owner@test.com&password=password123" | jq -r .access_token)
echo "Access Token: $ACCESS_TOKEN"

# 4. Create a new chama (owner)
curl -X POST "http://localhost:8000/chamas/" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"name": "My Chama", "description": "Group savings"}'

# 5. List your chamas
curl -X GET "http://localhost:8000/chamas/" \
-H "Authorization: Bearer $ACCESS_TOKEN"

# 6. Get details of chama 1
curl -X GET "http://localhost:8000/chamas/1" \
-H "Authorization: Bearer $ACCESS_TOKEN"

# 7. Add a member to chama 1 (owner only)
curl -X POST "http://localhost:8000/chamas/1/members" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"member_email": "member@test.com"}'

# 8. Register a treasurer user
curl -X POST "http://localhost:8000/users/" \
-H "Content-Type: application/json" \
-d '{"email": "treasurer@test.com", "password": "password123", "role": "treasurer"}'

# 9. Add treasurer as member (assigns treasurer role in chama)
curl -X POST "http://localhost:8000/chamas/1/members" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"member_email": "treasurer@test.com"}'

# 10. Login as treasurer and add a contribution
TREASURER_TOKEN=$(curl -s -X POST "http://localhost:8000/users/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=treasurer@test.com&password=password123" | jq -r .access_token)

curl -X POST "http://localhost:8000/chamas/1/contributions" \
-H "Authorization: Bearer $TREASURER_TOKEN" \
-H "Content-Type: application/json" \
-d '{"amount": 100.00}'

# 11. List members of chama 1
curl -X GET "http://localhost:8000/chamas/1/members" \
-H "Authorization: Bearer $ACCESS_TOKEN"
```

## 💡 Next Steps
- 📈 Create /summary endpoint for total chama balance and analytics
- 🧪 Expand test coverage with additional edge cases and performance tests
- 🌐 Build a Next.js + TypeScript frontend to visualize chama data

## 🧑‍💻 Author
**Josiah Mbao**
Track Lead (Cloud & DevOps) – GDSC USIU
GitHub • LinkedIn

## 🪄 License

This project is licensed under the MIT License.

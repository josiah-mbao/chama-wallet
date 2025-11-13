# Chama Wallet API

![CI](https://github.com/josiah-mbao/chama-wallet/actions/workflows/tests.yml/badge.svg)
![Coverage](https://img.shields.io/badge/Coverage-73%25-brightgreen)

A simple **FastAPI + Docker + PostgreSQL** backend for managing chama (group savings) members and their contributions. 
Built to demonstrate how to design, containerize, and run a real-world financial microservice.

---

## 🚀 Features

* **🔐 JWT Authentication:** Secure user registration and login for API access.
* **🧑‍💻 User Management:** Register new API users and retrieve current user details (`/users/me`).
* 🧾 Register new chama members
* 💰 Record contributions from members
* 📊 Retrieve all members with their total contributions
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
git clone https://github.com/your-username/chama-wallet.git
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
# Add a member
docker-compose run --rm api alembic upgrade head
```
Visit: 👉 http://localhost:8000/docs


### 4️⃣ Test the API (Authenticated Flow)

The core application features are protected by JWT. You must first register and log in to get an access token

```bash
# 1. Register an API User
curl -X POST "http://localhost:8000/users/" \
-H "Content-Type: application/json" \
-d '{"email": "test@example.com", "password": "password123"}'

# 2. Login and get JWT Access Token
ACCESS_TOKEN=$(curl -s -X POST "http://localhost:8000/users/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=test@example.com&password=password123" | jq -r .access_token)
echo "Access Token: $ACCESS_TOKEN"

# 3. Use the token to access a protected route (e.g., Get the current user)
curl -X GET "http://localhost:8000/users/me" \
-H "Authorization: Bearer $ACCESS_TOKEN"

# 4. Use the token for application logic (Protected endpoint example - Add a member)
curl -X POST "http://localhost:8000/members" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $ACCESS_TOKEN" \
-d '{"name": "Josiah", "email": "josiah@example.com"}'
```

## 💡 Next Steps
- 📈 Create /summary endpoint for total chama balance
- 🧪 Write unit tests using pytest
- 🌐 Build a Next.js + TypeScript frontend to visualize chama data

## 🧑‍💻 Author
**Josiah Mbao**
Track Lead (Cloud & DevOps) – GDSC USIU
GitHub • LinkedIn

## 🪄 License

This project is licensed under the MIT License.

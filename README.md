A simple **FastAPI + Docker + PostgreSQL** backend for managing chama (group savings) members and their contributions.  
Built to demonstrate how to design, containerize, and run a real-world financial microservice in just a few hours.

---

## 🚀 Features

- 🧾 Register new chama members  
- 💰 Record contributions from members  
- 📊 Retrieve all members with their total contributions  
- 🐳 Fully containerized with Docker Compose  
- ⚡ Built with FastAPI + SQLAlchemy + PostgreSQL

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|-------------|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL) |
| ORM | SQLAlchemy |
| Serialization | Pydantic |
| Containerization | Docker & Docker Compose |

---

## 🗂️ Project Structure

```bash
chama-wallet/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── database.py          # DB connection setup
│   ├── requirements.txt     # Dependencies
│   └── Dockerfile           # API Docker image
├── docker-compose.yml       # Multi-container setup
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/chama-wallet.git
cd chama-wallet
```

### 2️⃣ Build and Run with Docker
```bash
docker-compose up --build
```
This will start both:
	•	🐘 PostgreSQL (on port 5432)
	•	⚡ FastAPI backend (on port 8000)

Visit:
👉 http://localhost:8000/docs

### 3️⃣ Test the API

Open Swagger docs:
👉 http://localhost:8000/docs

Or use curl:
```bash
# Add a member
curl -X POST "http://localhost:8000/members" \
-H "Content-Type: application/json" \
-d '{"name": "Josiah", "email": "josiah@example.com"}'

# Record a contribution
curl -X POST "http://localhost:8000/contributions" \
-H "Content-Type: application/json" \
-d '{"amount": 500.0, "member_id": 1}'

# Get all members with contributions
curl http://localhost:8000/members
```

## 💡 Next Steps
- 🔐 Add JWT authentication (Next)
- 📈 Create /summary endpoint for total chama balance
- 🗄️ Switch to PostgreSQL for persistence (Done)
- 🧪 Write unit tests using pytest
- 🌐 Build a Next.js + TypeScript frontend to visualize chama data

## 🧑‍💻 Author
**Josiah Mbao**
Track Lead (Cloud & DevOps) – GDSC USIU
GitHub • LinkedIn

## 🪄 License

This project is licensed under the MIT License.

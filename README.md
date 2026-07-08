# 🥗 NutriBudget-AI

An AI-powered health and personal finance assistant that helps users track calories, estimate nutrition from food photos or descriptions, and manage daily expenses—all in one application.

## 🚀 Features

### 🍽️ AI Calorie Tracker

* Estimate calories and macronutrients from food images.
* Analyze meals from text descriptions.
* View detailed nutritional information.
* Edit AI predictions before saving.
* Track daily calorie intake and nutrition history.

### 💰 Budget Tracker

* Record daily expenses.
* Categorize spending.
* View monthly expense summaries.
* Track personal financial habits.
* Support shared expense tracking with collaborators.

### 👤 User Management

* User registration with email or phone.
* Secure login using JWT authentication.
* Password reset functionality.
* User profile management.

## 🛠️ Tech Stack

### Backend

* FastAPI
* SQLAlchemy (Async)
* PostgreSQL (Supabase)
* Alembic
* Pydantic
* JWT Authentication
* Python 3.12

### Frontend

* React
* TypeScript
* Tailwind CSS

### AI

* Vision model for food recognition
* Nutrition estimation from food images
* Food description analysis

## 📂 Project Structure

```text
NutriBudget-AI/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
└── README.md
```

## ⚙️ Installation

### Clone the repository

```bash
git clone https://github.com/<your-username>/NutriBudget-AI.git
cd NutriBudget-AI
```

### Backend Setup

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside the backend directory and configure your environment variables.

Run database migrations:

```bash
alembic upgrade head
```

Start the backend server:

```bash
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

## 📸 Planned Features

* Barcode scanning
* Meal history analytics
* Personalized nutrition recommendations
* AI meal suggestions
* Weekly and monthly nutrition reports
* Budget insights and visualizations
* Export reports as PDF
* Mobile application
* OCR for nutrition labels

## 📊 API Documentation

After starting the backend, open:

```
http://localhost:8000/docs
```

Swagger UI provides interactive API documentation.

## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push to your branch.
5. Open a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Soumik Dash**

---

⭐ If you find this project useful, consider giving it a star on GitHub!

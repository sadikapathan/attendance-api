# Employee Attendance & Analytics API

## Project Overview

This project is an Employee Attendance & Analytics API built using Python, FastAPI, and MongoDB.

It provides employee management, attendance punch-in and punch-out, manual attendance corrections with an audit trail, and analytics endpoints.

## Technologies Used

- Python
- FastAPI
- MongoDB
- PyMongo
- Pydantic
- Uvicorn

## Features

- Create and list employees
- Employee punch-in and punch-out
- View attendance records with pagination
- Manually correct attendance records
- Maintain an audit trail for attendance corrections
- Monthly employee attendance analytics
- Department-wise attendance summary
- Late attendance leaderboard
- Department attendance trends
- Database health check
- MongoDB indexes for data integrity and query performance

## Project Structure

```text
attendance-api/
├── app/
│   └── main.py
├── .venv/
├── requirements.txt
├── README.md
├── REVIEW.md
├── DECISIONS.md
└── .gitignore
```

## Prerequisites

- Python 3.11 or later
- MongoDB installed and running
- pip

## Installation

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd attendance-api
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual GitHub repository URL.

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

On Windows:

```powershell
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure MongoDB

The application uses the following default configuration:

```text
MONGO_URI=mongodb://localhost:27017
MONGO_DB=attendance_db
```

Make sure MongoDB is running before starting the application.

### 6. Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

## API Documentation

After starting the application, open the following URLs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API welcome endpoint |
| GET | `/health` | Health check |
| POST | `/employees` | Create an employee |
| GET | `/employees` | List employees |
| POST | `/attendance/punch-in` | Record punch-in |
| POST | `/attendance/punch-out` | Record punch-out |
| GET | `/attendance` | List attendance records |
| PATCH | `/attendance/{emp_code}/{attendance_date}` | Correct attendance |
| GET | `/analytics/employees/{emp_code}/monthly` | Monthly employee analytics |
| GET | `/analytics/departments/summary` | Department attendance summary |
| GET | `/analytics/leaderboard/late` | Late attendance leaderboard |
| GET | `/analytics/departments/{department}/trend` | Department attendance trend |
| GET | `/admin/explain/{endpoint}` | Query execution plan information |

## Database Collections

- `employees`: Stores employee information.
- `attendance_logs`: Stores daily attendance records.
- `audit_logs`: Stores attendance correction history.

## Testing

The API endpoints can be tested using Swagger UI at:

http://localhost:8000/docs

Select an endpoint, click **Try it out**, enter the required request data, and click **Execute**.

## Design Decisions and Code Review

- `DECISIONS.md` describes the design decisions made for this project.
- `REVIEW.md` contains code review observations and recommendations.

## Author

Sadik Aslam Pathan

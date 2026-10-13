
from datetime import datetime, timezone, date
from calendar import monthrange
import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError


# --------------------------------------------------
# APP AND DATABASE
# --------------------------------------------------

app = FastAPI(title="Employee Attendance & Analytics API")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "attendance_db")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=3000,
    tz_aware=True,
)

db = client[MONGO_DB]

employees = db["employees"]
attendance_logs = db["attendance_logs"]
audit_logs = db["audit_logs"]


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class EmployeeCreate(BaseModel):
    emp_code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    email: str
    department: str = Field(min_length=1, max_length=100)
    joined_on: date
    shift_start: str = "09:00"
    shift_end: str = "18:00"


class PunchInRequest(BaseModel):
    emp_code: str
    status: str = "PRESENT"


class PunchOutRequest(BaseModel):
    emp_code: str


class AttendanceCorrection(BaseModel):
    status: str | None = None
    punch_in: datetime | None = None
    punch_out: datetime | None = None
    correction_reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def utc_now():
    return datetime.now(timezone.utc)


def get_employee(emp_code: str):
    employee = employees.find_one({"emp_code": emp_code})

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return employee


def get_attendance_date():
    # Uses UTC date. Change to business timezone if required.
    return utc_now().date().isoformat()


# --------------------------------------------------
# DATABASE INDEXES
# --------------------------------------------------

@app.on_event("startup")
def create_indexes():
    employees.create_index(
        [("emp_code", ASCENDING)],
        unique=True,
    )

    attendance_logs.create_index(
        [("emp_code", ASCENDING), ("date", ASCENDING)],
        unique=True,
    )

    attendance_logs.create_index(
        [("date", ASCENDING), ("status", ASCENDING)]
    )

    audit_logs.create_index(
        [("emp_code", ASCENDING), ("date", ASCENDING)]
    )


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/")
def home():
    return {"message": "Employee Attendance API is running"}


@app.get("/health")
def health():
    try:
        client.admin.command("ping")
        return {"status": "ok", "database": MONGO_DB}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable",
        )


# --------------------------------------------------
# EMPLOYEES
# --------------------------------------------------

@app.post("/employees", status_code=201)
def create_employee(employee: EmployeeCreate):
    document = employee.model_dump()
    document["joined_on"] = document["joined_on"].isoformat()
    document["created_at"] = utc_now()

    try:
        employees.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Employee code already exists",
        )

    return {
        "message": "Employee created successfully",
        "emp_code": employee.emp_code,
    }


@app.get("/employees")
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = employees.count_documents({})

    results = list(
        employees.find({}, {"_id": 0})
        .sort("emp_code", ASCENDING)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "employees": results,
    }


# --------------------------------------------------
# ATTENDANCE: PUNCH IN
# --------------------------------------------------

@app.post("/attendance/punch-in", status_code=201)
def punch_in(data: PunchInRequest):
    get_employee(data.emp_code)

    allowed_statuses = {"PRESENT", "WFH"}

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=422,
            detail="Status must be PRESENT or WFH",
        )

    now = utc_now()
    today = now.date().isoformat()

    record = {
        "emp_code": data.emp_code,
        "date": today,
        "status": data.status,
        "punch_in": now,
        "punch_out": None,
        "created_at": now,
        "updated_at": now,
    }

    try:
        attendance_logs.insert_one(record)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Attendance already recorded for today",
        )

    return {
        "message": "Punch-in successful",
        "emp_code": data.emp_code,
        "date": today,
        "status": data.status,
        "punch_in": now,
    }


# --------------------------------------------------
# ATTENDANCE: PUNCH OUT
# --------------------------------------------------

@app.post("/attendance/punch-out")
def punch_out(data: PunchOutRequest):
    get_employee(data.emp_code)

    today = get_attendance_date()
    now = utc_now()

    result = attendance_logs.update_one(
        {
            "emp_code": data.emp_code,
            "date": today,
            "punch_in": {"$ne": None},
            "punch_out": None,
        },
        {
            "$set": {
                "punch_out": now,
                "updated_at": now,
            }
        },
    )

    if result.matched_count == 0:
        existing = attendance_logs.find_one(
            {"emp_code": data.emp_code, "date": today}
        )

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Punch-in record not found for today",
            )

        raise HTTPException(
            status_code=409,
            detail="Already punched out",
        )

    return {
        "message": "Punch-out successful",
        "emp_code": data.emp_code,
        "date": today,
        "punch_out": now,
    }


# --------------------------------------------------
# LIST ATTENDANCE
# --------------------------------------------------

@app.get("/attendance")
def list_attendance(
    emp_code: str | None = None,
    attendance_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    filters = {}

    if emp_code:
        filters["emp_code"] = emp_code

    if attendance_date:
        filters["date"] = attendance_date.isoformat()

    total = attendance_logs.count_documents(filters)

    results = list(
        attendance_logs.find(filters, {"_id": 0})
        .sort("date", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "attendance": results,
    }


# --------------------------------------------------
# MANUAL CORRECTION WITH AUDIT TRAIL
# --------------------------------------------------

@app.patch("/attendance/{emp_code}/{attendance_date}")
def correct_attendance(
    emp_code: str,
    attendance_date: date,
    correction: AttendanceCorrection,
):
    get_employee(emp_code)

    record_date = attendance_date.isoformat()

    existing = attendance_logs.find_one(
        {"emp_code": emp_code, "date": record_date}
    )

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found",
        )

    changes = correction.model_dump(
        exclude_unset=True,
        exclude={"correction_reason"},
    )

    if not changes:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to correct",
        )

    if "status" in changes and changes["status"] not in {
        "PRESENT", "WFH", "ABSENT", "LEAVE"
    }:
        raise HTTPException(
            status_code=422,
            detail="Invalid attendance status",
        )

    # Save the original record before changing it.
    audit_logs.insert_one({
        "emp_code": emp_code,
        "date": record_date,
        "action": "MANUAL_CORRECTION",
        "before": existing,
        "changes": changes,
        "reason": correction.correction_reason,
        "corrected_at": utc_now(),
    })

    changes["updated_at"] = utc_now()

    attendance_logs.update_one(
        {"emp_code": emp_code, "date": record_date},
        {"$set": changes},
    )

    return {
        "message": "Attendance corrected successfully",
        "emp_code": emp_code,
        "date": record_date,
        "corrected_fields": list(changes.keys()),
    }


# --------------------------------------------------
# MONTHLY EMPLOYEE ANALYTICS
# --------------------------------------------------

@app.get("/analytics/employees/{emp_code}/monthly")
def employee_monthly_analytics(
    emp_code: str,
    year: int = Query(default_factory=lambda: utc_now().year),
    month: int = Query(default_factory=lambda: utc_now().month, ge=1, le=12),
):
    get_employee(emp_code)

    start_date = date(year, month, 1).isoformat()
    end_date = date(year, month, monthrange(year, month)[1]).isoformat()

    pipeline = [
        {
            "$match": {
                "emp_code": emp_code,
                "date": {"$gte": start_date, "$lte": end_date},
            }
        },
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
            }
        },
    ]

    summary = list(attendance_logs.aggregate(pipeline))

    return {
        "emp_code": emp_code,
        "year": year,
        "month": month,
        "attendance_summary": {
            item["_id"]: item["count"] for item in summary
        },
    }


# --------------------------------------------------
# DEPARTMENT SUMMARY
# --------------------------------------------------

@app.get("/analytics/departments/summary")
def department_summary():
    pipeline = [
        {
            "$group": {
                "_id": "$department",
                "employee_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    return {
        "departments": list(employees.aggregate(pipeline))
    }


# --------------------------------------------------
# LATE ARRIVAL LEADERBOARD
# --------------------------------------------------

@app.get("/analytics/leaderboard/late")
def late_arrival_leaderboard(
    limit: int = Query(10, ge=1, le=100),
):
    pipeline = [
        {
            "$lookup": {
                "from": "employees",
                "localField": "emp_code",
                "foreignField": "emp_code",
                "as": "employee",
            }
        },
        {"$unwind": "$employee"},
        {
            "$match": {
                "punch_in": {"$ne": None},
                "status": {"$in": ["PRESENT", "WFH"]},
            }
        },
        {
            "$addFields": {
                "scheduled_start": {
                    "$dateFromString": {
                        "dateString": {
                            "$concat": ["$date", "T", "$employee.shift_start", ":00"]
                        },
                        "onError": None,
                    }
                }
            }
        },
        {
            "$match": {
                "scheduled_start": {"$ne": None}
            }
        },
        {
            "$match": {
                "$expr": {"$gt": ["$punch_in", "$scheduled_start"]}
            }
        },
        {
            "$group": {
                "_id": "$emp_code",
                "name": {"$first": "$employee.name"},
                "late_days": {"$sum": 1},
            }
        },
        {"$sort": {"late_days": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "emp_code": "$_id",
                "name": 1,
                "late_days": 1,
            }
        },
    ]

    return {
        "leaderboard": list(attendance_logs.aggregate(pipeline))
    }


# --------------------------------------------------
# DEPARTMENT MONTHLY TREND
# --------------------------------------------------

@app.get("/analytics/departments/{department}/trend")
def department_trend(department: str):
    pipeline = [
        {
            "$lookup": {
                "from": "employees",
                "localField": "emp_code",
                "foreignField": "emp_code",
                "as": "employee",
            }
        },
        {"$unwind": "$employee"},
        {"$match": {"employee.department": department}},
        {
            "$group": {
                "_id": {
                    "year_month": {"$substr": ["$date", 0, 7]},
                    "status": "$status",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year_month": 1}},
    ]

    return {
        "department": department,
        "trend": list(attendance_logs.aggregate(pipeline)),
    }


# --------------------------------------------------
# ADMIN: EXPLAIN ENDPOINT
# --------------------------------------------------

@app.get("/admin/explain/{endpoint}")
def explain_endpoint(endpoint: str):
    explanations = {
        "employees": "Creates or lists employee records.",
        "attendance/punch-in": "Records an employee's punch-in.",
        "attendance/punch-out": "Records an employee's punch-out.",
        "attendance": "Lists attendance records with optional filters.",
        "analytics/employees": "Summarizes monthly attendance for an employee.",
        "analytics/departments": "Provides department attendance analytics.",
    }

    key = endpoint.strip("/")

    if key not in explanations:
        raise HTTPException(
            status_code=404,
            detail="No explanation available for this endpoint",
        )

    return {
        "endpoint": key,
        "explanation": explanations[key],
    }

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import re

app = FastAPI(
    title="Medical Appointment System API",
    description="A complete medical appointment booking system with doctors, patients, and appointments management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=3)
    specialization: str
    experience_years: int = Field(..., ge=1, le=50)
    consultation_fee: float = Field(..., gt=0)
    rating: float = Field(..., ge=1.0, le=5.0)

class Doctor(DoctorCreate):
    doctor_id: int
    available: bool = True

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=3)
    age: int = Field(..., ge=1, le=120)
    gender: str
    contact: str
    blood_group: str

    @validator('contact')
    def validate_contact(cls, v):
        if not re.match(r'^\d{10}$', v):
            raise ValueError('Contact must be exactly 10 digits')
        return v

class Patient(PatientCreate):
    patient_id: int

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: str
    appointment_time: str
    reason: str

class Appointment(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    appointment_date: str
    appointment_time: str
    reason: str
    status: str = "Scheduled"
    prescription: Optional[str] = None
    total_fee: float

class AppointmentComplete(BaseModel):
    prescription: str

doctors_db: List[dict] = []
patients_db: List[dict] = []
appointments_db: List[dict] = []

doctor_counter = 1
patient_counter = 1
appointment_counter = 1

def init_seed_data():
    global doctor_counter, patient_counter, appointment_counter
    
    doctors_seed = [
        {"doctor_id": 1, "name": "Dr. Anil Sharma", "specialization": "Cardiologist", "experience_years": 15, "consultation_fee": 800.0, "available": True, "rating": 4.8},
        {"doctor_id": 2, "name": "Dr. Priya Mehta", "specialization": "Dermatologist", "experience_years": 8, "consultation_fee": 600.0, "available": True, "rating": 4.5},
        {"doctor_id": 3, "name": "Dr. Ramesh Gupta", "specialization": "Neurologist", "experience_years": 20, "consultation_fee": 1000.0, "available": True, "rating": 4.9},
        {"doctor_id": 4, "name": "Dr. Sneha Patil", "specialization": "Orthopedic", "experience_years": 12, "consultation_fee": 750.0, "available": True, "rating": 4.6},
        {"doctor_id": 5, "name": "Dr. Arjun Nair", "specialization": "General Physician", "experience_years": 5, "consultation_fee": 400.0, "available": True, "rating": 4.2}
    ]
    
    patients_seed = [
        {"patient_id": 1, "name": "Rohit Verma", "age": 34, "gender": "Male", "contact": "9876543210", "blood_group": "B+"},
        {"patient_id": 2, "name": "Anita Singh", "age": 28, "gender": "Female", "contact": "9123456780", "blood_group": "O+"},
        {"patient_id": 3, "name": "Kiran Desai", "age": 45, "gender": "Male", "contact": "9988776655", "blood_group": "A+"},
        {"patient_id": 4, "name": "Meena Joshi", "age": 60, "gender": "Female", "contact": "9001122334", "blood_group": "AB-"},
        {"patient_id": 5, "name": "Raj Patel", "age": 22, "gender": "Male", "contact": "9876001234", "blood_group": "O-"}
    ]
    
    appointments_seed = [
        {"appointment_id": 1, "patient_id": 1, "doctor_id": 1, "appointment_date": "2025-08-01", "appointment_time": "10:00", "reason": "Chest Pain", "status": "Scheduled", "prescription": None, "total_fee": 800.0},
        {"appointment_id": 2, "patient_id": 2, "doctor_id": 2, "appointment_date": "2025-08-02", "appointment_time": "11:30", "reason": "Skin Rash", "status": "Scheduled", "prescription": None, "total_fee": 600.0},
        {"appointment_id": 3, "patient_id": 3, "doctor_id": 3, "appointment_date": "2025-08-03", "appointment_time": "09:00", "reason": "Headache", "status": "Checked-In", "prescription": None, "total_fee": 1000.0}
    ]
    
    doctors_db.extend(doctors_seed)
    patients_db.extend(patients_seed)
    appointments_db.extend(appointments_seed)
    
    doctor_counter = 6
    patient_counter = 6
    appointment_counter = 4

init_seed_data()

def find_doctor(doctor_id: int):
    for doctor in doctors_db:
        if doctor["doctor_id"] == doctor_id:
            return doctor
    raise HTTPException(status_code=404, detail="Doctor not found")

def find_patient(patient_id: int):
    for patient in patients_db:
        if patient["patient_id"] == patient_id:
            return patient
    raise HTTPException(status_code=404, detail="Patient not found")

def find_appointment(appointment_id: int):
    for appointment in appointments_db:
        if appointment["appointment_id"] == appointment_id:
            return appointment
    raise HTTPException(status_code=404, detail="Appointment not found")

def calculate_fee(doctor_id: int) -> float:
    doctor = find_doctor(doctor_id)
    return doctor["consultation_fee"]

def is_doctor_available(doctor_id: int) -> bool:
    doctor = find_doctor(doctor_id)
    return doctor["available"]

def filter_appointments(status: Optional[str] = None, date: Optional[str] = None):
    filtered = appointments_db
    if status is not None:
        filtered = [a for a in filtered if a["status"] == status]
    if date is not None:
        filtered = [a for a in filtered if a["appointment_date"] == date]
    return filtered

@app.get("/", tags=["Home"], response_description="Welcome message with system overview")
def home():
    return {
        "message": "Welcome to Medical Appointment System API",
        "total_doctors": len(doctors_db),
        "total_patients": len(patients_db),
        "total_appointments": len(appointments_db)
    }

@app.get("/doctors/summary", tags=["Doctors"], response_description="Summary statistics of all doctors")
def doctors_summary():
    if not doctors_db:
        return {
            "total_doctors": 0,
            "available_count": 0,
            "unavailable_count": 0,
            "average_rating": 0,
            "average_consultation_fee": 0
        }
    
    available_count = sum(1 for d in doctors_db if d["available"])
    unavailable_count = len(doctors_db) - available_count
    avg_rating = sum(d["rating"] for d in doctors_db) / len(doctors_db)
    avg_fee = sum(d["consultation_fee"] for d in doctors_db) / len(doctors_db)
    
    return {
        "total_doctors": len(doctors_db),
        "available_count": available_count,
        "unavailable_count": unavailable_count,
        "average_rating": round(avg_rating, 2),
        "average_consultation_fee": round(avg_fee, 2)
    }

@app.get("/doctors/search", tags=["Doctors"], response_description="Search doctors by keyword")
def search_doctors(search: Optional[str] = Query(None)):
    if search is None:
        return doctors_db
    
    search_lower = search.lower()
    results = [d for d in doctors_db if search_lower in d["name"].lower() or search_lower in d["specialization"].lower()]
    return results

@app.get("/doctors/browse", tags=["Doctors"], response_description="Browse doctors with advanced filtering and pagination")
def browse_doctors(
    search: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    min_fee: Optional[float] = Query(None),
    max_fee: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    available_only: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("fee"),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(3, ge=1, le=10)
):
    results = doctors_db.copy()
    
    if search is not None:
        search_lower = search.lower()
        results = [d for d in results if search_lower in d["name"].lower() or search_lower in d["specialization"].lower()]
    
    if specialization is not None:
        results = [d for d in results if d["specialization"] == specialization]
    
    if min_fee is not None:
        results = [d for d in results if d["consultation_fee"] >= min_fee]
    
    if max_fee is not None:
        results = [d for d in results if d["consultation_fee"] <= max_fee]
    
    if min_rating is not None:
        results = [d for d in results if d["rating"] >= min_rating]
    
    if available_only is not None:
        if available_only:
            results = [d for d in results if d["available"]]
    
    if sort_by == "fee":
        results.sort(key=lambda x: x["consultation_fee"], reverse=(order == "desc"))
    elif sort_by == "rating":
        results.sort(key=lambda x: x["rating"], reverse=(order == "desc"))
    elif sort_by == "experience":
        results.sort(key=lambda x: x["experience_years"], reverse=(order == "desc"))
    
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = results[start:end]
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "results": paginated
    }

@app.get("/doctors", tags=["Doctors"], response_description="List all doctors")
def get_doctors():
    return doctors_db

@app.get("/doctors/{doctor_id}", tags=["Doctors"], response_description="Get a specific doctor by ID")
def get_doctor(doctor_id: int):
    return find_doctor(doctor_id)

@app.post("/doctors", tags=["Doctors"], response_description="Create a new doctor", status_code=201)
def create_doctor(doctor_data: DoctorCreate):
    global doctor_counter
    
    new_doctor = {
        "doctor_id": doctor_counter,
        "name": doctor_data.name,
        "specialization": doctor_data.specialization,
        "experience_years": doctor_data.experience_years,
        "consultation_fee": doctor_data.consultation_fee,
        "available": True,
        "rating": doctor_data.rating
    }
    doctors_db.append(new_doctor)
    doctor_counter += 1
    
    return new_doctor

@app.put("/doctors/{doctor_id}", tags=["Doctors"], response_description="Update doctor details")
def update_doctor(doctor_id: int, doctor_data: DoctorCreate):
    doctor = find_doctor(doctor_id)
    doctor.update({
        "name": doctor_data.name,
        "specialization": doctor_data.specialization,
        "experience_years": doctor_data.experience_years,
        "consultation_fee": doctor_data.consultation_fee,
        "rating": doctor_data.rating
    })
    return doctor

@app.delete("/doctors/{doctor_id}", tags=["Doctors"], response_description="Delete a doctor")
def delete_doctor(doctor_id: int):
    doctor = find_doctor(doctor_id)
    doctors_db.remove(doctor)
    return {"message": "Doctor deleted successfully"}

@app.get("/patients", tags=["Patients"], response_description="List all patients")
def get_patients():
    return patients_db

@app.post("/patients", tags=["Patients"], response_description="Create a new patient", status_code=201)
def create_patient(patient_data: PatientCreate):
    global patient_counter
    
    new_patient = {
        "patient_id": patient_counter,
        "name": patient_data.name,
        "age": patient_data.age,
        "gender": patient_data.gender,
        "contact": patient_data.contact,
        "blood_group": patient_data.blood_group
    }
    patients_db.append(new_patient)
    patient_counter += 1
    
    return new_patient

@app.put("/patients/{patient_id}", tags=["Patients"], response_description="Update patient details")
def update_patient(patient_id: int, patient_data: PatientCreate):
    patient = find_patient(patient_id)
    patient.update({
        "name": patient_data.name,
        "age": patient_data.age,
        "gender": patient_data.gender,
        "contact": patient_data.contact,
        "blood_group": patient_data.blood_group
    })
    return patient

@app.get("/appointments/sorted", tags=["Appointments"], response_description="Get appointments sorted by specified criteria")
def get_sorted_appointments(sort_by: str = Query("date"), order: str = Query("asc")):
    results = appointments_db.copy()
    
    if sort_by == "date":
        results.sort(key=lambda x: x["appointment_date"], reverse=(order == "desc"))
    elif sort_by == "fee":
        results.sort(key=lambda x: x["total_fee"], reverse=(order == "desc"))
    elif sort_by == "status":
        results.sort(key=lambda x: x["status"], reverse=(order == "desc"))
    
    return results

@app.post("/appointments/book", tags=["Appointments"], response_description="Book a new appointment", status_code=201)
def book_appointment(appointment_data: AppointmentCreate):
    global appointment_counter
    
    find_patient(appointment_data.patient_id)
    find_doctor(appointment_data.doctor_id)
    
    if not is_doctor_available(appointment_data.doctor_id):
        raise HTTPException(status_code=400, detail="Doctor is not available")
    
    total_fee = calculate_fee(appointment_data.doctor_id)
    
    new_appointment = {
        "appointment_id": appointment_counter,
        "patient_id": appointment_data.patient_id,
        "doctor_id": appointment_data.doctor_id,
        "appointment_date": appointment_data.appointment_date,
        "appointment_time": appointment_data.appointment_time,
        "reason": appointment_data.reason,
        "status": "Scheduled",
        "prescription": None,
        "total_fee": total_fee
    }
    appointments_db.append(new_appointment)
    appointment_counter += 1
    
    return new_appointment

@app.get("/appointments", tags=["Appointments"], response_description="Get appointments with optional filtering")
def get_appointments(status: Optional[str] = Query(None), date: Optional[str] = Query(None)):
    return filter_appointments(status, date)

@app.get("/appointments/{appointment_id}", tags=["Appointments"], response_description="Get appointment details with doctor and patient names")
def get_appointment(appointment_id: int):
    appointment = find_appointment(appointment_id)
    patient = find_patient(appointment["patient_id"])
    doctor = find_doctor(appointment["doctor_id"])
    
    return {
        **appointment,
        "patient_name": patient["name"],
        "doctor_name": doctor["name"]
    }

@app.delete("/appointments/{appointment_id}", tags=["Appointments"], response_description="Cancel an appointment")
def cancel_appointment(appointment_id: int):
    appointment = find_appointment(appointment_id)
    appointment["status"] = "Cancelled"
    
    return {
        "message": "Appointment cancelled",
        "appointment_id": appointment_id
    }

@app.post("/appointments/{appointment_id}/checkin", tags=["Workflow"], response_description="Check in patient for appointment")
def checkin_appointment(appointment_id: int):
    appointment = find_appointment(appointment_id)
    
    if appointment["status"] != "Scheduled":
        raise HTTPException(status_code=400, detail="Appointment is not in Scheduled status")
    
    appointment["status"] = "Checked-In"
    
    return {
        "message": "Patient checked in",
        "status": "Checked-In"
    }

@app.post("/appointments/{appointment_id}/complete", tags=["Workflow"], response_description="Complete appointment and add prescription")
def complete_appointment(appointment_id: int, completion_data: AppointmentComplete):
    appointment = find_appointment(appointment_id)
    
    if appointment["status"] != "Checked-In":
        raise HTTPException(status_code=400, detail="Appointment must be in Checked-In status")
    
    appointment["status"] = "Completed"
    appointment["prescription"] = completion_data.prescription
    
    return {
        "message": "Appointment completed",
        "prescription": completion_data.prescription
    }

@app.get("/appointments/{appointment_id}/history", tags=["Workflow"], response_description="Get complete appointment history")
def appointment_history(appointment_id: int):
    appointment = find_appointment(appointment_id)
    patient = find_patient(appointment["patient_id"])
    doctor = find_doctor(appointment["doctor_id"])
    
    return {
        "appointment_id": appointment["appointment_id"],
        "patient_name": patient["name"],
        "doctor_name": doctor["name"],
        "appointment_date": appointment["appointment_date"],
        "appointment_time": appointment["appointment_time"],
        "reason": appointment["reason"],
        "status": appointment["status"],
        "prescription": appointment["prescription"],
        "total_fee": appointment["total_fee"]
    }

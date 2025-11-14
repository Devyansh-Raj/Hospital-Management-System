from .database import db

class User(db.Model):   
    id = db.Column(db.Integer, primary_key=True)      
    username = db.Column(db.String(80), unique = True, nullable = False)
    email = db.Column(db.String(100), unique = True, nullable = False)
    password = db.Column(db.String(20), nullable = False)
    phone = db.Column(db.String(15), nullable=True)
    type = db.Column(db.String(20), nullable = False, default='user')
    requests = db.relationship('Appointment', backref='user', lazy=True)

class Doctors(db.Model):   
    id = db.Column(db.Integer, primary_key=True)      
    name = db.Column(db.String(80), nullable = False)
    specialization = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(100), unique = True, nullable = False) 
    password = db.Column(db.String(20), nullable = False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    #availability = db.Column(db.String(200), nullable = False)  
    # relationship to appointments and slots
    requests = db.relationship('Appointment', backref='doctor', lazy=True)
    slots = db.relationship('Slot', backref='doctor', lazy=True)

from datetime import datetime

class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)        # if your users table is 'user'
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)   # point to doctors table
    appointment_date = db.Column(db.DateTime, nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=True)
    reason = db.Column(db.String(500))   # store short reason
    status = db.Column(db.String(20), nullable=False, default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'appointment_date', name='uix_doctor_appointment_dt'),
    )


class Slot(db.Model):
    __tablename__ = 'slots'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    label = db.Column(db.String(100))


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    treatment_notes = db.Column(db.String(1000))  # treatment details
    prescription_text = db.Column(db.String(2000))  # medicine/prescription details
    image_path = db.Column(db.String(500))  # path to uploaded prescription image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # relationships
    appointment = db.relationship('Appointment', backref='prescription', uselist=False)
    doctor = db.relationship('Doctors', backref='prescriptions')


                                                                                                
                                                                                                                                                   
                                                   
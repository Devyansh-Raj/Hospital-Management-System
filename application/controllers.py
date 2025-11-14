from flask import Flask, render_template,redirect,request, jsonify
from flask import current_app as app
from .models import * 
from datetime import datetime


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        pwd = request.form.get("pwd", "").strip()
        
        this_user = User.query.filter_by(username=username).first()
        if not this_user:
            return render_template("not_exist.html")
        
        if this_user.password == pwd:
            if this_user.type == 'admin':
                all_doctors = Doctors.query.all()
                return render_template('admin_dashboard.html', this_user=this_user, all_doctors=all_doctors)
            elif this_user.type == 'doctor':
                doctor = Doctors.query.filter_by(email=this_user.email).first()
                appointments = []
                if doctor:
                    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_date).all()
                return render_template('doctor_dashboard.html', this_user=this_user, doctor=doctor, appointments=appointments)
            elif this_user.type == 'user':
                all_doctors = Doctors.query.all()
                return render_template('user_dashboard.html', this_user=this_user, all_doctors=all_doctors)
            else:
                return render_template("incorrect.html")
        else:
            return render_template("incorrect.html")
    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        phone = request.form.get("phone", "").strip()
        pwd= request.form["pwd"]
        user_name = User.query.filter(User.username == username).first()
        user_email = User.query.filter(User.email == email).first()
        if user_name or user_email:
            return render_template("already.html")

        else:
            new_user = User(username=username, email=email, password=pwd, phone=phone, type='user')
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
    return render_template('register.html') 

@app.route('/admin')
def admin():
    # when visiting /admin directly we don't have a current_user session in this simple app
    # so avoid passing a list as `this_user` (which caused confusion). Pass None instead.
    this_user = None
    all_doctors = Doctors.query.all()
    return render_template('admin_dashboard.html', this_user=this_user, all_doctors=all_doctors)


@app.route('/home/<int:user_id>')
def home(user_id):
    this_user = User.query.get(user_id)
    all_doctors = Doctors.query.all() 
    return render_template('user_dashboard.html', this_user=this_user, all_doctors=all_doctors)



@app.route('/doctors', methods=['GET','POST'])
def doctors():
    if request.method == "POST":
        name = request.form["name"]
        specialization = request.form["specialization"]
        email = request.form["email"]
        password = request.form["password"]
       # availability = request.form["availability"]
        new_doctor = Doctors(name=name, specialization=specialization , password=password, email=email)
        db.session.add(new_doctor)
        db.session.commit()
        # create default slots for this doctor
        from datetime import time
        default_slots = [
            (time(10,0), time(11,0), '10:00 - 11:00 AM'),
            (time(13,0), time(14,0), '1:00 - 2:00 PM'),
            (time(16,0), time(17,0), '4:00 - 5:00 PM'),
        ]
        for s in default_slots:
            slot = Slot(doctor_id=new_doctor.id, start_time=s[0], end_time=s[1], label=s[2])
            db.session.add(slot)
        db.session.commit()

        # ensure there's a corresponding User account for this doctor so they can log in
        # use the doctor's NAME as username (so they log in with their name and password)
        existing_user = User.query.filter((User.email == email) | (User.username == name)).first()
        if not existing_user:
            # derive a username from doctor's name
            uname = name.replace(' ', '').lower()
            # avoid username collisions by appending a number if needed
            base = uname
            i = 1
            while User.query.filter_by(username=uname).first():
                uname = f"{base}{i}"
                i += 1

            doc_user = User(username=uname, email=email, password=password, type='doctor')
            db.session.add(doc_user)
            db.session.commit()
            print(f"[NEW DOCTOR] Created user account: username={uname}, password={password}")
        return redirect('/admin')
    # this_user is not defined in this scope; render page without it
    return render_template('doctors.html')


# @app.route('/appointment/<int:user_id>', methods=['GET','POST'])
# def appointment(user_id):
#     this_user = User.query.get(user_id)
#     all_doctors = Doctors.query.all()
#     if request.method == "POST":
#         doctor_id = request.form["doctor_id"]
#         appointment_date = request.form["date"]
#         reason = request.form["reason"]
#         new_appointment = Appointment(user_id=this_user.id, doctor_id=doctor_id, appointment_date=appointment_date, reason=reason)
#         db.session.add(new_appointment)
#         db.session.commit()
#         return redirect(f'/home/{this_user.id}')
#     return render_template('appointment.html', this_user=this_user, all_doctors=all_doctors)
@app.route('/appointment/<int:user_id>', methods=['GET', 'POST'])
def appointment(user_id):
    this_user = User.query.get(user_id)
    all_doctors = Doctors.query.all()

    if request.method == "POST":
        doctor_id = int(request.form['doctor_id'])
        date_raw = request.form['date']       # YYYY-MM-DD
        slot_id = int(request.form['slot_id'])
        reason = request.form['reason']

        slot = Slot.query.get(slot_id)
        # combine date + slot.start_time to a datetime
        appointment_dt = datetime.fromisoformat(date_raw + 'T' + slot.start_time.strftime('%H:%M:%S'))

        # prevent double-booking at application level
        exists = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appointment_dt).first()
        if exists:
            # rebuild doctor_slots for the template and show an error
            doctor_slots = {d.id: [{'id': s.id, 'label': s.label} for s in d.slots] for d in all_doctors}
            error = 'Selected slot is already booked. Please choose another slot.'
            return render_template('appoitment.html', this_user=this_user, all_doctors=all_doctors, doctor_slots=doctor_slots, error=error)

        new_appointment = Appointment(
            user_id=this_user.id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            appointment_date=appointment_dt,
            reason=reason
        )
        db.session.add(new_appointment)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            # if DB uniqueness constraint triggered, return error to user
            doctor_slots = {d.id: [{'id': s.id, 'label': s.label} for s in d.slots] for d in all_doctors}
            error = 'Selected slot is already booked (concurrent). Please choose another slot.'
            return render_template('appoitment.html', this_user=this_user, all_doctors=all_doctors, doctor_slots=doctor_slots, error=error)

        return redirect(f'/home/{this_user.id}')
    
    # if doctor_id query param is provided (clicked from dashboard), preselect that doctor
    selected_doctor = None
    qdoc = request.args.get('doctor_id')
    if qdoc:
        try:
            selected_doctor = Doctors.query.get(int(qdoc))
        except Exception:
            selected_doctor = None
    
    # our template file is named 'appoitment.html' (typo in filename), render that
    # load slots per doctor to show in the form via JS or server-side
    # small convenience: build mapping doctor_id -> slots
    doctor_slots = {d.id: [{'id': s.id, 'label': s.label} for s in d.slots] for d in all_doctors}
    return render_template('appoitment.html', this_user=this_user, all_doctors=all_doctors, doctor_slots=doctor_slots, selected_doctor=selected_doctor)


@app.route('/slots/<int:doctor_id>/<date>')
def slots_for_doctor(doctor_id, date):
    """Return JSON list of slots for doctor with availability on given date (YYYY-MM-DD)."""
    slots = Slot.query.filter_by(doctor_id=doctor_id).all()
    out = []
    for s in slots:
        dt = datetime.fromisoformat(date + 'T' + s.start_time.strftime('%H:%M:%S'))
        booked = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=dt).first() is not None
        out.append({'id': s.id, 'label': s.label, 'available': not booked})
    return jsonify(out)


@app.route('/admin/appointments')
def admin_appointments():
    """Admin view: all appointments in the system."""
    appointments = Appointment.query.all()
    return render_template('admin_appointments.html', appointments=appointments)


@app.route('/admin/appointments/cancel/<int:appt_id>', methods=['POST'])
def admin_cancel_appointment(appt_id):
    """Allow an admin to cancel an appointment (marks status as 'cancelled')."""
    appt = Appointment.query.get(appt_id)
    if not appt:
        return redirect('/admin/appointments')
    appt.status = 'cancelled'
    db.session.add(appt)
    db.session.commit()
    return redirect('/admin/appointments')


@app.route('/admin/doctor/deactivate/<int:doctor_id>', methods=['POST'])
def admin_deactivate_doctor(doctor_id):
    """Admin removes/deactivates a doctor (prevents future bookings)."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/admin')
    doc.is_active = False
    db.session.add(doc)
    db.session.commit()
    print(f"[ADMIN] Doctor {doc.name} (ID {doc.id}) deactivated")
    return redirect('/admin')


@app.route('/admin/doctor/reactivate/<int:doctor_id>', methods=['POST'])
def admin_reactivate_doctor(doctor_id):
    """Admin renews/reactivates a deactivated doctor."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/admin')
    doc.is_active = True
    db.session.add(doc)
    db.session.commit()
    print(f"[ADMIN] Doctor {doc.name} (ID {doc.id}) reactivated")
    return redirect('/admin')


@app.route('/doctor/appointments/<int:doctor_id>')
def doctor_appointments(doctor_id):
    """Doctor view: their own appointments."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/login')
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    return render_template('doctor_appointments.html', doctor=doc, appointments=appointments)


@app.route('/prescription/add/<int:appointment_id>', methods=['GET', 'POST'])
def add_prescription(appointment_id):
    """Doctor adds prescription and optional image to an appointment."""
    """Prescription can only be added after appointment is marked completed."""
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime as dt
    
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return redirect('/login')
    
    # Only allow prescription for completed appointments
    if appt.status != 'completed':
        print(f"[PRESCRIPTION] Attempt to add prescription for non-completed appointment {appointment_id}")
        return render_template('add_prescription.html', appointment=appt, prescription=None)
    
    if request.method == 'POST':
        treatment_notes = request.form.get('treatment_notes', '')
        prescription_text = request.form.get('prescription_text', '')
        
        # Check if prescription already exists
        existing = Prescription.query.filter_by(appointment_id=appointment_id).first()
        if existing:
            existing.treatment_notes = treatment_notes
            existing.prescription_text = prescription_text
            db.session.add(existing)
        else:
            prescription = Prescription(
                appointment_id=appointment_id,
                doctor_id=appt.doctor_id,
                treatment_notes=treatment_notes,
                prescription_text=prescription_text
            )
            db.session.add(prescription)
        
        # Handle image upload if present
        if 'prescription_image' in request.files:
            file = request.files['prescription_image']
            if file and file.filename:
                filename = secure_filename(f"prescription_{appointment_id}_{dt.now().timestamp()}.jpg")
                upload_path = os.path.join('static', 'uploads', filename)
                file.save(upload_path)
                if not existing:
                    prescription.image_path = upload_path
                else:
                    existing.image_path = upload_path
        
        db.session.commit()
        print(f"[PRESCRIPTION] Added for appointment {appointment_id}")
        return redirect(f'/doctor/appointments/{appt.doctor_id}')
    
    # GET: show form to add prescription
    prescription = Prescription.query.filter_by(appointment_id=appointment_id).first()
    return render_template('add_prescription.html', appointment=appt, prescription=prescription)


@app.route('/prescription/view/<int:appointment_id>')
def view_prescription(appointment_id):
    """View prescription for an appointment."""
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return redirect('/login')
    
    prescription = Prescription.query.filter_by(appointment_id=appointment_id).first()
    return render_template('view_prescription.html', appointment=appt, prescription=prescription)


@app.route('/appointment/mark-complete/<int:appointment_id>', methods=['POST'])
def mark_appointment_complete(appointment_id):
    """Doctor marks an appointment as completed."""
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return redirect('/login')
    
    appt.status = 'completed'
    db.session.add(appt)
    db.session.commit()
    print(f"[APPOINTMENT] Marked appointment {appointment_id} as completed")
    return redirect(f'/doctor/appointments/{appt.doctor_id}')


# ===== TIER 1: NEW FEATURES =====

# 1. ADMIN DASHBOARD STATS
@app.route('/admin/stats')
def admin_stats_api():
    """API endpoint to return counts of doctors, patients, appointments."""
    total_doctors = Doctors.query.count()
    total_patients = User.query.filter_by(type='user').count()
    total_appointments = Appointment.query.count()
    completed_appointments = Appointment.query.filter_by(status='completed').count()
    return jsonify({
        'doctors': total_doctors,
        'patients': total_patients,
        'appointments': total_appointments,
        'completed': completed_appointments
    })


# 2. PATIENT PROFILE VIEW & EDIT
@app.route('/patient/profile/<int:user_id>')
def patient_profile(user_id):
    """Patient views their profile."""
    user = User.query.get(user_id)
    if not user or user.type != 'user':
        return redirect('/login')
    return render_template('patient_profile.html', user=user)


@app.route('/patient/profile/edit/<int:user_id>', methods=['GET', 'POST'])
def patient_profile_edit(user_id):
    """Patient edits their profile."""
    user = User.query.get(user_id)
    if not user or user.type != 'user':
        return redirect('/login')
    
    if request.method == 'POST':
        user.username = request.form.get('username', user.username).strip()
        user.email = request.form.get('email', user.email).strip()
        user.phone = request.form.get('phone', user.phone).strip()
        user.password = request.form.get('password', user.password).strip()
        db.session.commit()
        return redirect(f'/patient/profile/{user_id}')
    
    return render_template('patient_profile_edit.html', user=user)


# 3. PATIENT APPOINTMENT HISTORY
@app.route('/patient/history/<int:user_id>')
def patient_history(user_id):
    """Patient views their appointment history with prescriptions."""
    user = User.query.get(user_id)
    if not user or user.type != 'user':
        return redirect('/login')
    
    appointments = Appointment.query.filter_by(user_id=user_id).order_by(Appointment.appointment_date.desc()).all()
    return render_template('patient_history.html', user=user, appointments=appointments)


# 4. PATIENT APPOINTMENT CANCELLATION
@app.route('/appointment/cancel/<int:appt_id>', methods=['POST'])
def patient_cancel_appointment(appt_id):
    """Allow a patient to cancel their own appointment."""
    appt = Appointment.query.get(appt_id)
    if not appt:
        return redirect('/login')
    
    # Only allow cancellation if appointment is scheduled
    if appt.status != 'scheduled':
        return redirect(f'/patient/history/{appt.user_id}')
    
    appt.status = 'cancelled'
    db.session.add(appt)
    db.session.commit()
    return redirect(f'/patient/history/{appt.user_id}')


# 5. DOCTOR PATIENT LIST
@app.route('/doctor/patients/<int:doctor_id>')
def doctor_patients(doctor_id):
    """Display list of unique patients seen by a doctor."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/login')
    
    # Get all completed appointments for this doctor to list patients
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    # Extract unique patients (avoid duplicates)
    patients = {}
    for appt in appointments:
        if appt.user_id not in patients:
            patients[appt.user_id] = appt.user
    
    return render_template('doctor_patients.html', doctor=doc, patients=list(patients.values()))


# 6. DOCTOR AVAILABILITY MANAGEMENT
@app.route('/doctor/availability/<int:doctor_id>', methods=['GET', 'POST'])
def doctor_availability(doctor_id):
    """Doctor manages their appointment slots."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/login')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            label = request.form.get('label')
            
            from datetime import datetime as dt, time
            start_time = dt.strptime(start_time_str, '%H:%M').time()
            end_time = dt.strptime(end_time_str, '%H:%M').time()
            
            slot = Slot(doctor_id=doctor_id, start_time=start_time, end_time=end_time, label=label)
            db.session.add(slot)
            db.session.commit()
            return redirect(f'/doctor/availability/{doctor_id}')
        
        elif action == 'delete':
            slot_id = request.form.get('slot_id')
            slot = Slot.query.get(slot_id)
            if slot and slot.doctor_id == doctor_id:
                db.session.delete(slot)
                db.session.commit()
            return redirect(f'/doctor/availability/{doctor_id}')
    
    slots = Slot.query.filter_by(doctor_id=doctor_id).all()
    return render_template('doctor_availability.html', doctor=doc, slots=slots)


# 7. ADMIN EDIT DOCTOR PROFILE
@app.route('/admin/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    """Admin edits doctor profile."""
    doc = Doctors.query.get(doctor_id)
    if not doc:
        return redirect('/admin')
    
    if request.method == 'POST':
        doc.name = request.form.get('name', doc.name).strip()
        doc.specialization = request.form.get('specialization', doc.specialization).strip()
        doc.email = request.form.get('email', doc.email).strip()
        is_active_str = request.form.get('is_active', '1')
        doc.is_active = is_active_str == '1'
        db.session.commit()
        return redirect('/admin')
    
    return render_template('admin_edit_doctor.html', doctor=doc)


# --- ADMIN: PATIENT MANAGEMENT ---
@app.route('/admin/patient/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_patient(user_id):
    """Admin edits a patient's profile."""
    patient = User.query.get(user_id)
    if not patient or patient.type not in ('user', 'blacklisted'):
        return redirect('/admin/search')

    if request.method == 'POST':
        patient.username = request.form.get('username', patient.username).strip()
        patient.email = request.form.get('email', patient.email).strip()
        patient.phone = request.form.get('phone', patient.phone).strip()
        db.session.commit()
        return redirect('/admin/search')

    return render_template('admin_edit_patient.html', patient=patient)


@app.route('/admin/patient/deactivate/<int:user_id>', methods=['POST'])
def admin_deactivate_patient(user_id):
    """Admin deactivates (blacklists) a patient."""
    patient = User.query.get(user_id)
    if not patient:
        return redirect('/admin/search')
    # mark as blacklisted
    patient.type = 'blacklisted'
    db.session.commit()
    return redirect('/admin/search')


@app.route('/admin/patient/reactivate/<int:user_id>', methods=['POST'])
def admin_reactivate_patient(user_id):
    """Admin reactivates a blacklisted patient."""
    patient = User.query.get(user_id)
    if not patient:
        return redirect('/admin/search')
    patient.type = 'user'
    db.session.commit()
    return redirect('/admin/search')


# 8. LOGOUT
@app.route('/logout')
def logout():
    """User logout - redirects to login."""
    return redirect('/login')


# 9. SEARCH FUNCTIONALITY
@app.route('/admin/search', methods=['GET', 'POST'])
def admin_search():
    """Admin search for doctors/patients."""
    doctors = []
    patients = []
    search_query = " "
    search_type = "all"
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        search_type = request.form.get('search_type', 'all')
        
        if search_type in ['all', 'doctor']:
            doctors = Doctors.query.filter(
                (Doctors.name.ilike(f'%{search_query}%')) |
                (Doctors.specialization.ilike(f'%{search_query}%'))
            ).all()
        
        if search_type in ['all', 'patient']:
            patients = User.query.filter(
                (User.type == 'user') &
                ((User.username.ilike(f'%{search_query}%')) |
                 (User.email.ilike(f'%{search_query}%')) |
                 (User.phone.ilike(f'%{search_query}%')))
            ).all()
    
    return render_template('admin_search.html', doctors=doctors, patients=patients, 
                         search_query=search_query, search_type=search_type)


@app.route('/patient/search-doctors', methods=['GET', 'POST'])
def patient_search_doctors(user_id=None):
    """Patient search for doctors by specialization."""
    if request.method == 'POST':
        specialization = request.form.get('specialization', '').strip()
        doctors = Doctors.query.filter(
            (Doctors.specialization.ilike(f'%{specialization}%')) &
            (Doctors.is_active == True)
        ).all()
        return render_template('patient_search_doctors.html', doctors=doctors, specialization=specialization)
    
    # Get unique specializations
    specializations = db.session.query(Doctors.specialization).distinct().all()
    return render_template('patient_search_doctors.html', specializations=specializations, doctors=[], specialization='')
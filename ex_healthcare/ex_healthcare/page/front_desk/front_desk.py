import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, nowtime, add_to_date


# =============================================
# PATIENT REGISTRATION
# =============================================

@frappe.whitelist()
def create_walkin_patient(first_name, last_name=None, mobile=None, gender=None, dob=None):
	"""Register a brand-new walk-in patient."""

	patient = frappe.get_doc({
		"doctype": "Patient",
		"first_name": first_name,
		"last_name": last_name,
		"mobile": mobile,
		"sex": gender,
		"dob": dob,
	})

	patient.insert(ignore_permissions=True)

	return {
		"status": "Success",
		"patient": patient.name,
		"patient_name": patient.patient_name
	}


DEFAULT_APPOINTMENT_DURATION_MINUTES = 15
MINIMUM_APPOINTMENT_DURATION_MINUTES = 5


def _resolve_duration(appointment_type):
	"""Resolve appointment duration.

	Healthcare validates that appointment_end_datetime
	must be after appointment_datetime.

	Prefer Appointment Type duration.
	Fallback to default duration.

	Hard floor at MINIMUM_APPOINTMENT_DURATION_MINUTES so that,
	regardless of what Appointment Type / Practitioner-level
	overrides do downstream inside Healthcare's own validate(),
	we never hand off a 0/negative/None duration.
	"""

	duration = None

	if appointment_type:
		duration = frappe.db.get_value(
			"Appointment Type",
			appointment_type,
			"default_duration"
		)

	try:
		duration = int(duration) if duration else DEFAULT_APPOINTMENT_DURATION_MINUTES
	except (TypeError, ValueError):
		duration = DEFAULT_APPOINTMENT_DURATION_MINUTES

	if duration < MINIMUM_APPOINTMENT_DURATION_MINUTES:
		duration = MINIMUM_APPOINTMENT_DURATION_MINUTES

	return duration


# =============================================
# BOOKING (schedule only — no queue, no invoice)
# =============================================

@frappe.whitelist()
def create_consultation(
	patient,
	practitioner,
	department=None,
	appointment_type=None,
	appointment_date=None,
	appointment_time=None,
):
	"""Book a Patient Appointment.

	This is a pure schedule record now: no queue_status, no
	checked_in_at, no invoice. Those only come into existence once the
	patient physically arrives — see check_in_appointment() below.
	"""

	appointment_date = appointment_date or nowdate()
	appointment_time = appointment_time or nowtime()

	duration = int(_resolve_duration(appointment_type))

	appointment_datetime = f"{appointment_date} {appointment_time}"
	appointment_end_datetime = add_to_date(appointment_datetime, minutes=duration)

	appointment = frappe.get_doc({
		"doctype": "Patient Appointment",

		"patient": patient,
		"practitioner": practitioner,
		"department": department,
		"appointment_type": appointment_type,

		"appointment_date": appointment_date,
		"appointment_time": appointment_time,

		"appointment_datetime": appointment_datetime,
		"appointment_end_datetime": appointment_end_datetime,

		"duration": duration,

		"status": "Open",
	})

	try:
		appointment.insert(ignore_permissions=True)
	except frappe.ValidationError:
		frappe.log_error(
			title="Front Desk: create_consultation appointment insert failed",
			message=(
				f"patient={patient}\n"
				f"practitioner={practitioner}\n"
				f"department={department}\n"
				f"appointment_type={appointment_type}\n"
				f"appointment_date={appointment_date!r}\n"
				f"appointment_time={appointment_time!r}\n"
				f"resolved_duration={duration!r}\n"
				f"appointment_datetime={appointment_datetime!r}\n"
				f"appointment_end_datetime={appointment_end_datetime!r}\n"
			),
		)
		raise

	return {
		"status": "Success",
		"appointment": appointment.name,
	}


@frappe.whitelist()
def get_pending_checkins(date=None, patient=None):
	"""Booked appointments for `date` that have not yet been checked in
	(i.e. no Patient Encounter has been created against them yet)."""

	date = date or nowdate()

	filters = {
		"appointment_date": date,
		"status": ["!=", "Cancelled"],
	}
	if patient:
		filters["patient"] = patient

	appointments = frappe.get_all(
		"Patient Appointment",
		filters=filters,
		fields=["name", "patient", "patient_name", "practitioner", "practitioner_name", "appointment_time"],
		order_by="appointment_time asc",
	)

	if not appointments:
		return []

	already_checked_in = set(frappe.get_all(
		"Patient Encounter",
		filters={"appointment": ["in", [a.name for a in appointments]]},
		pluck="appointment",
	))

	return [a for a in appointments if a.name not in already_checked_in]


# =============================================
# CHECK-IN (creates the draft Patient Encounter
# that carries the queue from here on)
# =============================================

@frappe.whitelist()
def check_in_appointment(appointment, consultation_fee=0):
	"""Patient with a booked appointment has physically arrived.

	Creates the draft Patient Encounter (docstatus=0) that now owns
	queue_status / checked_in_at / vitals_* / consultation_invoice.
	The Patient Appointment record itself is left untouched (it stays
	a plain schedule record) apart from being linked via `appointment`.
	"""

	appt = frappe.get_doc("Patient Appointment", appointment)

	# Idempotency: if this appointment was already checked in, don't
	# spin up a second Encounter — just hand back the existing one.
	existing = frappe.db.get_value("Patient Encounter", {"appointment": appt.name}, "name")
	if existing:
		return {
			"status": "Success",
			"encounter": existing,
			"invoice": frappe.db.get_value("Patient Encounter", existing, "consultation_invoice"),
			"queue_status": frappe.db.get_value("Patient Encounter", existing, "queue_status"),
		}

	encounter = frappe.get_doc({
		"doctype": "Patient Encounter",
		"patient": appt.patient,
		"practitioner": appt.practitioner,
		"medical_department": appt.department,
		# Patient Encounter has appointment_type as a mandatory field of
		# its own — inherit it from the booking rather than asking the
		# front-desk user to re-enter something already captured.
		"appointment_type": appt.appointment_type,
		"appointment": appt.name,
		"encounter_date": nowdate(),
		"encounter_time": nowtime(),
		"queue_status": "Registered",
		"checked_in_at": now_datetime(),
	})
	encounter.insert(ignore_permissions=True)

	return _finalize_checkin(encounter, appt.patient, consultation_fee)


@frappe.whitelist()
def create_walkin_encounter(patient, practitioner, appointment_type, department=None, consultation_fee=0):
	"""Walk-in patient with no prior booking. Skips Patient Appointment
	entirely and creates the draft Patient Encounter directly.

	appointment_type is required because Patient Encounter itself has it
	as a mandatory field with no Patient Appointment to inherit it from.
	"""

	encounter = frappe.get_doc({
		"doctype": "Patient Encounter",
		"patient": patient,
		"practitioner": practitioner,
		"medical_department": department,
		"appointment_type": appointment_type,
		"encounter_date": nowdate(),
		"encounter_time": nowtime(),
		"queue_status": "Registered",
		"checked_in_at": now_datetime(),
	})
	encounter.insert(ignore_permissions=True)

	return _finalize_checkin(encounter, patient, consultation_fee)


def _finalize_checkin(encounter, patient, consultation_fee):
	"""Shared tail end of both check-in paths: raise the paid invoice (if
	any) and set the encounter's queue_status accordingly."""

	invoice_name = None

	if float(consultation_fee or 0) > 0:
		invoice_name = _create_paid_consultation_invoice(patient, consultation_fee, encounter.name)
		encounter.db_set("consultation_invoice", invoice_name)
		encounter.db_set("queue_status", "Paid - Awaiting Vitals")
	else:
		encounter.db_set("queue_status", "Payment Pending")

	return {
		"status": "Success",
		"encounter": encounter.name,
		"invoice": invoice_name,
		"queue_status": encounter.queue_status,
	}


def _create_paid_consultation_invoice(patient, amount, encounter_name):
	"""Create paid consultation Sales Invoice."""

	CONSULTATION_ITEM_CODE = "Consultation"

	patient_doc = frappe.get_doc("Patient", patient)
	customer = patient_doc.customer or patient_doc.name

	default_company = frappe.defaults.get_global_default("company")

	mode_of_payment = (
		frappe.db.get_single_value("Healthcare Settings", "default_mode_of_payment")
		or "Cash"
	)

	invoice = frappe.get_doc({
		"doctype": "Sales Invoice",

		"customer": customer,
		"patient": patient,
		"company": default_company,

		"is_pos": 1,

		"posting_date": nowdate(),
		"due_date": nowdate(),

		"items": [{
			"item_code": CONSULTATION_ITEM_CODE,
			"qty": 1,
			"rate": float(amount),
		}],

		"payments": [{
			"mode_of_payment": mode_of_payment,
			"amount": float(amount),
		}],

		"remarks": f"Consultation fee for Patient Encounter {encounter_name}",
	})

	invoice.insert(ignore_permissions=True)
	invoice.submit()

	return invoice.name


# =============================================
# QUEUE (now reads Patient Encounter, filtered
# to docstatus=0 — a submitted Encounter has
# already left the front-desk queue)
# =============================================

@frappe.whitelist()
def get_queue(date=None, queue_status=None):

	date = date or nowdate()

	filters = {
		"encounter_date": date,
		"docstatus": 0,
	}

	if queue_status:
		filters["queue_status"] = queue_status

	rows = frappe.get_all(
		"Patient Encounter",

		filters=filters,

		fields=[
			"name",
			"patient",
			"patient_name",

			"practitioner",
			"practitioner_name",

			"medical_department",

			"appointment",

			"encounter_time",

			"queue_status",

			"consultation_invoice",

			"checked_in_at",

			"vitals_temperature",
			"vitals_blood_pressure",
			"vitals_pulse",
			"vitals_weight",
			"vitals_height",
			"vitals_notes",
		],

		order_by="encounter_time asc",
	)

	return rows


# =============================================
# NURSE STATION
# =============================================

@frappe.whitelist()
def send_to_nurse(encounter):

	frappe.db.set_value("Patient Encounter", encounter, "queue_status", "With Nurse")

	return {"status": "Success"}


@frappe.whitelist()
def save_vitals(
	encounter,
	temperature=None,
	blood_pressure=None,
	pulse=None,
	weight=None,
	height=None,
	notes=None
):

	doc_updates = {
		"vitals_temperature": temperature,
		"vitals_blood_pressure": blood_pressure,
		"vitals_pulse": pulse,
		"vitals_weight": weight,
		"vitals_height": height,
		"vitals_notes": notes,

		"vitals_recorded_by": frappe.session.user,
		"vitals_recorded_on": now_datetime(),

		"queue_status": "With Doctor",
	}

	for field, value in doc_updates.items():
		frappe.db.set_value("Patient Encounter", encounter, field, value)

	return {"status": "Success"}


# =============================================
# DOCTOR QUEUE
# =============================================

@frappe.whitelist()
def start_consultation(encounter):
	"""The Encounter already exists (created at check-in) — this just
	flips it into 'In Consultation' so the doctor can open and complete
	the same draft document."""

	enc = frappe.get_doc("Patient Encounter", encounter)

	frappe.db.set_value("Patient Encounter", encounter, "queue_status", "In Consultation")

	return {
		"status": "Success",
		"patient": enc.patient,
		"practitioner": enc.practitioner,
		"encounter": enc.name,
	}


def on_patient_encounter_submit(doc, method=None):
	"""Doctor completes + submits the Encounter -> queue_status = Completed.
	No more lookup into Patient Appointment: the queue state lives on
	this document itself now."""

	doc.db_set("queue_status", "Completed")

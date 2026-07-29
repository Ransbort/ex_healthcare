import frappe
from frappe import _
from frappe.utils import (
	now_datetime,
	nowdate,
	nowtime,
	add_to_date,
	get_datetime,
)


# =============================================
# CHECK-IN
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
		"patient_name": patient.patient_name,
	}


# =============================================
# APPOINTMENT HELPERS
# =============================================

DEFAULT_APPOINTMENT_DURATION_MINUTES = 15


def _resolve_duration(appointment_type):
	"""
	Resolve appointment duration.

	Healthcare validation requires:
	appointment_end_datetime > appointment_datetime

	If duration is empty or zero, validation fails.
	"""

	if appointment_type:
		duration = frappe.db.get_value(
			"Appointment Type",
			appointment_type,
			"default_duration"
		)

		if duration and int(duration) > 0:
			return int(duration)

	return DEFAULT_APPOINTMENT_DURATION_MINUTES



def _resolve_service_unit(appointment_type, service_unit=None):
	"""
	Resolve service unit requirement based on Appointment Type.
	"""

	if service_unit:
		return service_unit

	if not appointment_type:
		return None

	allow_booking_for = frappe.db.get_value(
		"Appointment Type",
		appointment_type,
		"allow_booking_for"
	)

	if allow_booking_for == "Service Unit":
		frappe.throw(
			_(
				"Appointment Type {0} requires a Service Unit. "
				"Please select one before creating the appointment."
			).format(appointment_type)
		)

	return None



# =============================================
# CREATE CONSULTATION
# =============================================

@frappe.whitelist()
def create_consultation(
	patient,
	practitioner,
	department=None,
	appointment_type=None,
	consultation_fee=0,
	appointment_date=None,
	appointment_time=None,
	service_unit=None,
):
	"""
	Create Patient Appointment,
	create consultation invoice,
	and place patient into queue.
	"""

	appointment_date = appointment_date or nowdate()
	appointment_time = appointment_time or nowtime()

	duration = _resolve_duration(appointment_type)

	service_unit = _resolve_service_unit(
		appointment_type,
		service_unit
	)


	# Build proper datetime window
	start_datetime = get_datetime(
		f"{appointment_date} {appointment_time}"
	)

	end_datetime = add_to_date(
		start_datetime,
		minutes=duration
	)


	appointment = frappe.get_doc({
		"doctype": "Patient Appointment",

		"patient": patient,
		"practitioner": practitioner,
		"department": department,

		"appointment_type": appointment_type,
		"service_unit": service_unit,

		"appointment_date": appointment_date,
		"appointment_time": appointment_time,

		# IMPORTANT FOR HEALTHCARE VALIDATION
		"appointment_datetime": start_datetime,
		"appointment_end_datetime": end_datetime,

		"duration": duration,

		"status": "Open",
		"queue_status": "Registered",

		"checked_in_at": now_datetime(),
	})


	frappe.logger().info({
		"Patient Appointment Start": start_datetime,
		"Patient Appointment End": end_datetime,
		"Duration": duration,
	})


	appointment.insert(ignore_permissions=True)


	invoice_name = None


	if float(consultation_fee or 0) > 0:

		invoice_name = _create_paid_consultation_invoice(
			patient,
			consultation_fee,
			appointment.name
		)

		appointment.db_set(
			"consultation_invoice",
			invoice_name
		)

		appointment.db_set(
			"queue_status",
			"Paid - Awaiting Vitals"
		)

	else:

		appointment.db_set(
			"queue_status",
			"Payment Pending"
		)


	return {
		"status": "Success",
		"appointment": appointment.name,
		"invoice": invoice_name,
		"queue_status": appointment.queue_status,
	}



# =============================================
# CONSULTATION INVOICE
# =============================================

def _create_paid_consultation_invoice(
	patient,
	amount,
	appointment_name
):
	"""
	Create paid Sales Invoice for consultation.
	"""

	CONSULTATION_ITEM_CODE = "Consultation"


	patient_doc = frappe.get_doc(
		"Patient",
		patient
	)

	customer = (
		patient_doc.customer
		or patient_doc.name
	)


	default_company = frappe.defaults.get_global_default(
		"company"
	)


	mode_of_payment = (
		frappe.db.get_single_value(
			"Healthcare Settings",
			"default_mode_of_payment"
		)
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


		"items": [
			{
				"item_code": CONSULTATION_ITEM_CODE,
				"qty": 1,
				"rate": float(amount),
			}
		],


		"payments": [
			{
				"mode_of_payment": mode_of_payment,
				"amount": float(amount),
			}
		],


		"remarks":
			f"Consultation fee for Patient Appointment {appointment_name}",

	})


	invoice.insert(
		ignore_permissions=True
	)

	invoice.submit()


	return invoice.name



# =============================================
# QUEUE
# =============================================

@frappe.whitelist()
def get_queue(date=None, queue_status=None):

	date = date or nowdate()

	filters = {
		"appointment_date": date
	}


	if queue_status:
		filters["queue_status"] = queue_status


	return frappe.get_all(
		"Patient Appointment",
		filters=filters,
		fields=[
			"name",
			"patient",
			"patient_name",
			"practitioner",
			"practitioner_name",
			"department",
			"appointment_type",
			"appointment_time",
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
		order_by="appointment_time asc",
	)



# =============================================
# NURSE STATION
# =============================================

@frappe.whitelist()
def send_to_nurse(appointment):

	frappe.db.set_value(
		"Patient Appointment",
		appointment,
		"queue_status",
		"With Nurse"
	)

	return {
		"status": "Success"
	}



@frappe.whitelist()
def save_vitals(
	appointment,
	temperature=None,
	blood_pressure=None,
	pulse=None,
	weight=None,
	height=None,
	notes=None
):

	updates = {

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


	for field, value in updates.items():

		frappe.db.set_value(
			"Patient Appointment",
			appointment,
			field,
			value
		)


	return {
		"status": "Success"
	}



# =============================================
# DOCTOR QUEUE
# =============================================

@frappe.whitelist()
def start_consultation(appointment):

	appt = frappe.get_doc(
		"Patient Appointment",
		appointment
	)


	frappe.db.set_value(
		"Patient Appointment",
		appointment,
		"queue_status",
		"In Consultation"
	)


	return {

		"status": "Success",

		"patient": appt.patient,

		"practitioner": appt.practitioner,

		"appointment": appt.name,

		"department": appt.department,

	}



def on_patient_encounter_submit(doc, method=None):

	"""
	Auto-close queue after encounter submission.
	"""

	if getattr(doc, "appointment", None):

		frappe.db.set_value(
			"Patient Appointment",
			doc.appointment,
			"queue_status",
			"Completed"
		)

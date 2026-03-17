# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import json
from datetime import date

import frappe
from frappe import _
from frappe.query_builder import functions
from frappe.query_builder.terms import ValueWrapper
from datetime import datetime

@frappe.whitelist()
def update_event(args: str, field_map: str):
	"""Updates Event (called via calendar) based on passed `field_map`"""
	args = frappe._dict(json.loads(args))
	field_map = frappe._dict(json.loads(field_map))
	w = frappe.get_doc(args.doctype, args.name)
	w.set(field_map.start, args[field_map.start])
	w.set(field_map.end, args.get(field_map.end))
	w.save()


def get_event_conditions(doctype, filters=None):
	"""Return SQL conditions with user permissions and filters for event queries."""
	from frappe.desk.reportview import get_filters_cond

	if not frappe.has_permission(doctype):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return get_filters_cond(doctype, filters, [], with_match_conditions=True)


@frappe.whitelist()
def get_events(
	doctype: str,
	start: date,
	end: date,
	field_map: str,
	filters: str | None = None,
	fields: str | list[str] | None = None,
):
	field_map = frappe._dict(json.loads(field_map))
	fields = frappe.parse_json(fields)

	doc_meta = frappe.get_meta(doctype)
	for d in doc_meta.fields:
		if d.fieldtype == "Color":
			field_map.update({"color": d.fieldname})

	filters = json.loads(filters) if filters else []

	if not fields:
		fields = [field_map.start, field_map.end, field_map.title, "name"]

	if field_map.color:
		fields.append(field_map.color)

	dt = frappe.qb.DocType(doctype)
	start_field = functions.IfNull(dt[field_map.start], ValueWrapper("0001-01-01 00:00:00"))
	end_field = functions.IfNull(dt[field_map.end], ValueWrapper("2199-12-31 00:00:00"))

	filters += [
		[start_field, "<=", end],
		[end_field, ">=", start],
	]

	fields = list({field for field in fields if field})
	events = frappe.get_list(doctype, fields=fields, filters=filters)

	for event in events:
		start_val = event.get(field_map.start)
		end_val = event.get(field_map.end)

		start_has_time = (
			isinstance(start_val, datetime) and (start_val.hour != 0 or start_val.minute != 0)
		)
		end_has_time = (
			isinstance(end_val, datetime) and (end_val.hour != 0 or end_val.minute != 0)
		)

		event["allDay"] = not (start_has_time or end_has_time)

	return events

# Copyright (c) 2026, Vivek Choudhary and contributors
# For license information, please see license.txt

import csv

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt
from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file


class PLMBOMImportTool(Document):
	pass


@frappe.whitelist()
def import_items(docname):
	doc = frappe.get_doc("PLM BOM Import Tool", docname)
	if not doc.plm_file:
		frappe.throw(_("Please attach a PLM file before creating items."))

	file_doc, extension = get_file(doc.plm_file)
	rows = load_rows(file_doc, extension)

	if not rows or len(rows) < 2:
		frappe.throw(_("No data found in the attached file."))

	header_map = build_header_map(rows[0])
	if "item_code" not in header_map.values():
		frappe.throw(_("Missing required column: Number / Item Code."))

	logs = []
	created = 0
	duplicates = 0
	skipped = 0
	errors = 0

	for row_idx, row in enumerate(rows[1:], start=2):
		if not any(row):
			continue

		row_data = extract_row_data(row, header_map)
		item_code = cstr(row_data.get("item_code")).strip()
		if not item_code:
			logs.append(f"Row {row_idx}: skipped (missing item code).")
			skipped += 1
			continue

		item_group = cstr(row_data.get("item_group")).strip()
		if not item_group:
			logs.append(f"Row {row_idx}: skipped {item_code} (missing part type / item group).")
			skipped += 1
			continue

		try:
			item_group = ensure_item_group(item_group)
		except Exception:
			logs.append(f"Row {row_idx}: failed {item_code} (could not create item group).")
			errors += 1
			continue

		if frappe.db.exists("Item", item_code):
			logs.append(f"Row {row_idx}: duplicate {item_code} (already exists).")
			duplicates += 1
			continue

		try:
			item_doc = frappe.new_doc("Item")
			item_doc.item_code = item_code
			item_doc.item_name = cstr(row_data.get("item_name")).strip() or item_code
			item_doc.item_group = item_group
			item_doc.stock_uom = cstr(row_data.get("stock_uom")).strip() or "Nos"

			if row_data.get("description"):
				item_doc.description = row_data.get("description")
			if row_data.get("gst_hsn_code"):
				item_doc.gst_hsn_code = cstr(row_data.get("gst_hsn_code")).strip()

			item_doc.custom_material = row_data.get("custom_material")
			item_doc.custom_length = flt(row_data.get("custom_length")) if row_data.get("custom_length") else 0
			item_doc.custom_width = flt(row_data.get("custom_width")) if row_data.get("custom_width") else 0
			item_doc.custom_height = flt(row_data.get("custom_height")) if row_data.get("custom_height") else 0
			item_doc.custom_diameter = flt(row_data.get("custom_diameter")) if row_data.get("custom_diameter") else 0
			item_doc.custom_thickness = (
				flt(row_data.get("custom_thickness")) if row_data.get("custom_thickness") else 0
			)
			item_doc.custom_weight = flt(row_data.get("custom_weight")) if row_data.get("custom_weight") else 0

			item_doc.insert(ignore_permissions=True)
			created += 1
			logs.append(f"Row {row_idx}: created {item_code}.")
		except Exception:
			logs.append(f"Row {row_idx}: failed {item_code} (see error log).")
			errors += 1

	summary = (
		f"Created: {created}, Duplicates: {duplicates}, Skipped: {skipped}, Errors: {errors}."
	)
	logs.insert(0, summary)
	doc.item_creation_log = "\n".join(logs)
	doc.save(ignore_permissions=True)

	return {"summary": summary, "log": doc.item_creation_log}


@frappe.whitelist()
def import_bom_creator(docname):
	doc = frappe.get_doc("PLM BOM Import Tool", docname)
	if not doc.plm_file:
		frappe.throw(_("Please attach a PLM file before creating BOM Creator."))

	file_doc, extension = get_file(doc.plm_file)
	rows = load_rows(file_doc, extension)

	if not rows or len(rows) < 2:
		frappe.throw(_("No data found in the attached file."))

	header_map = build_header_map(rows[0])
	if "structure_level" not in header_map.values():
		frappe.throw(_("Missing required column: Structure Level."))
	if "item_code" not in header_map.values():
		frappe.throw(_("Missing required column: Number / Item Code."))

	nodes = []
	for row_idx, row in enumerate(rows[1:], start=2):
		if not any(row):
			continue

		row_data = extract_row_data(row, header_map)
		item_code = cstr(row_data.get("item_code")).strip()
		structure_level = row_data.get("structure_level")
		if structure_level in (None, ""):
			continue
		if not item_code:
			continue

		level = cint(structure_level)
		qty_value = row_data.get("qty")
		qty, qty_uom = parse_qty_and_uom(qty_value)
		uom = cstr(row_data.get("stock_uom")).strip()
		if not uom and qty_uom:
			uom = map_qty_uom(qty_uom) or ""

		nodes.append(
			{
				"row_idx": row_idx,
				"level": level,
				"item_code": item_code,
				"item_name": cstr(row_data.get("item_name")).strip(),
				"item_group": cstr(row_data.get("item_group")).strip(),
				"qty": qty,
				"uom": uom,
			}
		)

	if not nodes:
		frappe.throw(_("No valid rows found in the attached file."))

	min_level = min(node["level"] for node in nodes)
	root = next(node for node in nodes if node["level"] == min_level)
	root_index = nodes.index(root)
	nodes = nodes[root_index:]
	if not frappe.db.exists("Item", root["item_code"]):
		frappe.throw(_("Root item {0} not found. Please create the item first.").format(root["item_code"]))

	logs = []
	company = frappe.defaults.get_user_default("company") or frappe.defaults.get_global_default("company")
	if not company:
		frappe.throw(_("Default company is not set."))

	currency = frappe.get_cached_value("Company", company, "default_currency")
	if not currency:
		frappe.throw(_("Default currency is not set for company {0}.").format(company))

	bom_creator = frappe.new_doc("BOM Creator")
	bom_creator.name = get_unique_bom_creator_name(root["item_code"])
	bom_creator.company = company
	bom_creator.currency = currency
	bom_creator.rm_cost_as_per = "Valuation Rate"
	bom_creator.item_code = root["item_code"]
	bom_creator.qty = normalize_qty(root["qty"])

	if root["item_name"]:
		bom_creator.item_name = root["item_name"]
	if root["item_group"]:
		bom_creator.item_group = root["item_group"]

	if root["uom"]:
		bom_creator.uom = root["uom"]
	else:
		bom_creator.uom = frappe.get_cached_value("Item", root["item_code"], "stock_uom")

	stack = [
		{
			"level": root["level"],
			"item_code": root["item_code"],
			"item_row_no": None,
		}
	]

	created = 0
	skipped = 0
	errors = 0

	for node in nodes[1:]:
		level = node["level"]
		while stack and level <= stack[-1]["level"]:
			stack.pop()

		if not stack:
			logs.append(f"Row {node['row_idx']}: skipped {node['item_code']} (no parent found).")
			skipped += 1
			continue

		if not frappe.db.exists("Item", node["item_code"]):
			logs.append(f"Row {node['row_idx']}: skipped {node['item_code']} (item not found).")
			skipped += 1
			continue

		parent = stack[-1]
		parent_row_no = parent["item_row_no"] if parent["item_row_no"] else ""
		item_uom = node["uom"] or frappe.get_cached_value("Item", node["item_code"], "stock_uom")
		item_qty = normalize_qty(node["qty"])

		try:
			row = bom_creator.append(
				"items",
				{
					"item_code": node["item_code"],
					"item_name": node["item_name"] or None,
					"item_group": node["item_group"] or None,
					"fg_item": parent["item_code"],
					"qty": item_qty,
					"uom": item_uom,
					"stock_uom": item_uom,
					"stock_qty": item_qty,
					"allow_alternative_item": 1,
					"parent_row_no": parent_row_no,
				},
			)
			created += 1
			stack.append(
				{
					"level": level,
					"item_code": node["item_code"],
					"item_row_no": row.idx,
				}
			)
		except Exception:
			logs.append(f"Row {node['row_idx']}: failed {node['item_code']} (see error log).")
			errors += 1

	bom_creator.save(ignore_permissions=True)
	bom_creator.set_rate_for_items()
	bom_creator.save(ignore_permissions=True)
	bom_creator.submit()

	summary = f"Created BOM Creator {bom_creator.name}. Items: {created}, Skipped: {skipped}, Errors: {errors}."
	logs.insert(0, summary)
	doc.bom_creation_log = "\n".join(logs)
	doc.bom_parent_item = bom_creator.name
	doc.save(ignore_permissions=True)

	return {"summary": summary, "log": doc.bom_creation_log, "bom_creator": bom_creator.name}


@frappe.whitelist()
def get_bom_for_bom_creator(bom_creator):
	if not bom_creator:
		return None

	bom_name = frappe.get_value(
		"BOM",
		{"bom_creator": bom_creator, "docstatus": 1},
		"name",
		order_by="creation desc",
	)
	return {"bom": bom_name}


def get_unique_bom_creator_name(base_name):
	base_name = cstr(base_name).strip()
	if not frappe.db.exists("BOM Creator", base_name):
		return base_name

	index = 1
	while True:
		candidate = f"{base_name}-REV{index}"
		if not frappe.db.exists("BOM Creator", candidate):
			return candidate
		index += 1


def get_file(file_name):
	file_doc = frappe.get_doc("File", {"file_url": file_name})
	parts = file_doc.get_extension()
	extension = parts[1].lstrip(".")

	if extension not in ("csv", "xlsx", "xls"):
		frappe.throw(_("Only CSV and Excel files are supported."))

	return file_doc, extension


def load_rows(file_doc, extension):
	if extension == "csv":
		file_path = file_doc.get_full_path()
		with open(file_path, newline="") as in_file:
			return list(csv.reader(in_file))

	content = file_doc.get_content()
	if extension == "xlsx":
		return read_xlsx_file_from_attached_file(fcontent=content)

	return read_xls_file_from_attached_file(content)


def build_header_map(headers):
	aliases = {
		"number": "item_code",
		"item_code": "item_code",
		"code": "item_code",
		"name": "item_name",
		"item_name": "item_name",
		"description": "description",
		"gst_hsn_code": "gst_hsn_code",
		"gst_hsn": "gst_hsn_code",
		"hsn_code": "gst_hsn_code",
		"material": "custom_material",
		"length": "custom_length",
		"width": "custom_width",
		"height": "custom_height",
		"diameter": "custom_diameter",
		"thickness": "custom_thickness",
		"weight": "custom_weight",
		"part_type": "item_group",
		"parttype": "item_group",
		"item_group": "item_group",
		"uom": "stock_uom",
		"stock_uom": "stock_uom",
		"structure_level": "structure_level",
		"level": "structure_level",
		"structurelevel": "structure_level",
		"qty": "qty",
		"quantity": "qty",
	}

	header_map = {}
	for idx, header in enumerate(headers):
		normalized = frappe.scrub(cstr(header))
		if normalized in aliases:
			header_map[idx] = aliases[normalized]

	return header_map


def extract_row_data(row, header_map):
	row_data = {}
	for idx, fieldname in header_map.items():
		if idx >= len(row):
			continue
		value = row[idx]
		if isinstance(value, str):
			value = value.strip()
		row_data[fieldname] = value
	return row_data


def normalize_qty(value):
	qty, _ = parse_qty_and_uom(value)
	return qty if qty > 0 else 1


def parse_qty_and_uom(value):
	uom = ""
	if isinstance(value, str):
		value = value.strip()
		if value:
			parts = value.split()
			value = parts[0]
			if len(parts) > 1:
				uom = parts[1]

	qty = flt(value) if value not in (None, "") else 0
	return (qty if qty > 0 else 1, uom)


def map_qty_uom(uom):
	uom = cstr(uom).strip().lower()
	if uom in ("each", "ea", "nos", "no", "pcs", "pc"):
		return "Nos"
	return ""


def ensure_item_group(item_group):
	if frappe.db.exists("Item Group", item_group):
		return item_group

	group_doc = frappe.new_doc("Item Group")
	group_doc.item_group_name = item_group
	group_doc.parent_item_group = "All Item Groups"
	group_doc.is_group = cint(0)
	group_doc.insert(ignore_permissions=True)
	return group_doc.name

// Copyright (c) 2026, Vivek Choudhary and contributors
// For license information, please see license.txt

frappe.ui.form.on("PLM BOM Import Tool", {
	refresh(frm) {
		toggle_create_buttons(frm);
		add_bom_creator_button_from_parent(frm);
		add_view_bom_button_from_log(frm);
	},
	bom_parent_item(frm) {
		toggle_create_buttons(frm);
	},
	item_create(frm) {
		if (!frm.doc.plm_file) {
			frappe.msgprint(__("Please attach a PLM file before creating items."));
			return;
		}

		frappe.call({
			method:
				"plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.import_items",
			args: {
				docname: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Creating items from PLM file..."),
		}).then((response) => {
			const message = response.message || {};
			if (message.log) {
				frm.set_value("item_creation_log", message.log);
			}
			if (message.summary) {
				frappe.msgprint(message.summary);
			}
			frm.refresh_field("item_creation_log");
		});
	},
	bom_create(frm) {
		if (!frm.doc.plm_file) {
			frappe.msgprint(__("Please attach a PLM file before creating BOM Creator."));
			return;
		}

		frappe.call({
			method:
				"plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.import_bom_creator",
			args: {
				docname: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Creating BOM Creator from PLM file..."),
		}).then((response) => {
			const message = response.message || {};
			if (message.log) {
				frm.set_value("bom_creation_log", message.log);
			}
			if (message.summary) {
				frappe.msgprint(message.summary);
			}
			if (message.bom_creator) {
				add_bom_creator_button(frm, message.bom_creator);
				add_view_bom_button(frm, message.bom_creator);
			} else {
				add_bom_creator_button_from_log(frm);
				add_view_bom_button_from_log(frm);
			}
			frm.refresh_field("bom_creation_log");
		});
	},
});

function toggle_create_buttons(frm) {
	if (frm.doc && frm.doc.bom_parent_item) {
		frm.remove_custom_button(__("Item Create"));
		frm.remove_custom_button(__("BOM Create"));
		frm.toggle_display("item_create", false);
		frm.toggle_display("bom_create", false);
		return;
	}

	frm.toggle_display("item_create", true);
	frm.toggle_display("bom_create", true);
}

function add_bom_creator_button_from_log(frm) {
	if (!frm.doc || !frm.doc.bom_creation_log) {
		return;
	}

	const match = frm.doc.bom_creation_log.match(/BOM Creator\\s+([^\\.\\n]+)/);
	if (match && match[1]) {
		add_bom_creator_button(frm, match[1].trim());
	}
}

function add_bom_creator_button_from_parent(frm) {
	if (!frm.doc || !frm.doc.bom_parent_item) {
		add_bom_creator_button_from_log(frm);
		return;
	}

	add_bom_creator_button(frm, frm.doc.bom_parent_item);
}

function add_view_bom_button_from_log(frm) {
	if (!frm.doc || !frm.doc.bom_creation_log) {
		return;
	}

	const match = frm.doc.bom_creation_log.match(/BOM Creator\\s+([^\\.\\n]+)/);
	if (match && match[1]) {
		add_view_bom_button(frm, match[1].trim());
	}
}

function add_bom_creator_button(frm, bomCreatorName) {
	if (!bomCreatorName) {
		return;
	}

	frm.add_custom_button(__("View BOM Creator"), () => {
		frappe.set_route("Form", "BOM Creator", bomCreatorName);
	});
}

function add_view_bom_button(frm, bomCreatorName) {
	if (!bomCreatorName) {
		return;
	}

	frm.add_custom_button(__("View BOM"), () => {
		frappe.call({
			method:
				"plm_bom.plm_bom.doctype.plm_bom_import_tool.plm_bom_import_tool.get_bom_for_bom_creator",
			args: {
				bom_creator: bomCreatorName,
			},
		}).then((response) => {
			const bom = response.message && response.message.bom;
			if (bom) {
				frappe.set_route("Form", "BOM", bom);
			} else {
				frappe.msgprint(__("BOM not found yet. Please wait and try again."));
			}
		});
	});
}

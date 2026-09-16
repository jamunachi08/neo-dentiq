frappe.ui.form.on("Neo Dentiq Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Reinstall master data"), () => {
			frappe.confirm(
				__("This adds any missing reference data. Existing records are left untouched. Continue?"),
				() => frm.call("run_setup_wizard").then(() =>
					frappe.show_alert({ message: __("Master data installed"),
						indicator: "green" })));
		});
		frm.add_custom_button(__("Install demo clinic"), () => {
			frappe.call({
				method: "neo_dentiq.setup.install_fixtures.install_demo_clinic",
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Demo clinic installed"),
						indicator: "green" });
					frm.reload_doc();
				},
			});
		});
	},
});

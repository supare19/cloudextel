// Copyright (c) 2024, samarth uapre and contributors
// For license information, please see license.txt

frappe.ui.form.on('Task Manager', {
    onload: function (frm) {

        // Set task_owner to the current user's email on load
		if(!frm.doc.task_owner){
			cur_frm.set_value('task_owner', frappe.session.user_email);
		}
		frm.refresh_field("task_owner");
		if (!frm.doc.start_date) {
            frm.set_value('start_date', frappe.datetime.get_today());
        }
    },
    refresh: function (frm) {
        // frm.add_custom_button(__('Custom Button'), function() {
        //     // Your custom button logic here
        //     frappe.msgprint('Custom button clicked!');
        // }, __("Actions"));
      
           // Set task_owner to the current user's email on load
		if(!frm.doc.task_owner){
			cur_frm.set_value('task_owner', frappe.session.user_email);
		}

        // Set a query on the 'next_task_link' field to exclude the current document
        frm.set_query('next_task_link', function () {
            console.log('function is executed', frm.name, frm.docname);
            return {
                filters: {
                    'name': ['not in', [frm.docname]],
                }
            };
        });

        // Refresh the 'next_task_link' field after applying the filter
        frm.refresh_field("next_task_link");
		frm.refresh_field("task_owner");
    },
	before_save: function (frm) {
        // Check if due_date is greater than today's date
        var today = frappe.datetime.get_today();
		console.log(today,(frm.doc.due_date < frm.doc.start_date))
        if (frm.doc.due_date < frm.doc.start_date) {
            frappe.throw('Due Date should not be greater than today.');
        }
    },	
	
});






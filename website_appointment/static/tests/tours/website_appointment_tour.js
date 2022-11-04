odoo.define('website_appointment.website_appointment_tour', function(require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('website_appointment_tour', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="calendar.mail_menu_calendar"]',
        content: 'click on calendar app',
    }, {
        trigger: 'a[data-menu-xmlid="appointment.appointment_type_menu"]',
        content: 'click on Online Appointment',
    }, {
        trigger: '.o-kanban-button-new',
        content: 'click on Create button',
    }, {
        trigger: 'input[name="name"]',
        content: 'set name of appointment type',
    }, {
        trigger: 'input[name="max_schedule_days"]',
        content: 'set max scheduled days',
        run: 'text 45',
    }, {
        trigger: 'div[name="staff_user_ids"] a',
        content: 'add users to the appointment_type',
    }, {
        trigger: '.o_list_record_selector',
        content: 'select users',
    }, {
        trigger: '.o_select_button',
        content: 'save new users for the appointment type',
    }, {
        trigger: 'a:contains("Availability")',
        content: 'go to slots tab',
    }, {
        trigger: 'div[name="slot_ids"] a',
        content: 'click on add a line',
    }, {
        trigger: '.o_form_button_save',
        content: 'save appointment type',
    }, {
        trigger: 'button[name="is_published"]',
        extra_trigger: 'button.o_form_button_create',
        content: 'go to the frontend',
    }, {
        trigger: 'iframe td.o_day:first',
        content: 'click on first date available',
    }, {
        trigger: 'iframe .o_slots_list a:first',
        content: 'click on first slot available',
    }, {
        trigger: 'iframe input[id="phone_field"]',
        content: 'fill tel field',
        run: 'text 0123456789'
    }, {
        trigger: 'iframe button[type="submit"]',
        content: 'confirm appointment',
        run: 'click',
    }, {
        trigger: 'iframe a:contains("Cancel") i',
        content: 'cancel appointment',
        run: 'click',
    }, {
        trigger: '.o_website_edit_in_backend > a',
        content: 'return in backend',
        run: 'click',
    }, {
        trigger: 'button.dropdown-toggle',
        content: 'click on Action dropdown',
        run: 'click',
    }, {
        trigger: 'a:contains("Delete")',
        content: 'delete appointment type',
        run: 'click',
    }, {
        trigger: 'button.btn-primary:contains("Ok")',
        content: 'confirm delete',
        run: 'click',
    }
]);
});

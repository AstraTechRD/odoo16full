/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('timesheet_record_time', {
    test: true,
    url: "/web",
}, [
    {
        trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
        content: "Open Timesheet app.",
        run: "click"
    },
    {
        trigger: '.btn_start_timer',
        content: "Launch the timer to start a new activity.",
        run: "click"
    }, 
    {
        trigger: '.input_description_timer',
        content: "Describe your activity.",
        run: "text Description"
    }, 
    {
        trigger: '.timer_project_id .o_field_many2one',
        content: "Select the project on which you are working.",
        run: function (actions) {
            actions.text("Test Project", this.$anchor.find("input"));
        }
    }, 
    {
        trigger: ".ui-autocomplete > li > a:contains(Test Project)",
        auto: true,
    },
    {
        trigger: '.btn_stop_timer',
        content: "Stop the timer when you are done.",
        run: "click"
    }
]);

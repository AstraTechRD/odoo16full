odoo.define('project_timesheet_synchro.test_screen_navigation', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('activity_creation', {
    test: true,
    url: '/project_timesheet_synchro/timesheet_app',
},
    [
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper"
        },
        {
            content: "Close the menu",
            trigger: '.pt_drawer_menu_wrapper .menu_text:contains(Today)',
            extra_trigger: '.pt_app:has(.pt_drawer_menu_wrapper.shown):has(.pt_btn_start_timer)',
        },
        {
            content: "Start the timer",
            extra_trigger: '.pt_drawer_menu_wrapper:not(.shown)',
            trigger: '.pt_btn_start_timer',
        },
        {
            content: "Stop the timer",
            trigger: '.pt_btn_stop_timer',
        },
        {
            content: "Insert a work summary",
            trigger: 'textarea',
            run: 'text A work summary'
        },
        {
            content: "Open the project selection",
            trigger: '.pt_activity_project .select2-choice',
            run: 'click'
        },
        {
            content: "Enter a project name",
            trigger: '.select2-input',
            run: "text A project Name",
        },
        {
            content: "Create the project",
            trigger: '.select2-result-label:contains("A project Name")',
        },
        {
            content: "Save the activity",
            trigger: '.pt_validate_edit_btn',
            // These next two lines are needed so that when the test-tour is running
            // we wait for the sync to be complete, so as to avoid making an RPC after
            // the chrome cookies have been cleared, because this causes an RPC to be
            // made without a valid session which will count the test as failed (even
            // if the tour succeeded). The run method is required so that this step is
            // not skipped by the test runner (the last step of tours is skipped if it's
            // an automatic action with no run method).
            extra_trigger: '.pt_nav_sync a:not(.pt_sync_in_progress)',
            run: () => {},
        },
    ]
);

tour.register('test_screen_navigation', {
    test: true,
    url: '/project_timesheet_synchro/timesheet_app',
},
    [
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper"
        },
        {
            content: '"Go to screen This week"',
            trigger: '.pt_menu_item:contains("This Week")',
        },
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper"
        },
        {
            content: '"Go to screen Settings"',
            trigger: '.pt_menu_item:contains("Settings")',
        },
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper"
        },
        {
            content: '"Go to screen Day Plan"',
            trigger: '.pt_menu_item:contains("Plan")',
        },
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper",
        },
        {
            content: '"Go to screen Synchronize"',
            trigger: '.pt_menu_item:contains("Synchronize")',
        },
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper",
        },
        {
            content: '"Go to screen Statistics"',
            trigger: '.pt_menu_item:contains("Statistics")',
        },
        {
            content: "Open the menu",
            trigger: '.pt_toggle',
            extra_trigger: ".pt_drawer_menu_wrapper"
        },
        {
            // This step is needed so that when the test-tour is running
            // we wait for the sync to be complete, so as to avoid making an RPC after
            // the chrome cookies have been cleared, because this causes an RPC to be
            // made without a valid session which will count the test as failed (even
            // if the tour succeeded). The run method is required so that this step is
            // not skipped by the test runner (the last step of tours is skipped if it's
            // an automatic action with no run method).
            content: "Dummy step",
            trigger: 'body',
            extra_trigger: '.pt_nav_sync a:not(.pt_sync_in_progress)',
            run: () => {},
        },
    ]
);

});
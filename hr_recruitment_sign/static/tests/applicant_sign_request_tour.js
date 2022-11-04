odoo.define('hr_recruitment_sign.tour', function (require) {
    'use strict';

    var Tour = require('web_tour.tour');

    Tour.register('applicant_sign_request_tour', {
            test: true,
            url: '/web',
        },[
            {
                content: "Access on the recruitment app",
                trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
                run: 'click',
            },
            {
                content: "Go on applications",
                trigger: '.dropdown-toggle[title="Applications"]',
                run: 'click',
            },
            {
                content: "Go on all applications",
                trigger: 'a[data-menu-xmlid="hr_recruitment.menu_crm_case_categ_all_app"]',
                run: 'click',
            },
            {
                content: "Open Saitama's application",
                trigger: '.o_data_cell[data-tooltip="Saitama"]',
                run: 'click',
            },
            {
                content: "Create an employee",
                trigger: '.btn[name="create_employee_from_applicant"]',
                run: 'click',
            },
            {
                content: "Validate the creation",
                trigger: '.btn.o_form_button_save',
                extra_trigger: '.o_employee_form',
                run: 'click',
            },
            {
                content: "Validate the creation",
                trigger: '.o_menu_brand',
                extra_trigger: '.o_form_status_indicator_buttons.invisible',
                run: 'click',
            },
        ]
    );
});

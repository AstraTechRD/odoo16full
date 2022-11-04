/** @odoo-module **/

import tour from 'web_tour.tour';
import '@hr_payroll/../tests/tours/dashboard_tour';

const DashboardTour = tour.tours.payroll_dashboard_ui_tour;
const setHrReponsibleStepIndex = _.findIndex(DashboardTour.steps, function (step) {
    return (step.id === 'set_hr_responsible');
});

DashboardTour.steps.splice(setHrReponsibleStepIndex + 1, 0, {
    /**
     * Add some steps upon creating the contract as new fields are added and are required
     * with the hr_contract_salary module.
     */
    content: "Set Contract Template",
    trigger: 'div.o_field_widget.o_field_many2one[name="sign_template_id"] div input',
    run: 'text Employment',
}, {
    content: "Select Contract Template",
    trigger: '.ui-menu-item a:contains("Employment")',
});

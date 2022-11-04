/** @odoo-module **/

/**
 * Adapt the step that is specific to the work details when the `worksheet` module is not installed.
 */

import tour from 'web_tour.tour';
import 'industry_fsm.tour';

const signReportStepIndex = tour.tours.industry_fsm_tour.steps.findIndex(step => step.id === 'sign_report');

tour.tours.industry_fsm_tour.steps.splice(signReportStepIndex, 0, {
    trigger: 'div[name="worksheet_map"] h5#task_worksheet',
    extra_trigger: '.o_project_portal_sidebar',
    content: ('"Worksheet" section is rendered'),
    auto: true,
}, {
    trigger: 'div[name="worksheet_map"] div[class*="row"] div:not(:empty)',
    extra_trigger: '.o_project_portal_sidebar',
    content: ('At least a field is rendered'),
    auto: true,
});

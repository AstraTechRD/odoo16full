/** @odoo-module **/

import tour from 'web_tour.tour';

const planningTestTour = tour.tours.planning_test_tour
const projectPlanningStartStepIndex = planningTestTour.steps.findIndex((step) => step.id && step.id === 'project_planning_start');

planningTestTour.steps.splice(projectPlanningStartStepIndex + 1, 0, {
    trigger: ".o_field_many2one[name='project_id'] input",
    content: "Create project named-'New Project' for this shift",
    run: "text New Project",
}, {
    trigger: "ul.ui-autocomplete a:contains(New Project)",
    auto: true,
    in_modal: false,
});

const projectPlanningEndStepIndex = planningTestTour.steps.findIndex((step) => step.id && step.id === 'planning_check_format_step');

planningTestTour.steps.splice(projectPlanningEndStepIndex + 1, 0, {
    trigger: ".o_gantt_button_add",
    content: "Click Add record to verify the naming format of planning template",
},
{
    trigger: "span.o_selection_badge:contains('[New Project]')",
    content: "Check the naming format of planning template",
    run() {}
},
{
    content: "exit the shift modal",
    trigger: "button[special=cancel]",
    in_modal: true,
    auto: true,
},
{
    content: 'wait for the modal to be removed',
    // the dialog container has an empty div child, and the actual modal gets
    // added afterwards, so we can check by asserting the nature of the last
    // child
    trigger: ".o_dialog_container > :last-child:not([role=dialog])",
    auto: true,
    run() {},
});

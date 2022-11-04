/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('planning_test_tour', {
    url: '/web',
    test: true,
}, [{
    trigger: '.o_app[data-menu-xmlid="planning.planning_menu_root"]',
    content: "Let's start managing your employees' schedule!",
    position: 'bottom',
}, {
    trigger: ".o_gantt_button_add",
    content: "Let's create your first <b>shift</b> by clicking on Add. <i>Tip: use the (+) shortcut available on each cell of the Gantt view to save time.</i>",
    id: 'project_planning_start',
}, {
    trigger: ".o_field_widget[name='resource_id'] input",
    content: "Assign this shift to your <b>resource</b>, or leave it open for the moment.",
    run: 'text Thibault',
}, {
    trigger: ".o-autocomplete--dropdown-item > a:contains('Thibault')",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_widget[name='role_id'] input",
    content: "Select the <b>role</b> your employee will have (<i>e.g. Chef, Bartender, Waiter, etc.</i>).",
    run: 'text Developer',
}, {
    trigger: ".o-autocomplete--dropdown-item > a:contains('Developer')",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_widget[name='start_datetime'] input",
    content: "Set start datetime",
    run: function (actions) {
        const input = this.$anchor[0];
        input.value = input.value.replace(/(\d{2}:){2}\d{2}/g, '08:00:00');
        input.dispatchEvent(new InputEvent('input', {
            bubbles: true,
        }));
        input.dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
}, {
    trigger: ".o_field_widget[name='end_datetime'] input",
    content: "Set end datetime",
    run: function (actions) {
        const input = this.$anchor[0];
        input.value = input.value.replace(/(\d{2}:){2}\d{2}/g, '11:59:59');
        input.dispatchEvent(new InputEvent('input', {
            bubbles: true,
        }));
        input.dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
}, {
    trigger: "div[name='template_creation'] input",
    content: "Save this shift as a template",
    run: function (actions) {
        if (!this.$anchor.prop('checked')) {
            actions.click(this.$anchor);
        }
    },
}, {
    trigger: "button[special='save']",
    content: "Save this shift once it is ready.",
}, {
    trigger: ".o_gantt_pill :contains('11:59 AM')",
    content: "<b>Drag & drop</b> your shift to reschedule it. <i>Tip: hit CTRL (or Cmd) to duplicate it instead.</i> <b>Adjust the size</b> of the shift to modify its period.",
    auto: true,
    run: function () {
        if (this.$anchor.length) {
            const expected = "8:00 AM - 11:59 AM (4h)";
            const actual = this.$anchor[0].textContent;
            if (!actual.startsWith(expected)) {
                console.error("Test in gantt view doesn't start as expected. Expected : '" + expected + "', actual : '" + actual + "'");
            }
        } else {
            console.error("Not able to select pill ending at 11h59");
        }
    }
}, {
    trigger: ".o_gantt_button_send_all",
    content: "If you are happy with your planning, you can now <b>send</b> it to your employees.",
}, {
    trigger: "button[name='action_check_emails']",
    content: "<b>Publish & send</b> your planning to make it available to your employees.",
}, {
    trigger: ".o_gantt_progressbar",
    content: "See employee progress bar",
    auto: true,
    run: function () {
        const $progressbar = $(".o_gantt_progressbar:eq(0)");
        if ($progressbar.length) {
            if ($progressbar[0].style.width === '') {
                console.error("Progress bar should be displayed");
            }
            if (!$progressbar[0].classList.contains("o_gantt_group_success")) {
                console.error("Progress bar should be displayed in success");
            }
        } else {
            console.error("Not able to select progressbar");
        }
    }
}, {
    trigger: ".o_gantt_button_copy_previous_week",
    content: "Copy previous week if you want to follow previous week planning schedule",
    run: 'click',
}, {
    id: "planning_check_format_step",
    trigger: ".o_gantt_pill p:contains(Developer)",
    content: "Check naming format of resource and role when grouped",
    auto: true,
    run: function () {}
}]);

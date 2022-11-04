/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
const { Component, useState, useEffect, useEnv, onWillStart, mount, xml, useRef } = owl;

export class TimeOffToDeferWarning extends Component {
    setup() {
        this.actionService = useService("action");
    }
    onTimeOffToDefer() {
        this.actionService.doAction("hr_payroll_holidays.hr_leave_action_open_to_defer");
    }
};

// inline template is used as the component is dynamically loaded
TimeOffToDeferWarning.template = xml`
    <div class="alert alert-warning text-center mb-0" role="alert">
        <p class="mb-0">
            You have some <button class="btn btn-link p-0 o_open_defer_time_off" role="button" t-on-click="onTimeOffToDefer">time off</button> to defer to the next month.
        </p>
    </div>
`;

export function useTimeOffToDefer(selector, position) {
    const orm = useService("orm");
    const rootRef = useRef("root");
    const env = useEnv();
    const state = useState({
        hasTimeOffToDefer: false
    });
    onWillStart(async () => {
        const result = await orm.search('hr.leave', [["payslip_state", "=", "blocked"]]);
        state.hasTimeOffToDefer = result.length !== 0;
    });
    useEffect((el) => {
        if (!el) {
          return;
        }
        const attachElement = el.querySelector(selector);
        mount(TimeOffToDeferWarning, attachElement, {
            position,
            env
        });
      },
      () => [state.hasTimeOffToDefer && rootRef.el]
    )
}

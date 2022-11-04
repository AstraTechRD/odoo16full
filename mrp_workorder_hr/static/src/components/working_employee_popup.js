/** @odoo-module **/

import { MrpTimer } from "@mrp/widgets/timer";
import { useService } from "@web/core/utils/hooks";
import time from 'web.time';

const { Component, onWillStart } = owl;

export class WorkingEmployeePopup extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.workorderId = this.props.popupData.workorderId;

        onWillStart(() => this._getState())
    }

    addEmployee() {
        this.props.onAddEmployee();
        this.close();
    }

    lockEmployee(employeeId) {
        this.startEmployee(employeeId);
        this.props.onLockEmployee(employeeId);
        this.close();
    }

    async stopEmployee(employeeId) {
        this.props.onStopEmployee(employeeId);
        this.lines.map(l => {
            if (l.employee_id === employeeId) {
                l.ongoing = false;
            }
        });
        this.render();
    }

    startEmployee(employeeId) {
        this.props.onStartEmployee(employeeId);
        this.lines.map(l => {
            if (l.employee_id === employeeId) {
                l.ongoing = true;
            }
        });
        this.render();
    }

    close() {
        this.props.onClosePopup('WorkingEmployeePopup', true);
    }

   async _getState() {
        const productivityLines = await this.orm.call('mrp.workcenter.productivity', 'read_group', [
            [
                ['workorder_id', '=', this.workorderId],
                ['employee_id', '!=', false],
            ],
            ['duration', 'date_start:array_agg', 'date_end:array_agg'],
            ['employee_id']
        ]);
        this.lines = productivityLines.map((pl) => {
            let duration = pl.duration * 60;
            const ongoingTimerIndex = pl.date_end.indexOf(null);
            if ( ongoingTimerIndex != -1 ){
                const additionalDuration = moment(new Date()).diff(moment(time.auto_str_to_date(pl.date_start[ongoingTimerIndex])), 'seconds');
                duration += additionalDuration;
            }
            return {
                'employee_id': pl.employee_id[0],
                'employee_name': pl.employee_id[1],
                'duration': duration,
                'ongoing': pl.date_end.some(d => !d),
            }
        })
   }
}

WorkingEmployeePopup.components = { MrpTimer };
WorkingEmployeePopup.template = 'mrp_workorder_hr.WorkingEmployeePopup';

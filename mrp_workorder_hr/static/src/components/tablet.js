/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import Tablet from '@mrp_workorder/components/tablet';
import { SelectionPopup } from '@mrp_workorder_hr/components/popup';
import { WorkingEmployeePopup } from '@mrp_workorder_hr/components/working_employee_popup';
import { patch } from 'web.utils';
import { PinPopup } from '@mrp_workorder_hr/components/pin_popup';

const { onMounted } = owl;

patch(Tablet.prototype, 'mrp_workorder_hr', {
    setup() {
        this._super();
        this.notification = useService("notification");
        this.popup.SelectionPopup = {
            isShown: false,
            data: {},
        };
        this.popup.PinPopup = {
            isShown: false,
            data: {},
        };
        this.popup.WorkingEmployeePopup = {
            isShown: false,
            data: {},
        };
        this.state.tabletEmployeeIds = [];
        this.employee = this.props.action.context.employee_id;
        this.actionRedirect = false;
        useBus(this.workorderBus, "popupEmployeeManagement", this.popupEmployeeManagement);
        onMounted(() => this.checkEmployeeLogged());
    },

    checkEmployeeLogged() {
        if (this.data.employee_list.length && !this.data.employee && !this.employee) {
            this.popupAddEmployee();
        }
    },
    // Popup Menu Actions

    popupEmployeeManagement() {
        this.showPopup({ workorderId: this.workorderId }, 'WorkingEmployeePopup');
    },

    popupAddEmployee() {
        const list = this.data.employee_list.filter(e => ! this.data.employee_ids.includes(e.id)).map((employee) => {
            return {
                id: employee.id,
                item: employee,
                label: employee.name,
                isSelected: false,
            };
        });
        const title = this.env._t('Change Worker');
        this.showPopup({ title, list }, 'SelectionPopup');
    },

    popupEmployeePin(employeeId) {
        const employee = this.data.employee_list.find(e => e.id === employeeId);
        this.showPopup({ employee }, 'PinPopup');
    },

    // Buisness method

    async lockEmployee(employeeId, pin) {
        const pinValid = await this._checkPin(employeeId, pin);
        if (! pinValid) {
            this.actionRedirect = this.lockEmployee;
            return;
        }
        this.render();
    },

    async startEmployee(employeeId, pin) {
        const pinValid = await this._checkPin(employeeId, pin);
        if (! pinValid) {
            this.actionRedirect = this.startEmployee;
            return;
        }
        this.state.tabletEmployeeIds.push(employeeId);
        await this.orm.call(
            'mrp.workorder',
            'start_employee',
            [this.workorderId, employeeId],
        );
        await this.getState();
        this.render();
    },

    async stopEmployee(employeeId, pin) {
        const pinValid = await this._checkPin(employeeId, pin, false);
        if (! pinValid) {
            this.actionRedirect = this.stopEmployee;
            return;
        }
        const index = this.state.tabletEmployeeIds.indexOf(employeeId);
        this.state.tabletEmployeeIds.slice(index, 1);
        await this.orm.call(
            'mrp.workorder',
            'stop_employee',
            [this.workorderId, employeeId],
        );
        await this.getState();
        this.render();
    },

    redirectToAction(employeeId, pin) {
        this.actionRedirect(employeeId, pin);
        this.actionRedirect = false;
    },

    get isBlocked() {
        let isBlocked = this._super();
        if (this.data.employee_list.length !== 0 && ! this.data.employee_id) {
            isBlocked = true;
        }
        return isBlocked;
    },

    // Private

    async _checkPin(employeeId, pin, sessionSave = true) {
        const pinValid = await this.orm.call('hr.employee', 'login', [employeeId, pin, sessionSave]);
        if (!pinValid) {
            this.popupEmployeePin(employeeId);
            return;
        }
        return true;
    },

    _onBarcodeScanned(barcode) {
        const employee = this.data.employee_list.find(e => e.barcode === barcode);
        if (employee) {
            this.startEmployee(employee.id);
        } else {
            return this._super(barcode);
        }
    },

    async _onWillStart() {
        const superMethod = this._super;
        const employeeId = this.props.action.context.employee_id;
        if (employeeId) {
            await this.startEmployee(employeeId);
        }
        await superMethod();
        if (employeeId) {
            await this.getState();
        }
    },
});

Tablet.components.SelectionPopup = SelectionPopup;
Tablet.components.PinPopup = PinPopup;
Tablet.components.WorkingEmployeePopup = WorkingEmployeePopup;

/** @odoo-module */

import { SelectionPopup } from '@mrp_workorder_hr/components/popup';
import { PinPopup } from '@mrp_workorder_hr/components/pin_popup';
import { useBus, useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import {MrpWorkorderKanbanController} from '@mrp_workorder/views/kanban/mrp_workorder_kanban_controller';

const {onWillStart, useState, onMounted} = owl;

MrpWorkorderKanbanController.components.SelectionPopup = SelectionPopup;
MrpWorkorderKanbanController.components.PinPopup = PinPopup;

patch(MrpWorkorderKanbanController.prototype, 'mrp_workorder_hr', {
    setup() {
        this._super();
        this.popup = useState({
            PinPopup: {
                isShown: false,
                data: {},
            },
            SelectionPopup: {
                isShown: false,
                data: {},
            }
        });
        this.notification = useService('notification');
        this.barcode = useService("barcode");
        useBus(this.barcode.bus, 'barcode_scanned', (event) => this._onBarcodeScanned(event.detail.barcode));
        this.workcenterId = this.props.context.default_workcenter_id;
        this.workcenter = false;
        this.employee = useState({
            name: false || this.props.context.employee_name,
            id: 0 || this.props.context.employee_id,
        });
        onWillStart(async () => {
            await this.onWillStart();
        });
        onMounted(() => {
             this.onMount();
        });
    },

    async onWillStart() {
        if (!this.workcenterId) {
            return;
        }
        const workcenter = await this.orm.read(
            "mrp.workcenter", [this.workcenterId], ['allow_employee', 'employee_ids']
        );
        this.workcenter = workcenter[0];
        if (!this.workcenter.allow_employee) {
            return;
        }
        const fieldsToRead = ['id', 'name', 'barcode'];
        const employees_domain = [];
        if (this.workcenter.employee_ids.length) {
            employees_domain.push(['id', 'in', this.workcenter.employee_ids]);
        }
        this.employees = await this.orm.searchRead(
             "hr.employee", employees_domain, fieldsToRead,
        );
    },

    onMount() {
        if (this.employeeId) {
            this.selectEmployee(this.employeeId);
        }
    },

    // destroy: function () {
    //     core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
    //     this._super();
    // },

    openEmployeeSelection() {
        const employeeList = this.employees.map(employee => Object.create({
            id: employee.id,
            item: employee,
            label: employee.name,
            isSelected: employee === this.employee.id,
        }));
        this.popup.SelectionPopup = {
            data: { title: this.env._t('Select Employee'), list: employeeList },
            isShown: true,
        };
    },

    async selectEmployee(employeeId, pin) {
        const employee = this.employees.find(e => e.id === employeeId);
        const employee_function = this.employee.name && this.employee.id === employeeId ? 'logout' : 'login';
        const pinValid = await this.orm.call(
            "hr.employee", employee_function, [employeeId, pin],
        );
        if (!pinValid && this.popup.PinPopup.isShown) {
            this.notification.add(this.env._t('Wrong password !'), {type: 'danger'});
            return;
        }
        if (!pinValid) {
            this._askPin(employee);
            return;
        }

        if (employee_function === 'login') {
            this.notification.add(this.env._t('Logged in!'), {type: 'success'});
            this.employee = {
                name: employee.name,
                id: employee.id,
            };
            if (this.context.openRecord) {
                this.openRecord(...this.context.openRecord);

            }
        } else {
            this.employee = {
                name: false,
                id: 0,
            };
        }
    },

    closePopup(popupName) {
        this.popup[popupName].isShown = false;
    },

    _askPin(employee) {
        this.popup.PinPopup = {
            data: {employee: employee},
            isShown: true,
        };
    },

    _onBarcodeScanned(barcode) {
        const employee = this.employees.find(e => e.barcode === barcode);
        if (employee) {
            this.selectEmployee(employee.id);
        } else {
            this.notification.add(this.env._t('This employee is not allowed on this workcenter'), {type: 'danger'});
        }
    },

    async openRecord(record, mode) {
        if (this.employees && !this.employee.name) {
            this.context.openRecord = [record, mode];
            this.openEmployeeSelection();
            return;
        }
        delete this.context.openRecord;
        Object.assign(this.context, {employee_id: this.employee.id});
        this._super(...arguments);
    },
});

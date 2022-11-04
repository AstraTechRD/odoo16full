/** @odoo-module **/

import { ComponentAdapter } from 'web.OwlCompatibility';
import { FieldBinaryFile } from 'web.basic_fields';

import { patch } from "@web/core/utils/patch";

import { PayrollDashboardPayslipBatch } from '@hr_payroll/components/dashboard/payslip_batch/payslip_batch';

export class PayrollDashboardPayslipBatchAdapter extends ComponentAdapter {
    /**
     * @override
     */
    setup() {
        // FieldBinaryFile requires getSession which requires the legacy environment.
        super.setup();
        this.env = owl.Component.env;
    }
}


patch(PayrollDashboardPayslipBatch.prototype, 'payroll_sepa', {
    /**
     * @override
     */
    setup() {
        this._super.apply(this, arguments);
        this.FieldBinaryFile = FieldBinaryFile;
    },

    /**
     * @returns {boolean} Whether any batch has a sepa export to display
     */
    _hasSepaExport() {
        return this.props.batches.find(elem => elem.sepa_export);
    },

    /**
     * Creates a fake record with the necessary data.
     *
     * @param batchData data from hr.payslip.run
     * @returns a fake record with the necessary data to render the widget
     */
    _generateRecord(batchData) {
        return {
            id: batchData.id,
            res_id: batchData.id,
            model: 'hr.payslip.run',
            data: {
                id: batchData.id,
                sepa_export: batchData.sepa_export,
                sepa_export_filename: 'SEPA',
            },
            fields: {
                sepa_export: {string: '', type: 'binary'},
                sepa_export_filename: {string: '', type: 'char'},
            },
            fieldsInfo: {
                default: {
                    sepa_export: {
                        filename: 'sepa_export_filename',
                    },
                },
            }
        };
    },
});

PayrollDashboardPayslipBatch.components = Object.assign({}, PayrollDashboardPayslipBatch.components, {PayrollDashboardPayslipBatchAdapter});

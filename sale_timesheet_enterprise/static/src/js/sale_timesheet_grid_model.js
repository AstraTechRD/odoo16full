/** @odoo-module */

import { patch } from 'web.utils';
import CommonTimesheetGridModel from 'timesheet_grid.CommonTimesheetGridModel';

patch(CommonTimesheetGridModel.prototype, 'sale_timesheet_enterprise.CommonTimesheetGridModel', {

    /**
     * @override
     */
    async __load(params) {
        const result = await this._super(...arguments);
        this._gridData.solHoursData = await this.fetchWorkingHoursData(this._getGridValues('so_line'), 'sale.order.line');
        return result;
    },

    /**
     * @override
     */
    async __reload(handle, params) {
        const result = await this._super(...arguments);
        this._gridData.solHoursData = await this.fetchWorkingHoursData(this._getGridValues('so_line'), 'sale.order.line');
        return result;
    },
});

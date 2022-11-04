odoo.define('timesheet_grid.GroupByNoDateMixin', function (require) {
    "use strict";

    const { _t } = require('web.core');

    const GroupByNoDateMixin = {

        /**
         * Retrieve the start and end date of the currently displayed range.
         * So, start of week / month and end of week / month.
         * The data is retrieved that way to avoid problems of localization where the start of the week may be a
         * different day (Sunday or Monday or ... )
         *
         * @returns {{start: string, end: string}}
         */

        _getTimeContext() {
            const anchor_date = moment(this.context.grid_anchor);
            const range = this.currentRange.name;
            return {
                start: anchor_date.startOf(range).format('YYYY-MM-DD'),
                end: anchor_date.endOf(range).format('YYYY-MM-DD'),
            }
        },

        // -------------------------------------------------------------------------
        // Private
        // -------------------------------------------------------------------------

        /**
         * Ensures that no date field is present in the group_by of the view and returns the
         * sanitized group_by.
         * @param {Object} params The params passed to the caller function.
         * @param {string} groupByPropName The name of the property name in params which provides the
         *                         group_by applied in the view.
         * @returns {Object} The sanitized params.
         * @private
         */
        _manageGroupBy(params, groupByPropName) {
            if (params && groupByPropName in params) {
                const groupBy = params[groupByPropName]
                const filteredGroupBy = groupBy.filter(filter => {
                    return filter.split(':').length === 1;
                });
                if (filteredGroupBy.length !== groupBy.length) {
                    this.displayNotification({ message: _t('Grouping by date is not supported'), type: 'danger' });
                }
                params[groupByPropName] = filteredGroupBy;
            }
            return params;
        },
        /**
         * @override
         */
        async __load(params) {
            params = this._manageGroupBy(params, 'groupedBy');
            await this._super(params);
            this._gridData.timeBoundariesContext = this._getTimeContext();
        },
        /**
         * @override
         */
        async __reload(handle, params) {
            params = this._manageGroupBy(params, 'groupBy');
            await this._super(handle, params);
            this._gridData.timeBoundariesContext = this._getTimeContext();
        },
    }

    return GroupByNoDateMixin;
});

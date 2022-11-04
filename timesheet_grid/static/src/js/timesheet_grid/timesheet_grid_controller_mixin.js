odoo.define('timesheet_grid.TimesheetGridControllerMixin', function (require) {
'use strict';

const core = require('web.core');
const { parse } = require("web.field_utils");
const { serializeDate } = require("@web/core/l10n/dates");

const qWeb = core.qweb;

const { markup } = owl;

const _t = core._t;

const TimesheetGridControllerMixin = {

    /**
     * display notification if the timesheet is created/updated outside the period displayed in the Grid View.
     *
     * @private
     * @param {Object} grid_data
     */
    _onDialogSaved(grid_data) {
        // convert analyticLineDate from luxon to moment
        const analyticLineDate = parse.date(serializeDate(grid_data.data.date), null, { isUTC: true });
        const state = this.model.get();
        const startDate = moment(state.timeBoundariesContext.start);
        const endDate = moment(state.timeBoundariesContext.end);
        if (!analyticLineDate.isBetween(startDate, endDate)) {
            this.displayNotification({
                type: "success",
                message: _t('The timesheet entry has successfully been created.'),
            });
        } else {
            this.reload();
        }
    },

    /**
     * @private
     * @override
     */
    _getFormDialogOptions() {
        let result = this._super(...arguments);
        result.onRecordSaved = this._onDialogSaved.bind(this);
        return result;
    },

    /**
     * @override
     */
    _getFormContext() {
        const formContext = this._super();
        const state = this.model.get();
        const cols = state.data && state.data.length > 0 ? state.data[0].cols : [];
        let firstWorkingDayCol = null;
        for (const col of cols) {
            if (col.is_current) {
                firstWorkingDayCol = null;
                break;
            } else if (!firstWorkingDayCol && !col.is_unavailable) {
                firstWorkingDayCol = col;
            }
        }
        const defaultColField = `default_${state.colField}`;
        if (firstWorkingDayCol && defaultColField in formContext) {
            // then we can assume the col field type is either a date or datetime since is_unavailable field is only available in thoses types.
            formContext[defaultColField] = firstWorkingDayCol.values[state.colField][0].split('/')[0];
        }
        return formContext;
    },

    /**
     * @override
     */
    _getEventAction(label, cell, ctx) {
        var action = this._super(label, cell, ctx);
        action.help = markup(qWeb.render('timesheet_grid.detailActionHelp'));
        return action;
    },

    _cellHasBeenUpdated(ev) {
        this.update({ onlyHoursData: true });
    },
};

return TimesheetGridControllerMixin;

});

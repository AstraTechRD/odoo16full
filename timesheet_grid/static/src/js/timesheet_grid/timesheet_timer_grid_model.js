odoo.define('timesheet_grid.TimerGridModel', function (require) {
    "use strict";

    const CommonTimesheetGridModel = require('timesheet_grid.CommonTimesheetGridModel');

    const TimerGridModel = CommonTimesheetGridModel.extend({
        /**
         * Update state
         *
         * When the user click on a timer button, we need to update the state without reordering the data.
         */
        async actionTimer(state) {
            await this.reload();

            let i = 0;

            const array = [];

            while (state.data.hasOwnProperty(i)) {
                array.push(state.data[i]);
                i += 1;
            }

            i = 0;

            // Get fields containing in rowFields without the sectionField
            const fields = _.difference(this.rowFields, [this.sectionField]);

            while (this._gridData.data.hasOwnProperty(i)) {
                array.some((el, index) => {
                    if (_.isEqual(el.__label, this._gridData.data[i].__label)) {
                        state.data[index].cols = this._gridData.data[i].cols;
                        if (this._checkRowsSameOrder(state.data[index].rows, this._gridData.data[i].rows, fields)) {
                            // Then same order
                            state.data[index].grid = this._gridData.data[i].grid;
                            state.data[index].rows = this._gridData.data[i].rows;
                        } else {
                            // Update state with the same order than the old state
                            const {rows, grid} = this._updateGrid(
                                {rows: state.data[index].rows, grid: state.data[index].grid},
                                {rows: this._gridData.data[i].rows, grid: this._gridData.data[i].grid},
                                fields
                            );

                            state.data[index].rows = rows;
                            state.data[index].grid = grid;
                        }

                        return true;
                    }
                });

                i += 1;
            }
            if (this._gridData.serverTime) {
                state.serverTime = this._gridData.serverTime;
            }
            this._gridData = state;
            this._gridData.data.forEach((group, groupIndex) => {
                this._gridData.data[groupIndex].totals = this._computeTotals(group.grid);
            });
            this._gridData.totals = this._computeTotals(_.flatten(_.pluck(this._gridData.data, 'grid'), true));
            return this._gridData;
        },

        // -------------------------------------------------------------------------
        // Private
        // -------------------------------------------------------------------------

        /**
         * @override
         */
        async __load() {
            await this._super(...arguments);
            await this._getTimerData();
        },
        _changeTimerDescription(timesheetId, description) {
            this._rpc({
                model: 'account.analytic.line',
                method: 'change_description',
                args: [[timesheetId], description],
            });
        },
        _addTimeTimer(timesheetId, time) {
            this._rpc({
                model: 'account.analytic.line',
                method: 'action_add_time_to_timer',
                args: [[timesheetId], time],
            });
        },
        async _stopTimer(timesheetId) {
            await this._rpc({
                model: 'account.analytic.line',
                method: 'action_timer_stop',
                args: [timesheetId, true],
            });
        },
        _unlinkTimer(timesheetId) {
            this._rpc({
                model: 'account.analytic.line',
                method: 'action_timer_unlink',
                args: [[timesheetId]],
            });
        },
        async _getTimerData() {
            const result = await this._rpc({
                model: 'account.analytic.line',
                method: 'get_timer_data',
                args: [],
            });
            this._gridData.stepTimer = result['step_timer'];
            this._gridData.defaultProject = result['favorite_project'];
        },
        /**
         * Check if the "rows" of 2 states (old and new) contains theirs elements in the same order
         * @param {Array} a contains rows of oldState
         * @param {Array} b contains rows of newState
         * @param {Array} fields contains rowFields of grid view without the sectionField
         */
        _checkRowsSameOrder(a, b, fields) {
            if (a.length !== b.length) {
                return false;
            }

            for (let i = 0; i < a.length; i++) {
                for (const field of fields) {
                    if (a[i].values[field] === false && b[i].values[field] !== false) {
                        return false;
                    }
                    if (_.difference(a[i].values[field], b[i].values[field]).length !== 0) {
                        return false;
                    }
                }
            }

            return true;
        },
        /**
         * We want to update the state when the user clicks on the timer button, but we want to keep
         * the same order that the oldState.
         *
         * @param {Array} a contains rows and grid of oldState
         * @param {Array} b contains rows and grid of newState
         * @param {Array} fields contains rowFields of grid view without the sectionField
         */
        _updateGrid(a, b, fields) {
            const result = {rows: [], grid: []};

            let i = 0;
            for (i = 0; i < a.rows.length; i++) {
                b.rows.some((row, index) => {
                    for (const field of fields) {
                        if (a.rows[i].values[field] === false && row.values[field] !== false) {
                            return false;
                        }
                        if (_.difference(a.rows[i].values[field], row.values[field]).length !== 0) {
                            return false;
                        }
                    }
                    result.rows.push(row);
                    result.grid.push(b.grid[index]);
                    return true;
                });
            }

            if (i < b.rows.length) {
                for (i; i < b.rows.length; i++) {
                    result.rows.push(b.rows[i]);
                    result.grid.push(b.grid[i]);
                }
            }

            return result;
        },
    });

    return TimerGridModel;
});

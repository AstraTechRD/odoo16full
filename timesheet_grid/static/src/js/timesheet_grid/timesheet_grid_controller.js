odoo.define('timesheet_grid.GridController', function (require) {
    "use strict";

    const GridController = require('web_grid.GridController');
    const TimesheetGridControllerMixin = require('timesheet_grid.TimesheetGridControllerMixin');

    const TimesheetGridController = GridController.extend(TimesheetGridControllerMixin, {

        /**
         * @override
         */
        renderButtons($node) {
            this._super(...arguments);
            this.$buttons.on('click', '.o_timesheet_validate', this._onValidateButtonClicked.bind(this));
        },

        /**
         * @override
         */
        updateButtons() {
            this._super(...arguments);
            this.$buttons.find('.o_timesheet_validate').removeClass('grid_arrow_button');
        },

        // -------------------------------------------------------------------------
        // Private
        // -------------------------------------------------------------------------

        _onValidateButtonClicked(e) {
            e.stopPropagation();

            return this.mutex.exec(async () => {
                const ids = await this.model.getIds();
                const res = await this._rpc({
                    model: 'account.analytic.line',
                    method: 'action_validate_timesheet',
                    args: [ids],
                });
                this.displayNotification({type: res.params.type, title: res.params.title});
                await this.model.reload();
                var state = this.model.get();
                await this.renderer.update(state);
                this.updateButtons(state);
            });
        },
    });


    return TimesheetGridController;
});

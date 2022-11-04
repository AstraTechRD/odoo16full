odoo.define('thimesheet_grid.timesheet_uom_timer', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
const fieldUtils = require('web.field_utils');
const TimesheetUom = require('hr_timesheet.timesheet_uom');
const { _lt } = require('web.core');
const { registry } = require("@web/core/registry");
const Timer = require('timer.Timer');

const TimesheetUomDisplayTimer = TimesheetUom.FieldTimesheetTime.extend({
    /**
     * Refresh the Widget content so that it shows the timer elapsed time.
     *
     * @private
     */
    _refreshTime() {
        if (this.$el.children().length) {
            this.$el.contents()[1].replaceWith(this.time.toString());
        } else {
            this.$el.text(this.time.toString());
        }
    },
    /**
     * Display the timer elapsed time.
     *
     * @private
     */
    _startTimeCounter() {
        // Check if the timer_start exists and it's not false
        // In other word, when user clicks on play button, this button
        if (this.recordData.timer_start && !this.recordData.timer_pause && !this.rendererIsSample) {
            this.time = Timer.createTimer(this.recordData.unit_amount, this.recordData.timer_start, this.serverTime);
            if (this.time) {
                this.$el.addClass('fw-bold text-danger');
                this._refreshTime();
                this.timer = setInterval(() => {
                    this.time = Timer.createTimer(this.recordData.unit_amount, this.recordData.timer_start, this.serverTime);
                    this._refreshTime();
                }, 1000);
            } else {
                clearTimeout(this.timer);
                this.$el.removeClass('fw-bold text-danger');
            }
        }
    },
    /**
     * @override
     */
    async _render() {
        await this._super.apply(this, arguments);
        this._startTimeCounter();
    },
});

/**
 * Extend float time widget to add the using of a timer for duration
 * (unit_amount) field.
 */
const FieldTimesheetTimeTimer = TimesheetUomDisplayTimer.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.isTimerRunning = this.record.data.is_timer_running;
        this.rendererIsSample = arguments[0].state.isSample; // This only works with list_views.
    },

    willstart() {
        const timePromise = this._rpc({
            model: 'timer.timer',
            method: 'get_server_time',
            args: []
        }).then((time) => {
            this.serverTime = time;
        });
        return Promise.all([
            this._super(...arguments),
            timePromise,
        ]);
    },

    _render: async function () {
        await this._super.apply(this, arguments);
        const my_timesheets = this.record.getContext().my_timesheet_display_timer;
        const display_timer = this.record.data.display_timer;
        if (my_timesheets && display_timer && this.record.viewType === 'list') {
            const title = this.isTimerRunning ? _lt('Stop') : _lt('Play');
            const name = this.isTimerRunning ? 'action_timer_stop' : 'action_timer_start';
            const label = this.isTimerRunning ? _lt('Stop') : _lt('Start');

            const button = $('<button>', {
                'class': 'o_icon_button o-timer-button mr8',
                'title': title,
                'name': name,
                'aria-label': label,
                'aria-pressed': this.isTimerRunning,
                'type': 'button',
                'role': 'button',
            });
            button.html('<i/>');
            button.find('i')
                .addClass('fa')
                .toggleClass('fa-stop-circle o-timer-stop-button text-danger', this.isTimerRunning)
                .toggleClass('fa-play-circle o-timer-play-button text-primary', !this.isTimerRunning)
                .attr('title', title);
            button.on('click', this._onToggleButton.bind(this));
            this.$el.prepend(button);
        }
    },

    _onToggleButton: async function (event) {
        const context = this.record.getContext();
        event.stopPropagation();
        await this._rpc({
            model: this.model,
            method: this._getActionButton(),
            context: context,
            args: [this.res_id]
        });

        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                'is_timer_running': !this.isTimerRunning,
            },
        });
        this.trigger_up('timer_changed', {
            id: this.res_id,
            is_timer_running: !this.isTimerRunning
        });
    },

    _getActionButton: function () {
        return this.isTimerRunning ? 'action_timer_stop' : 'action_timer_start';
    },

    /**
     * @override
     */
    destroy: function () {
        clearTimeout(this.timer);
        this._super.apply(this, arguments);
    },
});

const timesheetUomTimerService = {
    dependencies: ["timesheet_uom"],
    start(env, { timesheet_uom }) {
        /**
         * Binding depending on Company Preference
         *
         * determine wich widget will be the timesheet one.
         * Simply match the 'timesheet_uom' widget key with the correct
         * implementation (float_time, float_toggle, ...). The default
         * value will be 'float_factor'.
        **/
        const widgetName = timesheet_uom.widget || 'float_factor';

        let FieldTimesheetUom = null;

        if (widgetName === 'float_toggle') {
            FieldTimesheetUom = TimesheetUom.FieldTimesheetToggle;
        } else if (widgetName === 'float_time') {
            FieldTimesheetUom = FieldTimesheetTimeTimer;
        } else {
            FieldTimesheetUom = (
                    fieldRegistry.get(widgetName) &&
                    fieldRegistry.get(widgetName).extend({ })
                ) || TimesheetUom.FieldTimesheetFactor;
        }
        fieldRegistry.add('timesheet_uom_timer', FieldTimesheetUom);

        // bind the formatter and parser method, and tweak the options
        const _tweak_options = (options) => {
            if (!_.contains(options, 'factor')) {
                options.factor = timesheet_uom.factor;
            }
            return options;
        };

        fieldUtils.format.timesheet_uom_timer = function(value, field, options) {
            options = _tweak_options(options || { });
            const formatter = fieldUtils.format[FieldTimesheetUom.prototype.formatType];
            return formatter(value, field, options);
        };

        fieldUtils.parse.timesheet_uom_timer = function(value, field, options) {
            options = _tweak_options(options || { });
            const parser = fieldUtils.parse[FieldTimesheetUom.prototype.formatType];
            return parser(value, field, options);
        };
    },
};

registry.category("services").add("timesheet_uom_timer", timesheetUomTimerService);

/**
 * Extend Time widget to add the +/- button for duration
 * (duration_unit_amount) field.
 */
const FieldTimesheetHours = TimesheetUomDisplayTimer.extend({
    /**
     * @override
     */
    async _render() {
        await this._super.apply(this, arguments);
        const $timer = this.getParent().el.querySelector('.o_kanban_timer_start');
        $timer.before(this._makeButton(_lt('Decrease Time'), 'action_timer_decrease', 'fa-minus'));
        $timer.after(this._makeButton(_lt('Increase Time'), 'action_timer_increase', 'fa-plus'));
    },
    /**
     * @private
     * @param {String} title
     * @param {String} name
     * @param {String} icon
     */
    _makeButton(title, name, icon) {
        const button = document.createElement('button');
        button.className = 'btn btn-light btn-sm fa ' + icon;
        button.title = title;
        button.name = name;
        button.type = 'button';
        button.addEventListener('click', this._onToggleButton.bind(this));
        return button;
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    async _onToggleButton(ev) {
        ev.stopPropagation();
        await this._rpc({
            model: this.model,
            method: ev.currentTarget.name,
            args: [this.res_id]
        });
        this.trigger_up('reload');
    },
});

return {
    FieldTimesheetHours,
    FieldTimesheetTimeTimer,
    timesheetUomTimerService,
};

});

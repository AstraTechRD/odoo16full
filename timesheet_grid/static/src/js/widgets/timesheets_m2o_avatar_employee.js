/** @odoo-module alias=timesheet_grid.TimesheetM2OAvatarEmployee **/
import field_utils from 'web.field_utils';
import StandaloneM2OAvatarEmployee from '@hr/js/standalone_m2o_avatar_employee';
import { qweb, _lt } from 'web.core';

    /**
     * Widget that add hours to be performed next to the avatar name.
     * It's displayed in red if all hours for the currently displayed time period have not been timesheeted AND
     * and time period is in the past. Otherwise, it's red.
     */
    const TimesheetM2OAvatarEmployee = StandaloneM2OAvatarEmployee.extend({

        $className: '.o_grid_section_subtext',
        hoursTemplate: 'timesheet_grid.Many2OneAvatarHoursSubfield',
        title: _lt('Difference between the number of hours recorded and the number of hours the employee was supposed to work according to his contract.'),

        init(parent, value, rowIndex, rangeContext, timeBoundariesContext, workingHoursData) {
            this._super(...arguments);

            this.elementIndex = rowIndex;
            this.rangeContext = rangeContext;
            this.timeContext = timeBoundariesContext;

            this.hasAllTheRequiredData = true;

            if (workingHoursData) {
                this.cacheHours = workingHoursData['units_to_work'];
                this.cacheUnit = workingHoursData['uom'];
                this.cacheWorkedHours = workingHoursData['worked_hours'];
                if (this.cacheUnit === 'days') {
                    this.title = _lt('Difference between the number of days recorded and the number of days the employee was supposed to work according to his contract.');
                }
            } else {
                this.hasAllTheRequiredData = false;
                console.error("For some reason, the working hours of the employee couldn't be loaded...");
            }
        },

        start() {
            if (this.hasAllTheRequiredData) {
                this._updateTemplateFromCacheData();
                this._renderHoursFromCache(true);
            }

            return this._super(...arguments);
        },

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        async update(data) {
            let shouldAttachFreshTemplate = false;

            if (data.value[0] !== this.value[0]) {
                this.value = data.value;
                await this.avatarWidget.reinitialize(data.value);
                shouldAttachFreshTemplate = true;
            }

            this.rangeContext = data.rangeContext;
            this.timeContext = data.timeBoundariesContext;

            if (data.workingHoursData) {
                this.cacheHours = data.workingHoursData['units_to_work'];
                this.cacheUnit = data.workingHoursData['uom'];
                this.cacheWorkedHours = data.workingHoursData['worked_hours'];

                this._updateTemplateFromCacheData();
                this._renderHoursFromCache(shouldAttachFreshTemplate);
            } else {
                console.error("For some reason, the working hours of the employee couldn't be loaded...");
            }
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Renders the widget.
         *
         * @param {bool} attachNewTemplate should a new template be attached and not replaced ?
         */
        _renderHoursFromCache(attachNewTemplate = false) {
            if (attachNewTemplate) {
                this.avatarWidget.$el.find('.o_m2o_avatar').append(this.$templateHtml);
            } else {
                this.avatarWidget.$el.find(this.$className).replaceWith(this.$templateHtml);
            }
        },

        /**
         * @returns boolean should show the hours line in red ?
         */
        _shouldShowHoursInRed() {
            return (this.cacheWorkedHours < this.cacheHours) && (moment(this.timeContext.end) < moment());
        },

        /**
         * @returns boolean should show the hours line
         */
        _shouldShowHours() {
            return this.cacheWorkedHours !== undefined && this.cacheWorkedHours != null && this.cacheHours >= 0 && this.cacheWorkedHours - this.cacheHours != 0 && moment(this.timeContext.end) < moment();
        },

        _displayOvertimeIndication() {
            if (!this._shouldShowHours()) {
                return null;
            }
            const overtime = this.cacheWorkedHours - this.cacheHours;
            let overtimeIndication = overtime > 0 ? '+' : '';
            if (this.cacheUnit === 'days') { // format in days
                overtimeIndication += `${(Math.round(overtime * 100) / 100).toFixed(2)}`;
            } else { // format in hours
                overtimeIndication += field_utils.format.float_time(this.cacheWorkedHours - this.cacheHours);
            }

            return overtimeIndication;
        },

        /**
         * Generate (qweb render) the template from the attribute values.
         */
        _updateTemplateFromCacheData() {
            this.$templateHtml = $(qweb._render(this.hoursTemplate, {
                'overtime_indication': this._displayOvertimeIndication(),
                'unit': this.cacheUnit,
                'range': this.rangeContext,
                'not_enough_hours': this._shouldShowHoursInRed(),
                'title': this.title,
            }));
        },

    });

export default TimesheetM2OAvatarEmployee;

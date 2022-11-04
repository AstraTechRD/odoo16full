/** @odoo-module alias=timesheet_grid.TimesheetM2OWidget **/
import field_utils from 'web.field_utils';
import Widget from 'web.Widget';
import StandaloneFieldManagerMixin from 'web.StandaloneFieldManagerMixin';
import { FieldMany2One } from "web.relational_fields";
import { qweb, _lt } from 'web.core';

/**
 * Widget that add hours to be performed next to the label.
 * It is not displayed if there is no allocated hours.
 * It is displayed in :
 * green if progression <= 80%
 * orange if 80% < progression <= 99%
 * red otherwise
 */

const TimesheetM2OWidget = Widget.extend(StandaloneFieldManagerMixin, {
    $className: '.o_grid_section_subtext',
    className:'o_standalone_timesheets_m2o_widget d-inline-flex',
    hoursTemplate: 'timesheet_grid.Many2OneTimesheetSubfield',
    title: _lt('Difference between the time allocated and the time recorded.'),

    /**
     * @constructor
     */
    init(parent, value, rowIndex, workingHoursData) {
        this._super.apply(this, parent, this.modelName, value);
        StandaloneFieldManagerMixin.init.call(this);
        this.value = value;
        this.widget = undefined;

        this.elementIndex = rowIndex;
        this.hasAllTheRequiredData = true;

        if (workingHoursData) {
            this.cacheHours = workingHoursData.planned_hours
            this.cacheUnit = workingHoursData.uom;
            this.cacheWorkedHours = workingHoursData.worked_hours;
        } else {
            this.cacheUnit = 'hour';
            this.hasAllTheRequiredData = false;
            console.error("For some reason, the data couldn't be loaded...");
        }
    },
    /**
     * @override
     */
    async willStart() {
        await this._super.apply(this, arguments);
        await this._createM2OWidget();
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
            await this.widget.reinitialize(data.value);
            shouldAttachFreshTemplate = true;
        }

        if (data.workingHoursData) {
            this.cacheHours = data.workingHoursData.planned_hours;
            this.cacheUnit = data.workingHoursData.uom;
            this.cacheWorkedHours = data.workingHoursData.worked_hours;

            this._updateTemplateFromCacheData();
            this._renderHoursFromCache(shouldAttachFreshTemplate);
        } else {
            console.error("For some reason, the data couldn't be loaded...");
        }
    },

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------
    _createM2OWidget: async function () {
        const recordID = await this.model.makeRecord(this.modelName, [
            {
                name: this.fieldName,
                relation: this.modelName,
                type: "many2one",
                value: this.value,
            },
        ]);
        this.widget = new FieldMany2One(this, this.fieldName, this.model.get(recordID), {
            attrs: {
                can_create: false,
                can_write: false,
                options: { no_open: true },
                ...this.attrs,
            },
        });
        this._registerWidget(recordID, this.modelName, this.widget);
    },

    /**
     * Renders the widget.
     *
     * @param {bool} attachNewTemplate should a new template be attached and not replaced ?
     */
    _renderHoursFromCache(attachNewTemplate = false) {
        if (!attachNewTemplate) {
            this.$el.empty();
        }
        this.$el.append(this.$templateHtml);
    },

    /**
     * @returns boolean should show the hours line
     */
    _shouldShowHours() {
        return this.cacheHours > 0;
    },

    /**
     * @returns string color of the hours
     */
    _getColorClass() {
        if (!this._shouldShowHours()) return '';

        let progression = this.cacheWorkedHours / this.cacheHours;
        return progression <= 0.8
                ? 'o_grid_section_subtext_overtime text-success'
                : progression <= 0.99
                    ? 'o_grid_section_subtext_warning text-warning'
                    : 'o_grid_section_subtext_not_enough_hours text-danger';
    },

    _displayOvertimeIndication() {
        if (!this._shouldShowHours()) return null;

        const overtime = this.cacheHours - this.cacheWorkedHours;
        let overtimeIndication = overtime > 0 ? '+' : '';
        if (this.cacheUnit === 'days') { // format in days
            overtimeIndication += `${(Math.round(overtime * 100) / 100).toFixed(2)}`;
        } else { // format in hours
            overtimeIndication += field_utils.format.float_time(overtime);
        }

        return overtimeIndication;
    },

    /**
     * Generate (qweb render) the template from the attribute values.
     */
    _updateTemplateFromCacheData() {
        this.$templateHtml = $(qweb._render(this.hoursTemplate, {
            'value': this.value[1],
            'overtime_indication': this._displayOvertimeIndication(),
            'unit': this.cacheUnit,
            'color_class': this._getColorClass(),
            'title': this.title,
        }));
    },
});

export default TimesheetM2OWidget;

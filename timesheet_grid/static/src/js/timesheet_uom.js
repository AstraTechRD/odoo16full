odoo.define('timesheet_grid.timesheet_uom', function (require) {
    'use strict';

    const gridComponentRegistry = require('web_grid.component_registry');
    const gridComponent = require('web_grid.components');
    const session = require('web.session');
    const { registry } = require("@web/core/registry");

    const TimesheetUOMMultiCompanyMixin = (component) => class extends component {
        setup() {
            super.setup();
            owl.onWillStart(() => {
                const currentCompanyId = session.user_context.allowed_company_ids[0];
                const currentCompany = session.user_companies.allowed_companies[currentCompanyId];
                this.currentCompanyTimesheetUOMFactor = currentCompany.timesheet_uom_factor || 1;
            });
        }
    };
    /**
     * Extend the float toggle widget to set default value for timesheet
     * use case. The 'range' is different from the default one of the
     * native widget, and the 'factor' is forced to be the UoM timesheet
     * conversion.
     **/
    class FloatFactorComponentTimesheet extends TimesheetUOMMultiCompanyMixin(gridComponent.FloatFactorComponent) {
        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------
        /**
         * Returns the additional options pass to the format function.
         *
         * @returns {Object}
         */
        get fieldOptions() {
            const fieldOptions = Object.assign({}, this.props.nodeOptions);
            // force factor in format and parse options
            fieldOptions.factor = this.currentCompanyTimesheetUOMFactor;
            return fieldOptions;
        }
    }
    class FloatToggleComponentTimesheet extends TimesheetUOMMultiCompanyMixin(gridComponent.FloatToggleComponent) {
        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------
        /**
         * Returns the additional options pass to the format function.
         *
         * @returns {Object}
         */
        get fieldOptions() {
            const fieldOptions = Object.assign({}, this.props.nodeOptions);
            // force factor in format and parse options
            fieldOptions.factor = this.currentCompanyTimesheetUOMFactor;
            const hasRange = Object.keys(this.props.nodeOptions || {}).includes('range');
            // the range can be customized by setting the
            // option on the field in the view arch
            if (!hasRange) {
                fieldOptions.range = [0.00, 0.50, 1.00];
            }
            return fieldOptions;
        }
    }

    const timesheetUomGridService = {
        dependencies: ["timesheet_uom"],
        start(env, { timesheet_uom }) {
            const widgetName = timesheet_uom.widget || 'float_factor';

            /**
             * Binding depending on Company Preference
             *
             * determine which component will be the timesheet one.
             * Simply match the 'timesheet_uom' component key with the correct
             * implementation (float_time, float_toggle, ...). The default
             * value will be 'float_factor'.
             **/

            let FieldTimesheetUom;
            if (widgetName === "float_toggle") {
                FieldTimesheetUom = FloatToggleComponentTimesheet;
            } else if (widgetName === "float_factor") {
                FieldTimesheetUom = FloatFactorComponentTimesheet;
            } else {
                FieldTimesheetUom = (gridComponentRegistry.get(widgetName) || FloatFactorComponentTimesheet);
            }
            gridComponentRegistry.add('timesheet_uom', FieldTimesheetUom);
        },
    };
    registry.category("services").add("timesheet_uom_grid", timesheetUomGridService);

return {
    FloatFactorComponentTimesheet,
    FloatToggleComponentTimesheet,
    timesheetUomGridService,
};

});

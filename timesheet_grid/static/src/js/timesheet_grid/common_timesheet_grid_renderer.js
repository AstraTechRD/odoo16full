/** @odoo-module alias=timesheet_grid.CommonTimesheetGridRenderer */

import { ComponentAdapter } from 'web.OwlCompatibility';
import GridRenderer from 'web_grid.GridRenderer';
import TimesheetM2OTask from 'timesheet_grid.TimesheetM2OTask';
import TimesheetM2OProject from 'timesheet_grid.TimesheetM2OProject';

class CommonTimesheetGridRenderer extends GridRenderer {
    setup() {
        super.setup();
        this.widgetComponents = {
            TimesheetM2OTask: TimesheetM2OTask,
            TimesheetM2OProject: TimesheetM2OProject,
        };
        this.widgetFieldNames = ['task_id', 'project_id'];
    }

    showWidget(field) {
        const fieldIdGroupIndex = this.props.groupBy.indexOf(field);
        if (fieldIdGroupIndex < 0) return false;

        if (this.props.isGrouped) {
            const isGroupLabel = this.rowlabel_index === undefined;
            const isGroupLabelThisField = isGroupLabel && fieldIdGroupIndex === 0;
            const isLabelThisField = !isGroupLabel && fieldIdGroupIndex === this.label_index + 1;
            return isGroupLabelThisField || isLabelThisField;
        }
        
        return fieldIdGroupIndex === this.label_index;
    };

    get widgetToShow() {
        for (const fieldName of this.widgetFieldNames) {
            if (this.showWidget(fieldName)) return fieldName;
        }
        return false;
    };
};

class TimesheetM2OWidgetAdapter extends ComponentAdapter {

    /**
     * @override
     */
    async updateWidget(nextProps) {
        await this.widget.update(nextProps);
    }

    /**
     * @override
     */
    get widgetArgs() {
        return [this.props.value, this.props.rowIndex, this.props.workingHoursData];
    }

    renderWidget() {}
}

CommonTimesheetGridRenderer.components = {
    TimesheetM2OWidgetAdapter,
};

CommonTimesheetGridRenderer.props = Object.assign({}, GridRenderer.props, {
    taskHoursData: {
        type: Object,
        optional: true,
    },
    projectHoursData: {
        type: Object,
        optional: true,
    },
});

export default CommonTimesheetGridRenderer;

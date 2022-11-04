/** @odoo-module alias=timesheet_grid.CommonTimesheetGridModel */

import GridModel from 'web_grid.GridModel';
import GroupByNoDateMixin from 'timesheet_grid.GroupByNoDateMixin';


const CommonTimesheetGridModel = GridModel.extend(GroupByNoDateMixin).extend({

    /**
     * @override
     */
    async __load(params) {
        const result = await this._super(...arguments);
        this._gridData.taskHoursData = await this.fetchWorkingHoursData(this._getGridValues('task_id'), 'project.task');
        this._gridData.projectHoursData = await this.fetchWorkingHoursData(this._getGridValues('project_id'), 'project.project');
        return result;
    },

    /**
     * @override
     */
    async __reload(handle, params) {
        const result = await this._super(...arguments);
        this._gridData.taskHoursData = await this.fetchWorkingHoursData(this._getGridValues('task_id'), 'project.task');
        this._gridData.projectHoursData = await this.fetchWorkingHoursData(this._getGridValues('project_id'), 'project.project');
        return result;
    },

    /**
     * Retrieves from the grid data about the specified field.
     * This data is useful for the widgets timesheet avatar's/task's rpc.
     *
     * It needs to pay attention that depending on the way the grid is grouped or not,
     * the data is not at the same place and at the same format.
     *
     * @returns [ { id, display_name, grid_row_index }, ... ]
     */
    _getGridValues(field) {
        const gridValues = [];

        if (this._gridData.isGrouped && this._gridData.groupBy[0] === field) {
            for (const [index, row] of this._gridData.data.entries()) {
                if (row.__label) {
                    gridValues.push({
                        'id': row.__label[0],
                        'display_name': row.__label[1],
                        'grid_row_index': index,
                    });
                }
            }
        } else {
            for (const datum of this._gridData.data) {
                for (const [index, row] of datum.rows.entries()) {
                    if (field in row.values) {
                        gridValues.push({
                            'id': row.values[field][0],
                            'display_name': row.values[field][1],
                            'grid_row_index': index,
                        });
                    }
                }
            }
        }

        return gridValues;
    },

    async fetchWorkingHoursData(gridData, model) {
        if (!gridData.length) return {};

        const workingHoursData = await this._rpc({
            model: model,
            method: 'get_planned_and_worked_hours',
            args: [gridData],
        });

        return workingHoursData;
    },
})

export default CommonTimesheetGridModel;

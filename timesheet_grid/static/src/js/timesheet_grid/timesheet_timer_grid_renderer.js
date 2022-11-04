odoo.define('timesheet_grid.TimerGridRenderer', function (require) {
    "use strict";

    const utils = require('web.utils');
    const CommonTimesheetGridRenderer = require('timesheet_grid.CommonTimesheetGridRenderer');
    const TimerHeaderComponent = require('timesheet_grid.TimerHeaderComponent');
    const TimerStartComponent = require('timesheet_grid.TimerStartComponent');
    const { useListener } = require("@web/core/utils/hooks");

    const { EventBus, onMounted, onWillUpdateProps, useState, useExternalListener } = owl;

    class TimerGridRenderer extends CommonTimesheetGridRenderer {
        setup() {
            super.setup();
            useExternalListener(window, 'keydown', this._onKeydown);
            useExternalListener(window, 'keyup', this._onKeyup);

            this._bus = new EventBus;
            this.initialGridAnchor = this.props.context.grid_anchor;
            this.initialGroupBy = this.props.groupBy;
            this.hoveredButton = false;

            this.stateTimer = useState({
                taskId: undefined,
                taskName: '',
                projectId: undefined,
                projectName: '',
                addTimeMode: false,
                description: '',
                startSeconds: 0,
                timerRunning: false,
                indexRunning: -1,
                indexHovered: -1,
                readOnly: false,
                projectWarning: false,
            });
            this.timesheetId = false;
            this._onChangeProjectTaskDebounce = _.debounce(this._setProjectTask.bind(this), 500);
            useListener('mouseover', '.o_grid_view', this._onMouseOver);
            useListener('mouseout', '.o_grid_view', this._onMouseOut);

            onMounted(() => {
                if (this.formatType === 'float_time') {
                    this._get_running_timer();
                }
            });

            onWillUpdateProps(async (nextProps) => {
                if (nextProps.data !== this.props.data) {
                    this._match_line(nextProps.data);
                }
            });
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * @returns {boolean} returns true if when we need to display the timer button
         *
         */
        get showTimerButton() {
            return ((this.formatType === 'float_time') && (
                this.props.groupBy.includes('project_id')
            ));
        }
        /**
         * @returns {boolean} returns always true if timesheet in hours, that way we know we're on a timesheet grid and
         * we can show the timer header.
         *
         */
        get showTimer() {
            return this.formatType === 'float_time';
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _match_line(new_grid) {
            const grid = (new_grid) ? new_grid[0].rows : this.props.data[0].rows;
            let current_value;
            for (let i = 0; i < grid.length; i++) {
                current_value = grid[i].values;
                if (current_value.project_id && current_value.project_id[0] === this.stateTimer.projectId
                    && ((!current_value.task_id && !this.stateTimer.taskId) ||
                    (current_value.task_id && current_value.task_id[0] === this.stateTimer.taskId))) {
                    this.stateTimer.indexRunning = i;
                    return;
                }
            }
            this.stateTimer.indexRunning = -1;
        }
        async _get_running_timer() {
            const result = await this.rpc({
                model: 'account.analytic.line',
                method: 'get_running_timer',
                args: []
            });
            if (result.id !== undefined) {
                this.stateTimer.timerRunning = true;
                this.timesheetId = result.id;
                this.stateTimer.readOnly = result.readonly;
                this.stateTimer.projectId = result.project_id;
                this.stateTimer.taskId = result.task_id || undefined;

                // In case of read-only timer
                this.stateTimer.projectName = (result.project_name) ? result.project_name : '';
                this.stateTimer.taskName = (result.task_name) ? result.task_name : '';

                this.stateTimer.timerRunning = true;
                this.stateTimer.description = (result.description === '/') ? '' : result.description;
                this.stateTimer.startSeconds = Math.floor(Date.now() / 1000) - result.start;
            } else if (this.stateTimer.timerRunning && this.stateTimer.projectId) {
                this.timesheetId = false;
                this.stateTimer.readOnly = false;
                this.stateTimer.projectId = false;
                this.stateTimer.taskId = undefined;

                this.stateTimer.timerRunning = false;
                this.stateTimer.description = '';
            }
            this._bus.trigger("TIMESHEET_TIMER:focusStartButton");
            this._match_line();
        }
        async _onSetProject(data) {
            this.stateTimer.projectId = data.detail.projectId;
            this.stateTimer.taskId = undefined;
            this._onChangeProjectTaskDebounce(data.detail.projectId, undefined);
        }
        async _onSetTask(data) {
            this.stateTimer.projectId = data.detail.projectId;
            this.stateTimer.taskId = data.detail.taskId || undefined;
            this._onChangeProjectTaskDebounce(this.stateTimer.projectId, data.detail.taskId);
        }
        async _setProjectTask(projectId, taskId) {
            if (!this.stateTimer.projectId) {
                return;
            }
            if (this.timesheetId) {
                const timesheetId = await this.rpc({
                    model: 'account.analytic.line',
                    method: 'action_change_project_task',
                    args: [[this.timesheetId], this.stateTimer.projectId, this.stateTimer.taskId],
                });
                if (this.timesheetId !== timesheetId) {
                    this.timesheetId = timesheetId;
                    await this._get_running_timer();
                }
            } else {
                const seconds = Math.floor(Date.now() / 1000) - this.stateTimer.startSeconds;
                this.timesheetId = await this.rpc({
                    model: 'account.analytic.line',
                    method: 'create',
                    args: [{
                        'name': this.stateTimer.description,
                        'project_id': this.stateTimer.projectId,
                        'task_id': this.stateTimer.taskId,
                    }],
                });
                // Add already runned time and start timer if doesn't running yet in DB
                this.trigger('add_time_timer', {
                    timesheetId: this.timesheetId,
                    time: seconds
                });
            }
            this._match_line();
        }
        async _onClickLineButton(taskId, projectId) {
            // Check that we can create timers for the selected project.
            // This is an edge case in multi-company environment.
            const canStartTimerResult = await this.rpc({
                model: 'project.project',
                method: 'check_can_start_timer',
                args: [[projectId]],
            });
            if (canStartTimerResult !== true) {
                this.trigger('do_action', {action: canStartTimerResult})
                return;
            }
            if (this.stateTimer.addTimeMode === true) {
                this.timesheetId = await this.rpc({
                    model: 'account.analytic.line',
                    method: 'action_add_time_to_timesheet',
                    args: [[this.timesheetId], projectId, taskId, this.props.stepTimer * 60],
                });
                this.trigger('update_timer');
            } else if (! this.timesheetId && this.stateTimer.timerRunning) {
                this.stateTimer.projectId = projectId;
                this.stateTimer.taskId = (taskId) ? taskId : undefined;
                await this._onChangeProjectTaskDebounce(projectId, taskId);
            } else {
                if (this.stateTimer.projectId === projectId && this.stateTimer.taskId === taskId) {
                    await this._stop_timer();
                    return;
                }
                await this._stop_timer();
                this.stateTimer.projectId = projectId;
                this.stateTimer.taskId = (taskId) ? taskId : undefined;
                await this._onTimerStarted();
                await this._onChangeProjectTaskDebounce(projectId, taskId);
            }
            this._bus.trigger("TIMESHEET_TIMER:focusStopButton");
        }
        async _onTimerStarted() {
            this.stateTimer.timerRunning = true;
            this.stateTimer.addTimeMode = false;
            this.stateTimer.startSeconds = Math.floor(Date.now() / 1000);
            if (this.props.defaultProject && ! this.stateTimer.projectId) {
                this.stateTimer.projectId = this.props.defaultProject;
                this._onChangeProjectTaskDebounce(this.props.defaultProject, undefined);
            }
        }
        async _stop_timer() {
            if (!this.timesheetId) {
                this.stateTimer.projectWarning = true;
                return;
            }
            let timesheetId = this.timesheetId;
            this.timesheetId = false;
            this.trigger('stop_timer', {
                timesheetId: timesheetId,
            });
            this.stateTimer.description = '';
            this.stateTimer.timerRunning = false;
            this.timesheetId = false;
            this.stateTimer.projectId = undefined;
            this.stateTimer.taskId = undefined;

            this.stateTimer.timerRunning = false;
            this.stateTimer.projectWarning = false;

            this._match_line();
            this.stateTimer.readOnly = false;
        }
        async _onTimerUnlink() {
            if (this.timesheetId !== false) {
                this.trigger('unlink_timer', {
                    timesheetId: this.timesheetId,
                });
            }
            this.timesheetId = false;
            this.stateTimer.projectId = undefined;
            this.stateTimer.taskId = undefined;

            this.stateTimer.timerRunning = false;
            this.stateTimer.description = '';
            this.stateTimer.manualTimeInput = false;
            this._match_line();
            this.stateTimer.readOnly = false;
            this.stateTimer.projectWarning = false;
        }
        _onNewDescription(data) {
            this.stateTimer.description = data.detail;
            if (this.timesheetId) {
                this.trigger('update_timer_description', {
                    timesheetId: this.timesheetId,
                    description: data.detail
                });
            }
        }
        async _onNewTimerValue(data) {
            const seconds = Math.floor(Date.now() / 1000) - this.stateTimer.startSeconds;
            const toAdd = data.detail * 3600 - seconds;
            this.stateTimer.startSeconds = this.stateTimer.startSeconds - toAdd;
            if (this.timesheetId && typeof toAdd === 'number') {
                this.trigger('add_time_timer', {
                    timesheetId: this.timesheetId,
                    time: toAdd
                });
            }
            this._bus.trigger("TIMESHEET_TIMER:focusStopButton");
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        async _onClickStartTimerFromLine(ev) {
            if (! ev.detail) {
                return;
            }
            const cell_path = ev.detail.split('.');
            const grid_path = cell_path.slice(0, -2);
            const row_path = grid_path.concat(['rows'], cell_path.slice(-1));
            const row = utils.into(this.props.data, row_path);
            const data = row.values;
            const task = (data.task_id) ? data.task_id[0] : undefined;
            this._onClickLineButton(task, data.project_id[0]);
        }
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        async _onKeydown(ev) {
            if (ev.key === 'Shift' && !this.stateTimer.timerRunning && !this.state.editMode) {
                this.stateTimer.addTimeMode = true;
            } else if (!ev.altKey && !ev.ctrlKey && !ev.metaKey && this.showTimerButton && ! (['input', 'textarea'].includes(ev.target.tagName.toLowerCase()) || ev.target.className.toLowerCase().includes('note'))) {
                if (ev.key === 'Escape' && this.stateTimer.timerRunning) {
                    this._onTimerUnlink();
                }
                const index = ev.keyCode - 65;
                if (index >= 0 && index <= 26 && index < this.props.data[0].rows.length) {
                    const data = this.props.data[0].rows[index].values;
                    const projectId = data.project_id[0];
                    const taskId = data.task_id && data.task_id[0];
                    this._onClickLineButton(taskId, projectId);
                }
            }
        }
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeyup(ev) {
            if (ev.key === 'Shift' && !this.state.editMode) {
                this.stateTimer.addTimeMode = false;
            }
        }
        _onMouseOut(ev) {
            ev.stopPropagation();
            if (!this.hoveredButton) {
                // If buttonHovered is not set it means that we are not in a timer button. So ignore it.
                return;
            }
            let relatedTarget = ev.relatedTarget;
            while (relatedTarget) {
                // Go up the parent chain
                if (relatedTarget === this.hoveredButton) {
                    // Check that we are still inside hoveredButton.
                    // If so it means it is a transition between child elements so ignore it.
                    return;
                }
                relatedTarget = relatedTarget.parentElement;
            }
            this.hoveredButton = false;
            this.stateTimer.indexHovered = -1;
        }
        _onMouseOver(ev) {
            ev.stopPropagation();
            if (this.hoveredButton) {
                // As mouseout is call prior to mouseover, if hoveredButton is set this means
                // that we haven't left it. So it's a mouseover inside it.
                return;
            }
            let target = ev.target.closest('button.btn_timer_line');
            if (!target) {
                // We are not into a timer button si ignore.
                return;
            }
            this.hoveredButton = target;
            this.stateTimer.indexHovered = parseInt(target.dataset.index);
        }
    }

    TimerGridRenderer.props = Object.assign({}, CommonTimesheetGridRenderer.props, {
        serverTime: {
            type: String,
            optional: true
        },
        stepTimer: {
            type: Number,
            optional: true
        },
        defaultProject: {
            type: [Boolean, Number],
            optional: true
        },
        Component: {
            type: Object,
            optional: true
        },
        timeBoundariesContext: {
            type: Object,
            shape: {
                start: String,
                end: String,
            },
        },
    });

    Object.assign(TimerGridRenderer.components, {
        TimerHeaderComponent,
        TimerStartComponent,
    });

    return TimerGridRenderer;
});

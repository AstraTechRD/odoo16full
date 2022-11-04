odoo.define('timesheet_grid.TimerHeaderComponent', function (require) {
    "use strict";

    const fieldUtils = require('web.field_utils');
    const TimerHeaderM2O = require('timesheet_grid.TimerHeaderM2O');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { onMounted, onWillUpdateProps, onPatched, useState, useRef } = owl;
    const { ComponentAdapter } = require('web.OwlCompatibility');

    class TimerHeaderM2OAdapter extends ComponentAdapter {
        async updateWidget(nextProps) {
            if (this.widget.projectId !== nextProps.widgetArgs[0] ||
                this.widget.taskId !== nextProps.widgetArgs[1]) {
                this.widget.projectId = nextProps.widgetArgs[0];
                this.widget.taskId = nextProps.widgetArgs[1];
                this.widget._updateRequiredField();
                const project = this.widget.projectId || false;
                await this.widget.projectMany2one.reinitialize(project);
                this.widget.taskMany2one.field.domain = this.widget._getTaskDomain(project);
                const task = this.widget.taskId || false;
                await this.widget.taskMany2one.reinitialize(task);
            } else if (nextProps.widgetArgs[2]) {
                this.widget._updateRequiredField();
            }
        }
    }

    class TimerHeaderComponent extends LegacyComponent {
        setup() {
            this.state = useState({
                time: null,
                manualTimeInput: false,
                errorManualTimeInput: false,
                description: this.props.description,
            });
            this.TimerHeaderM2O = TimerHeaderM2O;
            this.manualTimerAmount = "00:00";
            this.manualTimeInput = useRef("manualTimerInput");
            this.startButton = useRef("startButton");
            this.stopButton = useRef("stopButton");
            this.timerStarted = false;

            if (this.props.timerRunning === true) {
                this.timerStarted = true;
                this.state.time = Math.floor(Date.now() / 1000) - this.props.timer;
                this.timer = setInterval(() => {
                    this.state.time = Math.floor(Date.now() / 1000) - this.props.timer;
                }, 1000);
            }

            onWillUpdateProps(async (nextProps) => {
                if (nextProps.description !== this.props.description) {
                    this.state.description = nextProps.description;
                }
            });

            onPatched(() => {
                if (this.state.manualTimeInput && !this.state.errorManualTimeInput && this.manualTimeInput.el !== document.activeElement) {
                    this.manualTimeInput.el.focus();
                    this.manualTimeInput.el.select();
                }
                if (this.props.timerRunning && !this.timerStarted) {
                    this.timerStarted = true;
                    this.state.time = Math.floor(Date.now() / 1000) - this.props.timer;
                    this.timer = setInterval(() => {
                        this.state.time = Math.floor(Date.now() / 1000) - this.props.timer;
                    }, 1000);
                    this.stopButton.el.focus();
                } else if (!this.props.timerRunning && this.timerStarted) {
                    this.timerStarted = false;
                    clearInterval(this.timer);
                    this.startButton.el.focus();
                }
            });

            onMounted(() => {
                this.props.bus.on("TIMESHEET_TIMER:focusStartButton", this, this._focusStartButton);
                this.props.bus.on("TIMESHEET_TIMER:focusStopButton", this, this._focusStopButton);
                if (this.stopButton.el) {
                    this.stopButton.el.focus();
                } else {
                    this.startButton.el.focus();
                }
            });
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get timerMode() {
            return this.props.addTimeMode;
        }
        get timeInput() {
            return this.manualTimerAmount;
        }
        get _timerIsRunning() {
            return this.props.timerRunning;
        }
        get _timerReadOnly() {
            return this.props.timerReadOnly;
        }
        get _manualTimeInput() {
            return this.state.manualTimeInput;
        }
        get _timerString() {
            if (this.state.time) {
                const hours = Math.floor(this.state.time / 3600);
                const secondsLeft = this.state.time % 3600;
                const seconds = this._display2digits(secondsLeft % 60);
                const minutes = this._display2digits(Math.floor(secondsLeft / 60));

                return `${this._display2digits(hours)}:${minutes}:${seconds}`;
            }
            return "00:00:00";
        }
        get isMobile() {
            return this.env.device.isMobile;
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _display2digits(number) {
            return number > 9 ? "" + number : "0" + number;
        }

        _focusStopButton() {
            if (this.stopButton.el) {
                this.stopButton.el.focus();
            }
        }

        _focusStartButton() {
            if (this.startButton.el) {
                this.startButton.el.focus();
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        async _onKeydown(ev) {
            if (ev.key === 'Enter') {
                ev.preventDefault();
                if (this.state.manualTimeInput) {
                    this._onFocusoutTimer(ev);
                } else {
                    this.trigger('new-description', ev.target.value);
                    this.trigger('timer-stopped');
                }
            }
        }
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onFocusoutTimer(ev) {
            try {
                const value = fieldUtils.parse['float_time'](ev.target.value);
                this.state.errorManualTimeInput = (value < 0);
                if (!this.state.errorManualTimeInput) {
                    this.trigger('new-timer-value', value);
                    this.state.time = value * 3600;
                    this.state.manualTimeInput = false;
                }
            } catch (_) {
                this.state.errorManualTimeInput = true;
            }
        }
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onInputTimer(ev) {
            try {
                const value = fieldUtils.parse['float_time'](ev.target.value);
                this.state.errorManualTimeInput = (value < 0);
            } catch (_) {
                this.state.errorManualTimeInput = true;
            }
            this.manualTimerAmount = ev.target.value;
        }
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickStopTimer(ev) {
            ev.stopPropagation();
            this.trigger('timer-stopped');
        }
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickStartTimer(ev) {
            ev.stopPropagation();
            this.trigger('timer-started');
        }
        /**
         * @private
         * @param {Event} ev
         */
        _onInputDescription(ev) {
            this.trigger('new-description', ev.target.value);
        }
        /**
         * @private
         * @param {MouseEvent} ev
         */
        async _onClickManualTime(ev) {
            if (this.props.timerReadOnly) {
                return;
            }
            const rounded_minutes = await this.rpc({
                model: 'account.analytic.line',
                method: 'get_rounded_time',
                args: [this.state.time/60],
            });
            this.manualTimerAmount = fieldUtils.format['float_time'](rounded_minutes);
            this.state.manualTimeInput = true;
        }
        /**
         * @private
         * @param {MouseEvent} ev
         */
        async _onUnlinkTimer(ev) {
            this.trigger('timer-unlink');
        }
    }
    TimerHeaderComponent.template = 'timesheet_grid.timer_header';
    TimerHeaderComponent.props = {
        taskId: {
            type: Number,
            optional: true
        },
        projectId: {
            type: Number,
            optional: true
        },
        taskName: {
            type: String,
            optional: true
        },
        projectName: {
            type: String,
            optional: true
        },
        stepTimer: Number,
        timer: Number,
        description: {
            type: String,
            optional: true
        },
        timerRunning: Boolean,
        addTimeMode: Boolean,
        timerReadOnly: {
            type: Boolean,
            optional: true
        },
        projectWarning: Boolean,
        onTimerStarted: Function,
        onTimerStopped: Function,
        onTimerUnlink: Function,
        onTimerEditProject: Function,
        onTimerEditTask: Function,
        onNewTimerValue: Function,
        onNewDescription: Function,
        bus: Object,
    };
    TimerHeaderComponent.components = { TimerHeaderM2OAdapter };

    return TimerHeaderComponent;
});

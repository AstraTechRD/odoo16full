odoo.define('web_grid.components', function (require) {
    "use strict";

    const fieldUtils = require('web.field_utils');
    const utils = require('web.utils');
    const { debounce } = require("@web/core/utils/timing");

    const { Component, onPatched, onWillUpdateProps, useRef, useState } = owl;


    class BaseGridComponent extends Component {
        setup() {
            this.currentInput = useRef("currentInput");
            this.state = useState({
                error: false,
            });

            onWillUpdateProps(this.onWillUpdateProps);
            onPatched(this.onPatched);
        }
        onWillUpdateProps(nextProps) {
            if (nextProps.date !== this.props.date) {
                // if we change the range of dates we are looking at, the
                // component must remove it's error state
                this.state.error = false;
            }
        }
        onPatched() {
            if (this.currentInput.el) {
                this.currentInput.el.select();
            }
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * Returns the additional options needed for format/parse.
         * Override this getter to add options.
         *
         * @returns {Object}
         */
        get fieldOptions() {
            return this.props.nodeOptions;
        }
        /**
         * Returns the formatType needed for the format/parse function.
         * Override this getter to add options.
         *
         * @returns {Object}
         */
        get formatType() {
            return this.constructor.formatType || this.props.fieldInfo.type;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {any} value
         * @returns {string}
         */
        _format(value) {
            return fieldUtils.format[this.formatType](value, {}, this.fieldOptions);
        }
        /**
         * @private
         * @param {any} value
         * @returns {string}
         */
        _parse(value) {
            return fieldUtils.parse[this.formatType](value, {}, this.fieldOptions);
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * This handler verifies that the value has a good format, if it is
         * the case it will trigger an event to update the value in DB.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onBlurCell(ev) {
            let value;
            try {
                value = this._parse(ev.target.value);
                this.state.error = false;
            } catch (_) {
                this.state.error = ev.target.value;
            } finally {
                this.props.onCellUpdated({
                    path: this.props.path,
                    value
                });
            }
        }
        /**
         * This handler notifies the grid that a cell has been focused
         *
         * @private
         */
        _onFocusCell() {
            this.props.onCellFocused(this.props.path);
        }
    }
    BaseGridComponent.defaultProps = {
        cellHeight: 0,
        cellValue: 0,
        hasBarChartTotal: false,
        readonly: false,
        isTotal: false,
        nodeOptions: {},
        onCellFocused: () => {},
        onCellUpdated: () => {},
    };
    BaseGridComponent.props = {
        cellHeight: {
            type: Number,
            optional: true
        },
        cellValue: {
            type: Number,
            optional: true
        },
        fieldInfo: Object,
        hasBarChartTotal: {
            type: Boolean,
            optional: true,
        },
        isInput: Boolean,
        nodeOptions: {
            type: Object,
            optional: true,
        },
        onCellFocused: {
            type: Function,
            optional: true,
        },
        onCellUpdated: {
            type: Function,
            optional: true,
        },
        path: {
            type: String,
            optional: true
        },
        readonly: {
            type: Boolean,
            optional: true,
        },
        isTotal: {
            type: Boolean,
            optional: true
        },
        date: {
            type: String,
            optional: true
        },
    };
    BaseGridComponent.template = 'web_grid.BaseGridComponent';
    BaseGridComponent.formatType = 'float_factor';


    class FloatFactorComponent extends BaseGridComponent {}


    class FloatTimeComponent extends BaseGridComponent {
        get fieldOptions() {
            return Object.assign({}, super.fieldOptions, {
                noLeadingZeroHour: true,
            });
        }
    }
    FloatTimeComponent.formatType = 'float_time';


    class FloatToggleComponent extends BaseGridComponent {
        setup() {
            super.setup();
            this.state = useState({
                disabled: false,
                value: this.initialValue,
            });
            this._onClickButton = debounce(this._onClickButton, 200, true);
        }
        onWillUpdateProps(nextProps) {
            if (nextProps.cellValue !== this.initialValue) {
                this.state.value = nextProps.cellValue;
            }
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * Returns the additional options to the format function.
         *
         * @returns {Object}
         */
        get fieldOptions() {
            const fieldOptions = Object.assign({}, this.props.nodeOptions);
            if (!fieldOptions.factor) {
                fieldOptions.factor = 1;
            }
            const range = [0.0, 0.5, 1.0];
            if (!fieldOptions.range) {
                fieldOptions.range = range;
            }
            return fieldOptions;
        }
        /**
         * Returns the initial value.
         *
         * @returns {Number}
         */
        get initialValue() {
            return this.props.cellValue;
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * This handler is called when a user clicks on a button
         * it will change the value in the state
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickButton() {
            const range = this.fieldOptions.range;
            const currentFloat = fieldUtils.parse.float(this._format(this.state.value));
            const closest = utils.closestNumber(currentFloat, range);
            const closestIndex = range.indexOf(closest);
            const nextIndex = closestIndex + 1 < range.length ? closestIndex + 1 : 0;
            this.state.value = this._parse(fieldUtils.format.float(range[nextIndex]));
            this.state.disabled = true;
            this.props.onCellUpdated({
                path: this.props.path,
                value: this.state.value,
                doneCallback: () => {
                    this.state.disabled = false;
                }
            });
        }

    }
    FloatToggleComponent.template = 'web_grid.FloatToggleComponent';


    return {
        BaseGridComponent,
        FloatFactorComponent,
        FloatTimeComponent,
        FloatToggleComponent,
    };
});

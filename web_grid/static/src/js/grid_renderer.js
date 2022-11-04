odoo.define('web_grid.GridRenderer', function (require) {
    "use strict";

    const AbstractRenderer = require('web.AbstractRendererOwl');
    const fieldUtils = require('web.field_utils');
    const utils = require('web.utils');

    const gridComponentRegistry = require('web_grid.component_registry');
    const { useListener } = require("@web/core/utils/hooks");

    const { onPatched, onWillUpdateProps, useRef, useState } = owl;

    class GridRenderer extends AbstractRenderer {
        setup() {
            super.setup();
            
            this.root = useRef("root");
            this.state = useState({
                editMode: false,
                currentPath: "",
                errors: {},
            });
            this.currentInput = useRef("currentInput");
            useListener('mouseover', 'td:not(:first-child), th:not(:first-child)', this._onMouseEnter);
            useListener('mouseout', 'td:not(:first-child), th:not(:first-child)', this._onMouseLeave);

            onWillUpdateProps(this.onWillUpdateProps);
            onPatched(this.onPatched);
        }

        onWillUpdateProps(nextProps) {
            if (nextProps.data[0].next.grid_anchor !== this.props.data[0].next.grid_anchor) {
                //if we change the range of dates we are looking at,
                //the cells should not be in error state anymore
                this.state.errors = {};
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
         * returns the columns of the first gridgroup
         *
         * @returns {Object}
         */
        get columns() {
            return this.props.data.length ? this.props.data[0].cols : [];
        }
        /**
         * returns a boolean expressing if the grid uses cellComponents
         *
         * @returns {Object}
         */
        get component() {
            return gridComponentRegistry.get(this.props.cellComponent);
        }
        get gridAnchorNext() {
            return this.props.data[0].next.grid_anchor;
        }
        /**
         * As there have to be a minimum of 5 rows in an ungrouped grid,
         * this will return the number of empty rows to add
         * if there are not enough.
         *
         * @returns {Array}
         */
        get emptyRows() {
            const rowLength = this.props.isGrouped ? this.props.data.reduce((count, d) => count + d.rows.length + 1, 0) : this.props.data[0].rows.length;
            return Array.from({
                length: Math.max(5 - rowLength, 0)
            }, (_, i) => i);
        }
        /**
         * get the formatType needed for format and parse
         *
         * @returns {string}
         */
        get formatType() {
            if (this.hasComponent) {
                return this.component.formatType;
            }
            return this.props.fields[this.props.cellField].type;
        }
        /**
         * returns a boolean expressing if the grid uses cellComponents
         *
         * @returns {Boolean}
         */
        get hasComponent() {
            return gridComponentRegistry.contains(this.props.cellComponent);
        }
        /**
         * Get the information needed to display the total of a grid correctly
         * will contain the classMap and the value
         *
         * @returns {classmap: Object, value: number}
         */
        get gridTotal() {
            if (this.props.totals.super) {
                const classMap = {
                    'o_grid_super': true,
                    'text-danger': this.props.totals.super < 0,
                };
                const value = this.props.totals.super;
                return {
                    classMap,
                    value
                };
            } else {
                return {
                    classMap: {
                        o_grid_super: true
                    },
                    value: 0.0
                };
            }
        }
        /**
         * returns the getMeasureLabels
         *
         * @returns {string}
         */
        get measureLabel() {
            if (this.props.measureLabel) {
                return _.str.sprintf("%s", this.props.measureLabel);
            } else {
                return this.env._t("Total");
            }
        }
        /**
         * returns the xml of the noContentHelper
         *
         * @returns {string}
         */
        get noContentHelper() {
            return utils.json_node_to_xml(this.props.noContentHelper);
        }
        /**
         * returns a boolean expressing if yes or no the noContentHelp should be shown
         *
         * @returns {Boolean}
         */
        get showNoContentHelp() {
            const stateRow = Array.isArray(this.props.data) ? this.props.data.find(data => data.rows[0]) : this.props.data.rows[0];
            return stateRow === undefined && !!this.props.noContentHelp;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Notifies the model that a cell has been edited.
         *
         * @private
         * @param {string} path path to the cell
         * @param {Number} value new value that we want to store in DB
         * @param {Function} doneCallback function to call after update
         */
        _cellEdited(path, value, doneCallback) {
            const cell_path = path.split('.');
            const grid_path = cell_path.slice(0, -3);
            const row_path = grid_path.concat(['rows'], cell_path.slice(-2, -1));
            const col_path = grid_path.concat(['cols'], cell_path.slice(-1));
            this.trigger('cell-edited', {
                cell_path,
                row_path,
                col_path,
                value,
                doneCallback,
            });
        }
        /**
         * @private
         * @param {any} value
         * @returns {string}
         */
        _format(value) {
            if (value === undefined) {
                return '';
            }
            const cellField = this.props.fields[this.props.cellField];
            return fieldUtils.format[this.formatType](value, cellField, this.props.cellComponentOptions);
        }
        /**
         * @private
         * @param {integer} index
         * @returns {value: number, smallerThanZero: boolean, muted: boolean}
         */
        _formatCellContentTotals(index) {
            if (this.props.totals) {
                return {
                    value: this.props.totals.columns[index],
                    smallerThanZero: this.props.totals.columns[index] < 0,
                    muted: !this.props.totals.columns || !this.props.totals.columns[index]
                };
            } else {
                return {};
            }
        }
        /**
         * @private
         * @param {Object} cell
         * @returns {Object}
         */
        _getCellClassMap(cell) {
            // these are "hard-set" for correct grid behaviour
            const classmap = {
                o_grid_cell_container: true,
                o_grid_cell_empty: !cell.size,
                o_grid_cell_readonly: !this.props.editableCells || cell.readonly,
            };
            // merge in class info from the cell
            for (const cls of cell.classes || []) {
                // don't allow overwriting initial values
                if (!(cls in classmap)) {
                    classmap[cls] = true;
                }
            }
            return classmap;
        }
        /**
         * @private
         * @param {string} value
         * @returns {*}
         */
        _parse(value) {
            const cellField = this.props.fields[this.props.cellField];
            return fieldUtils.parse[this.formatType](value, cellField, this.props.cellComponentOptions);
        }
        /**
         * measure the height value of footer cell if hasBarChartTotal="true"
         * max height value is 90%
         *
         * @private
         * @param {number} index
         * @returns {number} height: to be used as css percentage
         */
        _totalHeight(index) {
            const maxCount = Math.max(...Object.values(this.props.totals.columns));
            const factor = maxCount ? (90 / maxCount) : 0;
            return factor * this.props.totals.columns[index];
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _onClickCreateInline() {
            this.trigger('create-inline');
        }
        /**
         * @private
         * @param path path to the cell
         */
        _onClickCellInformation(path) {
            this.state.editMode = false;
            this.trigger('open-cell-information', {
                path
            });
        }
        /**
         * @private
         * @param {string} path
         */
        _onFocusComponent(path) {
            this.state.editMode = true;
            this.state.currentPath = path;
        }
        /**
         * @private
         * @param {string} path path to the cell
         * @param {CustomEvent} ev
         */
        _onFocusGridCell(path) {
            this.state.editMode = true;
            this.state.currentPath = path;
        }
        /**
         * @private
         * @param {Object} cell
         * @param {CustomEvent} ev
         */
        _onGridInputBlur(ev) {
            this.state.editMode = false;
            let hasError = false;
            let value = ev.target.value;
            try {
                value = this._parse(value);
            } catch (_) {
                hasError = true;
            }
            const path = this.state.currentPath;
            if (hasError) {
                this.state.errors[path] = value;
            } else {
                delete this.state.errors[path];
                this._cellEdited(path, value);
            }
        }
        /**
         * @private
         * @param {Object}
         */
        _onUpdateValue({ path, value, doneCallback }) {
            this.state.editMode = false;
            if (value !== undefined) {
                this._cellEdited(path, value, doneCallback);
            }
        }
        /**
         * Hover the column in which the mouse is.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onMouseEnter(ev) {
            const cellParent = ev.target.closest('td,th');
            const rowParent = ev.target.closest('tr');
            const index = [...rowParent.children].indexOf(cellParent) + 1;
            this.root.el.querySelectorAll(`td:nth-child(${index}), th:nth-child(${index})`)
                .forEach(el => {
                    if (cellParent.querySelector('.o_grid_total_title')) {
                        el.classList.add('o_cell_highlight');
                    }
                    el.classList.add('o_cell_hover');
                });
        }
        /**
         * Remove the hover on the columns.
         *
         * @private
         */
        _onMouseLeave() {
            this.root.el.querySelectorAll('.o_cell_hover')
                .forEach(el => el.classList.remove('o_cell_hover', 'o_cell_highlight'));
        }
    }

    GridRenderer.defaultProps = {
        cellComponentOptions: {},
        hasBarChartTotal: false,
        hideColumnTotal: false,
        hideLineTotal: false,
    };
    GridRenderer.props = {
        editableCells: {
            type: Boolean,
            optional: true
        },
        canCreate: Boolean,
        cellComponent: {
            type: String,
            optional: true
        },
        cellComponentOptions: {
            type: Object,
            optional: true,
        },
        cellField: String,
        colField: String,
        createInline: Boolean,
        displayEmpty: Boolean,
        fields: Object,
        groupBy: Array,
        hasBarChartTotal: {
            type: Boolean,
            optional: true,
        },
        hideColumnTotal: {
            type: Boolean,
            optional: true,
        },
        hideLineTotal: {
            type: Boolean,
            optional: true,
        },
        measureLabel: {
            type: String,
            optional: true
        },
        noContentHelp: {
            type: String,
            optional: true
        },
        range: String,
        context: Object,
        arch: Object,
        isEmbedded: Boolean,
        isGrouped: Boolean,
        data: [{
            cols: [{
                values: Object,
                domain: Array,
                is_current: Boolean,
                is_unavailable: Boolean,
            }],
            grid: [{
                size: Number,
                domain: Array,
                value: Number,
                readonly: {
                    type: Boolean,
                    optional: true
                },
                is_current: Boolean,
                is_unavailable: Boolean,
            }],
            initial: Object,
            next: Object,
            prev: Object,
            rows: [{
                values: Object,
                domain: Array,
                project: Object,
                label: Array
            }],
            totals: {
                columns: Object,
                rows: Object,
                super: Number
            },
            __label: Array
        }],
        totals: Object,
    };
    GridRenderer.template = 'web_grid.GridRenderer';

    return GridRenderer;
});

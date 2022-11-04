/** @odoo-module alias=web_gantt.GanttRenderer */

import AbstractRenderer from 'web.AbstractRenderer';
import core from 'web.core';
import GanttRow from 'web_gantt.GanttRow';
import qweb from 'web.QWeb';
import session from 'web.session';
import utils from 'web.utils';
import ConnectorContainer from './connector/connector_container';
import { device, isDebug } from 'web.config';
import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';

const QWeb = core.qweb;
const _t = core._t;

export default AbstractRenderer.extend(WidgetAdapterMixin, {
    config: {
        GanttRow: GanttRow
    },
    custom_events: _.extend({}, AbstractRenderer.prototype.custom_events, {
        start_dragging: '_onStartDragging',
        start_no_dragging: '_onStartNoDragging',
        stop_dragging: '_onStopDragging',
        stop_no_dragging: '_onStopNoDragging',
    }),

    DECORATIONS: [
        'decoration-secondary',
        'decoration-success',
        'decoration-info',
        'decoration-warning',
        'decoration-danger',
    ],
    sampleDataTargets: [
        '.o_gantt_row',
    ],
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {boolean} params.canCreate
     * @param {boolean} params.canEdit
     * @param {boolean} params.canCellCreate
     * @param {Object} params.cellPrecisions
     * @param {string} params.colorField
     * @param {Object} params.fieldsInfo
     * @param {Object} params.SCALES
     * @param {string} params.string
     * @param {string} params.totalRow
     * @param {string} [params.popoverTemplate]
     */
    init(parent, state, params) {
        this._super.apply(this, arguments);

        this.$draggedPill = null;
        this.$draggedPillClone = null;

        this.canCreate = params.canCreate;
        this.canCellCreate = params.canCellCreate;
        this.canEdit = params.canEdit;
        this.canPlan = params.canPlan;
        this.cellPrecisions = params.cellPrecisions;
        this.colorField = params.colorField;
        this.disableDragdrop = params.disableDragdrop;
        this.progressField = params.progressField;
        this.consolidationParams = params.consolidationParams;
        this.fieldsInfo = params.fieldsInfo;
        this.SCALES = params.SCALES;
        this.string = params.string;
        this.totalRow = params.totalRow;
        this.collapseFirstLevel = params.collapseFirstLevel;
        this.thumbnails = params.thumbnails;
        this.dependencyEnabled = params.dependencyEnabled;
        this.pillLabel = params.pillLabel;
        this.dependencyField = params.dependencyField

        this.rowWidgets = {};
        // Pill decoration colors, By default display primary color for pill
        this.pillDecorations = _.chain(this.arch.attrs)
            .pick((value, key) => {
                return this.DECORATIONS.indexOf(key) >= 0;
            }).mapObject((value) => {
                return py.parse(py.tokenize(value));
            }).value();
        if (params.popoverTemplate) {
            this.popoverQWeb = new qweb(isDebug(), {_s: session.origin});
            this.popoverQWeb.add_template(utils.json_node_to_xml(params.popoverTemplate));
        } else {
            this.popoverQWeb = QWeb;
        }

        this.isRTL = _t.database.parameters.direction === "rtl";
        this.template_to_use = "GanttView";
        this.firstRendering = true;

        if (this.dependencyEnabled) {
            this._initialize_connectors();
            this._preventHoverEffect = false;
            this._connectorsStrokeColors = this._getStrokeColors();
            this._connectorsStrokeWarningColors = this._getStrokeWarningColors();
            this._connectorsStrokeErrorColors = this._getStrokeErrorColors();
            this._connectorsOutlineStrokeColor = this._getOutlineStrokeColors();
            this._connectorsCssSelectors = {
                bullet: '.o_connector_creator_bullet',
                pill: '.o_gantt_pill',
                pillWrapper: '.o_gantt_pill_wrapper',
                wrapper: '.o_connector_creator_wrapper',
                groupByNoGroup: '.o_gantt_row_nogroup',
            };
            this.events = Object.assign({ }, this.events, {
                'mouseenter .o_gantt_pill, .o_connector_creator_wrapper': '_onPillMouseEnter',
                'mouseleave .o_gantt_pill, .o_connector_creator_wrapper': '_onPillMouseLeave',
            });
        }
    },
    /**
     * Called each time the renderer is attached into the DOM.
     */
    on_attach_callback() {
        this._isInDom = true;
        core.bus.on("keydown", this, this._onKeydown);
        core.bus.on("keyup", this, this._onKeyup);
        if (!this.disableDragdrop) {
            this._setRowsDroppable();
        }
        if (this.dependencyEnabled) {
            WidgetAdapterMixin.on_attach_callback.call(this);
            // As we need the source and target of the connectors to be part of the dom,
            // we need to use the on_attach_callback in order to have the first rendering successful.
            this._mountConnectorContainer();
            window.addEventListener('resize', this._throttledReRender);
        }
    },
    /**
     * Called each time the renderer is detached from the DOM.
     */
    on_detach_callback() {
        this._isInDom = false;
        core.bus.off("keydown", this, this._onKeydown);
        core.bus.off("keyup", this, this._onKeyup);
        _.invoke(this.rowWidgets, 'on_detach_callback');
        if (this.dependencyEnabled) {
            WidgetAdapterMixin.on_detach_callback.call(this);
            this._connectorContainerComponent.unmount();
        }
    },
    /**
     * @override
    */
    destroy() {
        this._super(...arguments);
        if (this.dependencyEnabled) {
            window.removeEventListener('resize', this._throttledReRender);
        }
    },
    /**
     * @override
    */
    async start() {
        await this._super(...arguments);
        if (this.dependencyEnabled) {
            this._connectorContainerComponent = new ComponentWrapper(this, ConnectorContainer, this._getConnectorContainerProps());
            this._throttledReRender = _.throttle(async () => {
                await this.updateConnectorContainerComponent();
            }, 100);
        }
    },
    /**
      * Make sure the connectorManager Component is updated each time the view is updated.
      *
      * @override
      */
    async update() {
        if (this.dependencyEnabled) {
            await this.updateConnectorContainerComponent();
        }
        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Sets the class on the gantt_view corresponding to the mode.
     * This class is used to prevent the magnifier and + buttons during connection creation.
     *
     * @param {boolean} in_creation
     */
    set_connector_creation_mode(in_creation) {
        this.el.classList.toggle('o_grabbing', in_creation);
    },
    /**
     * Toggles the highlighting of the connector.
     *
     * @param {ConnectorContainer.Connector.props} connector
     * @param {boolean} highlighted
     */
    toggleConnectorHighlighting(connector, highlighted) {
        const masterPill = this._rowsAndRecordsDict.rows[connector.data.masterRowId].records[connector.data.masterId].pillElement;
        const slavePill = this._rowsAndRecordsDict.rows[connector.data.slaveRowId].records[connector.data.slaveId].pillElement;
        const sourceConnectorCreatorInfo = this._getConnectorCreatorInfo(masterPill);
        const targetConnectorCreatorInfo = this._getConnectorCreatorInfo(slavePill);
        if (!this._isConnectorCreatorDragged(sourceConnectorCreatorInfo)) {
            sourceConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
        }
        if (!this._isConnectorCreatorDragged(targetConnectorCreatorInfo)) {
            targetConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
        }
    },
    /**
     * Toggles the preventConnectorsHover props of the connector container.
     *
     * @param {boolean} prevent
     */
    togglePreventConnectorsHoverEffect(prevent){
        this._preventHoverEffect = prevent;
        if (this.dependencyEnabled && this._shouldRenderConnectors()) {
            this._connectorContainerComponent.update(this._getConnectorContainerProps());
        }
    },
    /**
     * Toggles the highlighting of the pill and connector creator of the provided element.
     *
     * @param {HTMLElement} element
     * @param {boolean} highlighted
     */
    async togglePillHighlighting(element, highlighted) {
        const connectorCreatorInfo = this._getConnectorCreatorInfo(element);
        if (connectorCreatorInfo.pill.dataset.id != 0) {
            const connectedConnectors = Object.values(this._connectors)
                                              .filter((connector) => {
                                                  const ids = [connector.data.slaveId, connector.data.masterId];
                                                  return ids.includes(
                                                      parseInt(connectorCreatorInfo.pill.dataset.id)
                                                  );
                                              });
            if (connectedConnectors.length) {
                connectedConnectors.forEach((connector) => {
                    connector.hovered = highlighted;
                    connector.canBeRemoved = !highlighted;
                });
                await this._connectorContainerComponent.update(this._getConnectorContainerProps());
            }

            if (!(this._rowsAndRecordsDict
                && this._rowsAndRecordsDict.records[connectorCreatorInfo.pill.dataset.id]
                && this._rowsAndRecordsDict.records[connectorCreatorInfo.pill.dataset.id].rowsInfo)) return;

            for (const pill of Object.values(this._rowsAndRecordsDict.records[connectorCreatorInfo.pill.dataset.id].rowsInfo).map((rowInfo) => rowInfo.pillElement)) {
                const tempConnectorCreatorInfo = this._getConnectorCreatorInfo(pill);
                if (highlighted || !this._isConnectorCreatorDragged(tempConnectorCreatorInfo)) {
                    tempConnectorCreatorInfo.pill.classList.toggle('highlight', highlighted);
                    if (connectorCreatorInfo.pill === tempConnectorCreatorInfo.pill) {
                        for (const connectorCreator of tempConnectorCreatorInfo.connectorCreators) {
                            connectorCreator.classList.toggle('invisible', !highlighted);
                        }
                    }
                }
            }
        }
    },
    /**
     * Re-render a given row and its sub-rows. This typically occurs when a row
     * is collapsed/expanded, to prevent from re-rendering the whole view.
     *
     * @param {Object} rowState part of the state concerning the row to update
     * @returns {Promise}
     */
    updateRow(rowState) {
        const oldRowIds = [rowState.id].concat(rowState.childrenRowIds);
        const oldRows = [];
        oldRowIds.forEach((rowId) => {
            if (this.rowWidgets[rowId]) {
                oldRows.push(this.rowWidgets[rowId]);
                delete this.rowWidgets[rowId];
            }
        });
        this.proms = [];
        const rows = this._renderRows([rowState], rowState.groupedBy);
        const proms = this.proms;
        delete this.proms;
        return Promise.all(proms).then(() => {
            let $previousRow = oldRows[0].$el;
            rows.forEach((row) => {
                row.$el.insertAfter($previousRow);
                $previousRow = row.$el;
            });
            _.invoke(oldRows, 'destroy');
            if (!this.disableDragdrop) {
                this._setRowsDroppable();
            }
            if (this.dependencyEnabled && this._shouldRenderConnectors()) {
                this.updateConnectorContainerComponent();
            }
        });
    },
    /**
     * Update the ConnectorContainer component with updated connectors.
     * @returns {Promise}
     */
    async updateConnectorContainerComponent() {
        await this._connectorContainerComponent.update(this._generateAndGetConnectorContainerProps());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Applies the style to the connector depending on the gantt date start and stop values.
     *
     * @param {Object} connector
     * @param {Object} masterRecord the record the slaveRecord depends on.
     * @param {Object} slaveRecord the record that depends on the masterRecord.
     * @private
     */
    _applySpecialColors(connector, masterRecord, slaveRecord) {
        let specialColors;
        if (slaveRecord[this.state.dateStartField].isBefore(masterRecord[this.state.dateStopField])) {
            specialColors = this._connectorsStrokeWarningColors;
            if (slaveRecord[this.state.dateStartField].isBefore(masterRecord[this.state.dateStartField])) {
                specialColors = this._connectorsStrokeErrorColors;
            }
        }
        if (specialColors) {
            connector['style'] = {
                stroke: {
                    color: specialColors.stroke,
                    hoveredColor: specialColors.hoveredStroke,
                }
            };
        }
    },
    /**
     * Updates the connectors state in regards to the records state and returns the props.
     *
     * @return {Object} the props to pass to the ConnectorContainer
     * @private
     */
    _generateAndGetConnectorContainerProps() {
        this._preventHoverEffect = false;
        this._initialize_connectors();
        if (this._shouldRenderConnectors()) {
            this._generateConnectors();
        }
        return this._getConnectorContainerProps();
    },
    /**
     * Updates the connectors state according to the records state.
     *
     * @private
     */
    _generateConnectors() {
        /*
            First we need to build a dictionary in order to be able to manage the cases when a record is present
            multiple times in the gantt view, in order to draw the connectors accordingly.
            Structure of dict:
            {
                records : {
                    #ID_RECORD_1: {
                        record: STATE_RECORD,
                        rowsInfo: {
                            #ID_ROW_1: {
                                pillElement: HTMLElementPill1,
                            },
                            ...
                        }
                    },
                    ...
                },
                rows: {
                    #ID_ROW_1: {
                        records: {
                            #ID_RECORD_1: {
                                pillElement: HTMLElementPill1,
                                record: STATE_RECORD
                            },
                            ...
                        }
                    },
                    ...
                },
            }
        */
        this._rowsAndRecordsDict = {
            records: { },
            rows: { },
        };
        for (const row of this.state.rows) {
            // We need to remove the closing "}]" from the row.id in order to ensure that things works
            // smoothly when collapse_first_level option is activated. Then we need to escape '"' &
            // '\' from the row.id before calling the querySelector.
            const rowElementSelector = `${this._connectorsCssSelectors.groupByNoGroup}[data-row-id^="${row.id.replace("}]", "").replace(/["\\]/g, '\\$&')}"]`;
            const rowElement = this.el.querySelector(rowElementSelector);
            if (!rowElement) continue;
            this._rowsAndRecordsDict.rows[row.id] = {
                records: { }
            };
            for (const record of row.records) {
                if (!this._shouldRenderRecordConnectors(record)) {
                    continue;
                }
                const recordElementSelector = `${this._connectorsCssSelectors.pill}[data-id="${record.id}"]`;
                const pillElement = rowElement.querySelector(recordElementSelector);
                this._rowsAndRecordsDict.rows[row.id].records[record.id] = {
                    pillElement: pillElement,
                    record: record,
                };
                if (!(record.id in this._rowsAndRecordsDict.records)) {
                    this._rowsAndRecordsDict.records[record.id] = {
                        record: record,
                        rowsInfo: { },
                    };
                }
                this._rowsAndRecordsDict.records[record.id].rowsInfo[row.id] = {
                    pillElement: pillElement,
                };
            }
        }

        // Then we go over the rows and records one by one in order to create the connectors
        const connector_id_generator = {
            _value: 1,
            getNext() {
                return this._value++;
            }
        };
        for (const record of this.state.records) {
            const connectors = this._generateConnectorsForRecord(record, connector_id_generator);
            Object.assign(this._connectors, connectors);
        }
    },
    /**
     * Generates the connectors using the dependencyField of the provided slave record.
     *
     * @param {Object} slaveRecord the slave record.
     * @param {{ getNext(): Number }} connector_id_generator a connector_id generator.
     * @private
     */
    _generateConnectorsForRecord(slaveRecord, connector_id_generator) {
        const result = {};
        for (const masterId of slaveRecord[this.dependencyField]) {
            if (masterId in this._rowsAndRecordsDict.records) {
                let connectors = [];
                if (!this._rowsAndRecordsDict.records[slaveRecord.id]) continue;
                for (const slaveRowId in this._rowsAndRecordsDict.records[slaveRecord.id].rowsInfo) {
                    if (!this._rowsAndRecordsDict.records[masterId]) continue;
                    for (const masterRowId in this._rowsAndRecordsDict.records[masterId].rowsInfo) {
                        /**
                         *   Having:
                         *      * B dependent on A
                         *      * C dependent on B
                         *      * D dependent on C
                         *   Prevent:
                         *      * Connectors between B & C that are not in the same group if B is in same group than C:
                         *          G1        B --- C                  B --- C
                         *                  /   \ /   \              /         \
                         *          G2    A             D    =>    A             D
                         *                  \   / \   /              \         /
                         *          G3        B --- C                  B --- C
                         *      * Connectors between A & B if A has already a link to B in the same group:
                         *          G1        --------- B              --------- B
                         *                  /       /                /
                         *          G2    A      /           =>    A
                         *                    /
                         *          G3    A ----------- B          A ----------- B
                         *   Allow:
                         *      * Connectors between C & B when A & B are always present in the same groups
                         *          G1    A ------ B          A ------ B
                         *                                           /
                         *          G2    A               =>  A ====
                         *                                           \
                         *          G3    A ------ B          A ------ B
                         */
                        if (masterRowId === slaveRowId
                            || !(
                                slaveRecord.id in this._rowsAndRecordsDict.rows[masterRowId].records
                                || masterId in this._rowsAndRecordsDict.rows[slaveRowId].records
                            )
                            || Object.keys(this._rowsAndRecordsDict.records[slaveRecord.id].rowsInfo).every(
                                (rowId) => (masterRowId !== rowId && masterId in this._rowsAndRecordsDict.rows[rowId].records)
                            )
                            || Object.keys(this._rowsAndRecordsDict.records[masterId].rowsInfo).every(
                                (rowId) => (slaveRowId !== rowId && slaveRecord.id in this._rowsAndRecordsDict.rows[rowId].records)
                            )
                        ) {
                            connectors.push(
                                this._generateConnector(
                                    masterRowId,
                                    this._rowsAndRecordsDict.records[masterId].record,
                                    slaveRowId,
                                    slaveRecord,
                                    connector_id_generator)
                            );
                        }
                    }
                }
                for (const connector of connectors) {
                    result[connector.id] = connector;
                }
            }
        }
        return result;
    },
    /**
     *
     * @param Number masterRowId the row id of the masterRecord (in order to handle m2m grouping)
     * @param {Object} masterRecord the record the slaveRecord depends on.
     * @param Number slaveRowId the row id of the slave record (in order to handle m2m grouping)
     * @param {Object} slaveRecord the record that depends on the masterRecord.
     * @param {{ getNext(): Number }} connector_id_generator a connector_id generator.
     * @return {Object} a connector for the provided parameters.
     * @private
     */
    _generateConnector(masterRowId, masterRecord, slaveRowId, slaveRecord, connector_id_generator) {
        const masterRecordPill = this._rowsAndRecordsDict.rows[masterRowId].records[masterRecord.id].pillElement;
        const slaveRecordPill = this._rowsAndRecordsDict.rows[slaveRowId].records[slaveRecord.id].pillElement;
        let source = this._connectorContainerComponent.componentRef.comp.getAnchorsPositions(masterRecordPill);
        let target = this._connectorContainerComponent.componentRef.comp.getAnchorsPositions(slaveRecordPill);

        const connector = {
            id: connector_id_generator.getNext(),
            source: source.right,
            canBeRemoved: true,
            data: {
                slaveId: slaveRecord.id,
                slaveRowId: slaveRowId,
                masterId: masterRecord.id,
                masterRowId: masterRowId,
            },
            target: target.left,
        };

        this._applySpecialColors(connector, masterRecord, slaveRecord)

        return connector;
    },
    /**
     * Determines if a dragged pill aims to be copied or updated
     * @private
     * @param {jQueryEvent} event
     */
    _getAction(event) {
        return event.ctrlKey || event.metaKey ? 'copy': 'reschedule';
    },
    /**
     * Gets the connector creator info for the provided element.
     *
     * @param {HTMLElement} element HTMLElement with a class of either o_connector_creator_bullet,
     *                              o_connector_creator_wrapper, o_gantt_pill or o_gantt_pill_wrapper.
     * @returns {{pillWrapper: HTMLElement, pill: HTMLElement, connectorCreators: Array<HTMLElement>}}
     * @private
     */
    _getConnectorCreatorInfo(element) {
        let connectorCreators = [];
        let pill = null;
        if (element.matches(this._connectorsCssSelectors.pillWrapper)) {
            element = element.querySelector(this._connectorsCssSelectors.pill);
        }
        if (element.matches(this._connectorsCssSelectors.bullet)) {
            element = element.closest(this._connectorsCssSelectors.wrapper);
        }
        if (element.matches(this._connectorsCssSelectors.pill)) {
            pill = element;
            connectorCreators = Array.from(element.parentElement.querySelectorAll(this._connectorsCssSelectors.wrapper));
        } else if (element.matches(this._connectorsCssSelectors.wrapper)) {
            connectorCreators = [element];
            pill = element.parentElement.querySelector(this._connectorsCssSelectors.pill);
        }
        return {
            pill: pill,
            pillWrapper: pill.parentElement,
            connectorCreators: connectorCreators,
        };
    },
    /**
     * Returns the props according to the current connectors state
     *
     * @returns {Object} the props to pass to the ConnectorContainer.
     * @private
     */
    _getConnectorContainerProps() {
        return {
            connectors: this._connectors,
            defaultStyle: {
                slackness: 0.9,
                stroke: {
                    color: this._connectorsStrokeColors.stroke,
                    hoveredColor: this._connectorsStrokeColors.hoveredStroke,
                    width: 2,
                },
                outlineStroke: {
                    color: this._connectorsOutlineStrokeColor.stroke,
                    hoveredColor: this._connectorsOutlineStrokeColor.hoveredStroke,
                    width: 1,
                }
            },
            hoverEaseWidth: 10,
            preventHoverEffect: this._preventHoverEffect,
            sourceQuerySelector: this._connectorsCssSelectors.bullet,
            targetQuerySelector: this._connectorsCssSelectors.pillWrapper,
            onCreationAbort: this._onConnectorCreationAbort.bind(this),
            onCreationDone: this._onConnectorCreationDone.bind(this),
            onCreationStart: this._onConnectorCreationStart.bind(this),
            onMouseOut: this._onConnectorMouseOut.bind(this),
            onMouseOver: this._onConnectorMouseOver.bind(this),
            onRemoveButtonClick: this._onConnectorRemoveButtonClick.bind(this),
            onRescheduleLaterButtonClick: this._onConnectorRescheduleLaterButtonClick.bind(this),
            onRescheduleSoonerButtonClick: this._onConnectorRescheduleSoonerButtonClick.bind(this),
        };

    },
    /**
     * Gets the rgba css string corresponding to the provided parameters.
     *
     * @param {number} r - [0, 255]
     * @param {number} g - [0, 255]
     * @param {number} b - [0, 255]
     * @param {number} [a = 1] - [0, 1]
     * @return {string} the css color.
     * @private
     */
    _getCssRGBAColor(r, g, b, a) {
        return `rgba(${ r }, ${ g }, ${ b }, ${ a || 1 })`;
    },
    /**
     * Format focus date which is used to display in gantt header (see XML
     * template).
     *
     * @private
     */
    _getFocusDateFormat() {
        const focusDate = this.state.focusDate;
        switch (this.state.scale) {
            case 'day':
                return focusDate.format('dddd, MMMM DD, YYYY');
            case 'week':
                const dateStart = focusDate.clone().startOf('week').format('DD MMMM YYYY');
                const dateEnd = focusDate.clone().endOf('week').format('DD MMMM YYYY');
                return _.str.sprintf('%s - %s', dateStart, dateEnd);
            case 'month':
                return focusDate.format('MMMM YYYY');
            case 'year':
                return focusDate.format('YYYY');
            default:
                break;
        }
    },
    /**
     * Gets the outline stroke's rgba css strings for both the stroke and its hovered state in error state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getOutlineStrokeColors() {
        return this._getStrokeAndHoveredStrokeColor(255, 255, 255);
    },
    /**
     * Get pills info
     *
     * @param {Object} row
     * @param {*} groupLevel
     */
    _getPillsInfo(row, groupLevel) {
        return {
            resId: row.resId,
            pills: row.records,
            groupLevel: groupLevel,
            progressBar: row.progressBar,
        };
    },
    /**
     * Get dates between gantt start and gantt stop date to render gantt slots
     *
     * @private
     * @returns {Moment[]}
     */
    _getSlotsDates() {
        const token = this.SCALES[this.state.scale].interval;
        const stopDate = this.state.stopDate;
        let day = this.state.startDate;
        const dates = [];
        while (day <= stopDate) {
            dates.push(day);
            day = day.clone().add(1, token);
        }
        return dates;
    },
    /**
     * Gets the stroke's rgba css string corresponding to the provided parameters for both the stroke and its
     * hovered state.
     *
     * @param {number} r - [0, 255]
     * @param {number} g - [0, 255]
     * @param {number} b - [0, 255]
     * @return {{ stroke: {string}, hoveredStroke: {string} }} the css colors.
     * @private
     */
    _getStrokeAndHoveredStrokeColor(r, g, b) {
        return {
            stroke: this._getCssRGBAColor(r, g, b, 0.5),
            hoveredStroke: this._getCssRGBAColor(r, g, b, 1),
        };
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeColors() {
        return this._getStrokeAndHoveredStrokeColor(143, 143, 143);
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state in error state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeErrorColors() {
        return this._getStrokeAndHoveredStrokeColor(211, 65, 59);
    },
    /**
     * Gets the stroke's rgba css strings for both the stroke and its hovered state in warning state.
     *
     * @return {{ stroke: {string}, hoveredStroke: {string} }}
     * @private
     */
    _getStrokeWarningColors() {
        return this._getStrokeAndHoveredStrokeColor(236, 151, 31);
    },
    /**
     * Initialize the _connectors attribute and delete its associated _rowsAndRecordsDict attribute.
     * @private
     */
    _initialize_connectors() {
        this._connectors = { };
        delete this._rowsAndRecordsDict;
    },
    /**
     * Gets whether the provided connector creator is the source element of the currently dragged connector.
     *
     * @param {{pill: HTMLElement, connectorCreators: Array<HTMLElement>}} connectorCreatorInfo
     * @returns {boolean}
     * @private
     */
    _isConnectorCreatorDragged(connectorCreatorInfo) {
        return this._connectorInCreation && this._connectorInCreation.data.sourceElement.dataset.id === connectorCreatorInfo.pill.dataset.id;
    },
    /**
     * Mounts the ConnectorContainer Component if needed.
     *
     * @returns {Promise<void>}
     * @private
     */
    async _mountConnectorContainer() {
        this.el.classList.toggle('position-relative', true);
        if (this._connectorContainerComponent.status === 'mounted') {
            await this._connectorContainerComponent.unmount();
        }
        await this._connectorContainerComponent.mount(this.el);
        await this.updateConnectorContainerComponent();
    },
    /**
     * Prepare view info which is used by GanttRow widget
     *
     * @private
     * @returns {Object}
     */
    _prepareViewInfo() {
        return {
            colorField: this.colorField,
            progressField: this.progressField,
            consolidationParams: this.consolidationParams,
            state: this.state,
            fieldsInfo: this.fieldsInfo,
            slots: this._getSlotsDates(),
            pillDecorations: this.pillDecorations,
            popoverQWeb: this.popoverQWeb,
            activeScaleInfo: {
                precision: this.cellPrecisions[this.state.scale],
                interval: this.SCALES[this.state.scale].cellPrecisions[this.cellPrecisions[this.state.scale]],
                time: this.SCALES[this.state.scale].time,
            },
        };
    },
    /**
     * @override
     * @private
     */
    async _render() {
        await this._super(...arguments);
        if (this._isInDom && this.dependencyEnabled) {
            // If the renderer is not yet part of the dom (during first rendering), then
            // the call will be performed in the on_attach_callback.
            await this._mountConnectorContainer();
        }
    },
    /**
     * Renders gantt view and its rows.
     *
     * @override
     */
    async _renderView() {
        const oldRowWidgets = Object.keys(this.rowWidgets).map((rowId) => {
            return this.rowWidgets[rowId];
        });
        this.rowWidgets = {};
        this.viewInfo = this._prepareViewInfo();

        this.proms = [];
        const rows = this._renderRows(this.state.rows, this.state.groupedBy);
        let totalRow;
        if (this.totalRow) {
            totalRow = this._renderTotalRow();
        }
        this.proms.push(this._super.apply(this, arguments));
        const proms = this.proms;
        delete this.proms;
        return Promise.all(proms).then(() => {
            _.invoke(oldRowWidgets, 'destroy');
            if (this.firstRendering) {
                this._replaceElement(QWeb.render(this.template_to_use, {widget: this, isMobile: device.isMobile}));
                this.firstRendering = false;
            } else {
                const newContent = $(QWeb.render(this.template_to_use, {widget: this, isMobile: device.isMobile}));
                this.$el.html(newContent[0].innerHTML);
            }
            const $containment = $('<div id="o_gantt_containment"/>');
            const $rowContainer = this.$('.o_gantt_row_container');
            $rowContainer.append($containment);
            if (!this.state.groupedBy.length) {
                $containment.css(this.isRTL ? {right: 0} : {left: 0});
            }

            rows.forEach((row) => {
                row.$el.appendTo($rowContainer);
            });
            if (totalRow) {
                totalRow.$el.appendTo(this.$('.o_gantt_total_row_container'));
            }

            if (this._isInDom && !this.disableDragdrop) {
                this._setRowsDroppable();
            }

            if (this.state.isSample) {
                this._renderNoContentHelper();
            }
        });
    },
    /**
     * Render rows outside the DOM, so that we can insert them to the DOM once
     * they are all ready.
     *
     * @private
     * @param {Object[]} rows recursive structure of records according to
     *   groupBys
     * @param {string[]} groupedBy
     * @returns {Promise<GanttRow[]>} resolved with the row widgets
     */
    _renderRows(rows, groupedBy) {
        let rowWidgets = [];

        const groupLevel = this.state.groupedBy.length - groupedBy.length;
        // FIXME: could we get rid of collapseFirstLevel in Renderer, and fully
        // handle this in Model?
        let hideSidebar = groupedBy.length === 0;
        if (this.collapseFirstLevel) {
            hideSidebar = this.state.groupedBy.length === 0;
        }
        rows.forEach((row) => {
            const pillsInfo = this._getPillsInfo(row, groupLevel);
            if (groupedBy.length) {
                pillsInfo.groupName = row.name;
                pillsInfo.groupedByField = row.groupedByField;
            }
            const params = {
                canCreate: this.canCreate,
                canCellCreate: this.canCellCreate,
                canEdit: this.canEdit,
                canPlan: this.canPlan,
                isGroup: row.isGroup,
                consolidate: (groupLevel === 0) && (this.state.groupedBy[0] === this.consolidationParams.maxField),
                hideSidebar: hideSidebar,
                isOpen: row.isOpen,
                disableDragdrop: this.disableDragdrop,
                rowId: row.id,
                fromServer: row.fromServer,
                scales: this.SCALES,
                unavailabilities: row.unavailabilities,
                pillLabel: this.pillLabel,
            };
            if (this.thumbnails && row.groupedByField && row.groupedByField in this.thumbnails){
                params.thumbnail = {model: this.fieldsInfo[row.groupedByField].relation, field: this.thumbnails[row.groupedByField],};
            }
            rowWidgets.push(this._renderRow(pillsInfo, params));
            if (row.isGroup && row.isOpen) {
                const subRowWidgets = this._renderRows(row.rows, groupedBy.slice(1));
                rowWidgets = rowWidgets.concat(subRowWidgets);
            }
        });
        return rowWidgets;
    },
    /**
     * Render a row outside the DOM.
     *
     * Note that we directly call the private function _widgetRenderAndInsert to
     * prevent from generating a documentFragment for each row we have to
     * render. The Widget API should offer a proper way to start a widget
     * without inserting it anywhere.
     *
     * @private
     * @param {Object} pillsInfo
     * @param {Object} params
     * @returns {Promise<GanttRow>} resolved when the row is ready
     */
    _renderRow(pillsInfo, params) {
        const ganttRow = new this.config.GanttRow(this, pillsInfo, this.viewInfo, params);
        this.rowWidgets[ganttRow.rowId] = ganttRow;
        this.proms.push(ganttRow._widgetRenderAndInsert(() => {}));
        return ganttRow;
    },
    /**
     * Renders the total row outside the DOM, so that we can insert it to the
     * DOM once all rows are ready.
     *
     * @returns {Promise<GanttRow} resolved with the row widget
     */
    _renderTotalRow() {
        const pillsInfo = {
            pills: this.state.records,
            groupLevel: 0,
            groupName: "Total"
        };
        const params = {
            canCreate: this.canCreate,
            canCellCreate: this.canCellCreate,
            canEdit: this.canEdit,
            canPlan: this.canPlan,
            hideSidebar: this.state.groupedBy.length === 0,
            isGroup: true,
            rowId: '__total_row__',
            scales: this.SCALES,
        };
        return this._renderRow(pillsInfo, params);
    },
    /**
     * Set droppable on all rows
     */
    _setRowsDroppable() {
        // jQuery (< 3.0) rounds the width value but we need the exact value
        // getBoundingClientRect is costly when there are lots of rows
        const firstCell = this.$('.o_gantt_header_scale .o_gantt_header_cell:first')[0];
        _.invoke(this.rowWidgets, 'setDroppable', firstCell);
    },
    /**
     * Returns whether connectors should be rendered or not.
     * The connectors won't be rendered on sampleData as we can't be sure that data are coherent.
     * The connectors won't be rendered on mobile as the usability is not guarantied.
     * The connectors won't be rendered on multiple groupBy as we would need to manage groups folding which seems
     *     overkill at this stage.
     *
     * @return {boolean}
     * @private
     */
    _shouldRenderConnectors() {
        return this._isInDom && !this.state.isSample && !device.isMobile && this.state.groupedBy.length <= 1;
    },
    /**
     * Returns whether connectors should be rendered on particular records or not.
     * This method is intended to be overridden in particular modules in order to set particular record's condition.
     *
     * @return {boolean}
     * @private
     */
    _shouldRenderRecordConnectors(record) {
        return true;
    },
    /**
     * Toggles popover visibility.
     *
     * @param visible
     * @private
     */
    _togglePopoverVisibility(visible) {
        const $pills = this.$(this._connectorsCssSelectors.pill);
        if (visible) {
            $pills.popover('enable').popover('dispose');
        } else {
            $pills.popover('hide').popover('disable');
        }
    },
    /**
     * Triggers the on_connector_highlight at the Controller.
     *
     * @param {ConnectorContainer.Connector.props} connector
     * @param {boolean} highlighted
     * @private
     */
    _triggerConnectorHighlighting(connector, highlighted) {
        this.trigger_up(
            'on_connector_highlight',
            {
                connector: connector,
                highlighted: highlighted,
            });
    },
    /**
     * Triggers the on_pill_highlight at the Controller.
     *
     * @param {HTMLElement} element
     * @param {boolean} highlighted
     * @private
     */
    _triggerPillHighlighting(element, highlighted) {
        this.trigger_up(
            'on_pill_highlight',
            {
                element: element,
                highlighted: highlighted,
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handler for Connector connector-creation-abort event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorCreationAbort(payload) {
        this._connectorInCreation = null;
        const connectorCreatorInfo = this._getConnectorCreatorInfo(payload.data.sourceElement);
        this._triggerPillHighlighting(connectorCreatorInfo.pill, false);
        this.trigger_up('on_connector_end_drag');
        this._togglePopoverVisibility(true);
    },
    /**
     * Handler for Connector connector-creation-done event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorCreationDone(payload) {
        this._connectorInCreation = null;
        const connectorSourceCreatorInfo = this._getConnectorCreatorInfo(payload.data.sourceElement);
        const connectorTargetCreatorInfo = this._getConnectorCreatorInfo(payload.data.targetElement);
        this.trigger_up('on_connector_end_drag');
        this.trigger_up(
            'on_create_connector',
            {
                masterId: parseInt(connectorSourceCreatorInfo.pill.dataset.id),
                slaveId: parseInt(connectorTargetCreatorInfo.pill.dataset.id),
            });
        this._togglePopoverVisibility(true);
    },
    /**
     * Handler for Connector connector-creation-start event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorCreationStart(payload) {
        this._connectorInCreation = payload;
        this._togglePopoverVisibility(false);
        const connectorCreatorInfo = this._getConnectorCreatorInfo(payload.data.sourceElement);
        this._triggerPillHighlighting(connectorCreatorInfo.pill, false);
        this.trigger_up('on_connector_start_drag');
    },
    /**
     * Handler for Connector connector-mouseout event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorMouseOut(payload) {
        this._triggerConnectorHighlighting(payload, false);
    },
    /**
     * Handler for Connector connector-mouseover event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorMouseOver(payload) {
        this._triggerConnectorHighlighting(payload, true);
    },
    /**
     * Handler for Connector connector-remove-button-click event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorRemoveButtonClick(payload) {
        this.trigger_up(
        'on_remove_connector',
        {
            masterId: payload.data.masterId,
            slaveId: payload.data.slaveId,
        });
    },
    /**
     * Handler for Connector connector_reschedule_later_button_click event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorRescheduleLaterButtonClick(payload) {
        this.trigger_up(
        'on_reschedule_according_to_dependency',
        {
            direction: 'forward',
            masterId: payload.data.masterId,
            slaveId: payload.data.slaveId,
        });
    },
    /**
     * Handler for Connector connector_reschedule_sooner_button_click event.
     *
     * @param {Object} payload
     * @private
     */
    async _onConnectorRescheduleSoonerButtonClick(payload) {
        this.trigger_up(
        'on_reschedule_according_to_dependency',
        {
            direction: 'backward',
            masterId: payload.data.masterId,
            slaveId: payload.data.slaveId,
        });
    },
    /**
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        this.action = this._getAction(ev);
        if (this.$draggedPill && this.action === 'copy') {
            this.$el.addClass('o_copying');
            this.$el.removeClass('o_grabbing');
        }
    },
    /**
     * @param {KeyboardEvent} ev
     */
    _onKeyup(ev) {
        this.action = this._getAction(ev);
        if (this.$draggedPill && this.action === 'reschedule') {
            this.$el.addClass('o_grabbing');
            this.$el.removeClass('o_copying');
        }
    },
    /**
     * Handler for Pill connector-mouseenter event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillMouseEnter(ev) {
        ev.stopPropagation();
        this._triggerPillHighlighting(ev.currentTarget, true);
    },
    /**
     * Handler for Pill connector-mouseleave event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillMouseLeave(ev) {
        ev.stopPropagation();
        this._triggerPillHighlighting(ev.currentTarget, false);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onStartDragging(event) {
        this.$draggedPill = event.data.$draggedPill;
        this.$draggedPill.addClass('o_dragged_pill');
        if (this.action === 'copy') {
            this.$el.addClass('o_copying');
        } else {
            this.$el.addClass('o_grabbing');
        }
        if (this.dependencyEnabled) {
            this._triggerPillHighlighting(this.$draggedPill.get(0), false);
        }
    },
    /**
     * Used to give a feedback on the impossibility of moving the pill
     * @private
     */
    _onStartNoDragging() {
        this.$el.addClass('o_no_dragging');
    },
    /**
     * @private
     */
    _onStopDragging: function () {
        this.$draggedPill.removeClass('o_dragged_pill');
        this.$draggedPill = null;
        this.$draggedPillClone = null;
        this.$el.removeClass('o_grabbing');
        this.$el.removeClass('o_copying');
    },
    /**
     * @private
     */
    _onStopNoDragging() {
        this.$el.removeClass('o_no_dragging');
    },
});

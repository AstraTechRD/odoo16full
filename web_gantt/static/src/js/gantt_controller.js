/** @odoo-module alias=web_gantt.GanttController */

import AbstractController from 'web.AbstractController';
import core from 'web.core';
import config from 'web.config';
import { confirm as confirmDialog } from 'web.Dialog';
import { Domain } from '@web/core/domain';
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

const QWeb = core.qweb;
const _t = core._t;
const { Component } = owl;

export function removeDomainLeaf(domain, keysToRemove) {
    function processLeaf(elements, idx, operatorCtx, newDomain) {
        const leaf = elements[idx];
        if (leaf.type === 10) {
            if (keysToRemove.includes(leaf.value[0].value)) {
                if (operatorCtx === '&') {
                    newDomain.ast.value.push(...Domain.TRUE.ast.value);
                } else if (operatorCtx === '|') {
                    newDomain.ast.value.push(...Domain.FALSE.ast.value);
                }
            } else {
                newDomain.ast.value.push(leaf);
            }
            return 1;
        } else if (leaf.type === 1) {
            // Special case to avoid OR ('|') that can never resolve to true
            if (leaf.value === '|' && elements[idx + 1].type === 10 && elements[idx + 2].type === 10
                && keysToRemove.includes(elements[idx + 1].value[0].value)
                && keysToRemove.includes(elements[idx + 2].value[0].value)
            ) {
                newDomain.ast.value.push(...Domain.TRUE.ast.value);
                return 3;
            }
            newDomain.ast.value.push(leaf);
            if (leaf.value === '!') {
                return 1 + processLeaf(elements, idx + 1, '&', newDomain);
            }
            const firstLeafSkip = processLeaf(elements, idx + 1, leaf.value, newDomain);
            const secondLeafSkip = processLeaf(elements, idx + 1 + firstLeafSkip, leaf.value, newDomain);
            return 1 + firstLeafSkip + secondLeafSkip;
        }
        return 0;
    }

    domain = new Domain(domain);
    if (domain.ast.value.length === 0) {
        return domain;
    }
    const newDomain = new Domain([]);
    processLeaf(domain.ast.value, 0, '&', newDomain);
    return newDomain;
}

export default AbstractController.extend({
    events: _.extend({}, AbstractController.prototype.events, {
        'click .o_gantt_button_add': '_onAddClicked',
        'click .o_gantt_button_scale': '_onScaleClicked',
        'click .o_gantt_button_prev': '_onPrevPeriodClicked',
        'click .o_gantt_button_next': '_onNextPeriodClicked',
        'click .o_gantt_button_today': '_onTodayClicked',
        'click .o_gantt_button_expand_rows': '_onExpandClicked',
        'click .o_gantt_button_collapse_rows': '_onCollapseClicked',
    }),
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        add_button_clicked: '_onCellAddClicked',
        collapse_row: '_onCollapseRow',
        expand_row: '_onExpandRow',
        on_connector_end_drag: '_onConnectorEndDrag',
        on_connector_highlight: '_onConnectorHighlight',
        on_connector_start_drag: '_onConnectorStartDrag',
        on_create_connector: '_onCreateConnector',
        on_pill_highlight: '_onPillHighlight',
        on_remove_connector: '_onRemoveConnector',
        on_reschedule_according_to_dependency: '_onRescheduleAccordingToDependency',
        pill_clicked: '_onPillClicked',
        pill_resized: '_onPillResized',
        pill_dropped: '_onPillDropped',
        plan_button_clicked: '_onCellPlanClicked',
        updating_pill_started: '_onPillUpdatingStarted',
        updating_pill_stopped: '_onPillUpdatingStopped',
    }),
    buttonTemplateName: 'GanttView.buttons',

    /**
     * @override
     * @param {Widget} parent
     * @param {GanttModel} model
     * @param {GanttRenderer} renderer
     * @param {Object} params
     * @param {Object} params.context
     * @param {Array[]} params.dialogViews
     * @param {Object} params.SCALES
     * @param {boolean} params.collapseFirstLevel
     */
    init(parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.model = model;
        this.context = params.context;
        this.dialogViews = params.dialogViews;
        this.SCALES = params.SCALES;
        this.allowedScales = params.allowedScales;
        this.collapseFirstLevel = params.collapseFirstLevel;
        this.createAction = params.createAction;
        this.actionDomain = params.actionDomain;
        this._draggingConnector = false;

        this.isRTL = _t.database.parameters.direction === "rtl";
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQuery} [$node] to which the buttons will be appended
     */
    renderButtons($node) {
        this.$buttons = this._renderButtonsQWeb();
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    _renderButtonsQWeb() {
        return $(QWeb.render(this.buttonTemplateName, this._renderButtonQWebParameter()));
    },
    _renderButtonQWebParameter() {
        const state = this.model.get();
        const nbGroups = state.groupedBy.length;
        const minNbGroups = this.collapseFirstLevel ? 0 : 1;
        const displayExpandCollapseButtons = nbGroups > minNbGroups;
        return {
            groupedBy: state.groupedBy,
            widget: this,
            SCALES: this.SCALES,
            activateScale: state.scale,
            allowedScales: this.allowedScales,
            displayExpandCollapseButtons: displayExpandCollapseButtons,
            isMobile: config.device.isMobile,
        };
    },
    /**
     * @override
     */
    updateButtons() {
        if (!this.$buttons) {
            return;
        }
        this.$buttons.html(this._renderButtonsQWeb());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {integer} id
     * @param {Object} schedule
     */
    _copy(id, schedule) {
        return this._executeAsyncOperation(
            this.model.copy.bind(this.model),
            [id, schedule]
        );
    },
    /**
     * @private
     * @param {function} operation
     * @param {Array} args
     */
    _executeAsyncOperation(operation, args) {
        const prom = new Promise((resolve, reject) => {
            const asyncOp = operation(...args);
            asyncOp.then(resolve).guardedCatch(resolve);
            this.dp.add(asyncOp).guardedCatch(reject);
        });
        return prom.then(this.reload.bind(this, {}));
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _getDialogContext(date, rowId) {
        const state = this.model.get();
        const context = {};
        context[state.dateStartField] = date.clone();
        context[state.dateStopField] = date.clone().endOf(this.SCALES[state.scale].interval);
        if (rowId) {
            // Default values of the group this cell belongs in
            // We can read them from any pill in this group row
            for (const fieldName of state.groupedBy) {
                const groupValue = Object.assign({}, ...JSON.parse(rowId));
                let value = groupValue[fieldName];
                if (Array.isArray(value)) {
                    const { type: fieldType } = state.fields[fieldName];
                    if (fieldType === "many2many") {
                        value = [value[0]];
                    } else if (fieldType === "many2one") {
                        value = value[0];
                    }
                }
                if (value !== undefined) {
                    context[fieldName] = value;
                }
            }
        }

        // moment context dates needs to be converted in server time in view
        // dialog (for default values)
        for (const k in context) {
            const type = state.fields[k].type;
            if (context[k] && (type === 'datetime' || type === 'date')) {
                context[k] = this.model.convertToServerTime(context[k]);
            }
        }

        return context;
    },
    /**
     * Opens dialog to add/edit/view a record
     *
     * @private
     * @param {Object} props FormViewDialog props
     * @param {Object} options
     */
    _openDialog(props, options = {}) {
        const title = props.title || (props.resId ? _t("Open") : _t("Create"));
        const onClose = options.onClose || (() => {});
        options = {
            ...options,
            onClose: async () => {
                onClose();
                await this.reload();
            },
        };
        let removeRecord;
        if (this.is_action_enabled('delete') && props.resId) {
            removeRecord = this._onDialogRemove.bind(this, props.resId)
        }
        Component.env.services.dialog.add(FormViewDialog, {
            title,
            resModel: this.modelName,
            viewId: this.dialogViews[0][0],
            resId: props.resId,
            mode: this.is_action_enabled('edit') ? "edit" : "readonly",
            context: _.extend({}, this.context, props.context),
            removeRecord
        }, options);
    },
    /**
     * Handler called when clicking the
     * delete button in the edit/view dialog.
     * Reload the view and close the dialog
     *
     * @returns {function}
     */
    _onDialogRemove(resID) {
        const confirm = new Promise((resolve) => {
            confirmDialog(this, _t('Are you sure to delete this record?'), {
                confirm_callback: () => {
                    resolve(true);
                },
                cancel_callback: () => {
                    resolve(false);
                },
            });
        });

        return confirm.then((confirmed) => {
            if ((!confirmed)) {
                return Promise.resolve();
            }// else
            return this._rpc({
                model: this.modelName,
                method: 'unlink',
                args: [[resID,],],
            }).then(() => {
                return this.reload();
            })
        });
    },
    /**
     * Get domain of records for plan dialog in the gantt view.
     *
     * @private
     * @param {Object} state
     * @returns {Array[]}
     */
    _getPlanDialogDomain(state) {
        const newDomain = removeDomainLeaf(
            this.actionDomain,
            [state.dateStartField, state.dateStopField]
        );
        return Domain.and([
            newDomain,
            ['|', [state.dateStartField, '=', false], [state.dateStopField, '=', false]],
        ]).toList({});
    },
    /**
     * Opens dialog to plan records.
     *
     * @private
     * @param {Object} context
     */
    _openPlanDialog(context) {
        const state = this.model.get();
        Component.env.services.dialog.add(SelectCreateDialog, {
            title: _t("Plan"),
            resModel: this.modelName,
            domain: this._getPlanDialogDomain(state),
            views: this.dialogViews,
            context: Object.assign({}, this.context, context),
            onSelected: (resIds) => {
                if (resIds.length) {
                    // Here, the dates are already in server time so we set the
                    // isUTC parameter of reschedule to true to avoid conversion
                    this._reschedule(resIds, context, true, this.openPlanDialogCallback);
                }
            },
        });
    },
    /**
     * upon clicking on the create button, determines if a dialog with a formview should be opened
     * or if a wizard should be openned, then opens it
     *
     * @param {object} context
     */
    _onCreate(context) {
        if (this.createAction) {
            const fullContext = Object.assign({}, this.context, context);
            this.do_action(this.createAction, {
                additional_context: fullContext,
                on_close: this.reload.bind(this, {})
            });
        } else {
            this._openDialog({ context });
        }
    },
    /**
     * Reschedule records and reload.
     *
     * Use a DropPrevious to prevent unnecessary reload and rendering.
     *
     * Note that when the rpc fails, we have to reload and re-render as some
     * records might be outdated, causing the rpc failure).
     *
     * @private
     * @param {integer[]|integer} ids
     * @param {Object} schedule
     * @param {boolean} isUTC
     * @returns {Promise} resolved when the record has been reloaded, rejected
     *   if the request has been dropped by DropPrevious
     */
    _reschedule(ids, schedule, isUTC, callback) {
        return this._executeAsyncOperation(
            this.model.reschedule.bind(this.model),
            [ids, schedule, isUTC, callback]
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens a dialog to create a new record.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCellAddClicked(ev) {
        ev.stopPropagation();
        const context = this._getDialogContext(ev.data.date, ev.data.rowId);
        for (const k in context) {
            context[_.str.sprintf('default_%s', k)] = context[k];
        }
        this._onCreate(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddClicked(ev) {
        ev.preventDefault();
        const context = {};
        const state = this.model.get();
        context[state.dateStartField] = this.model.convertToServerTime(state.focusDate.clone().startOf(state.scale));
        context[state.dateStopField] = this.model.convertToServerTime(state.focusDate.clone().endOf(state.scale));
        for (const k in context) {
            context[_.str.sprintf('default_%s', k)] = context[k];
        }
        this._onCreate(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCollapseClicked(ev) {
        ev.preventDefault();
        this.model.collapseRows();
        this.update({}, { reload: false });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.rowId
     */
    _onCollapseRow(ev) {
        ev.stopPropagation();
        this.model.collapseRow(ev.data.rowId);
        this.renderer.updateRow(this.model.get(ev.data.rowId));
    },
    /**
     * Handler for renderer on-connector-end-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorEndDrag(ev) {
        ev.stopPropagation();
        this._draggingConnector = false;
        this.renderer.set_connector_creation_mode(this._draggingConnector);
    },
    /**
     * Handler for renderer on-connector-highlight event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorHighlight(ev) {
        ev.stopPropagation();
        if (!this._updating && !this._draggingConnector) {
            this.renderer.toggleConnectorHighlighting(ev.data.connector, ev.data.highlighted);
        }
    },
    /**
     * Handler for renderer on-connector-start-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onConnectorStartDrag(ev) {
        ev.stopPropagation();
        this._draggingConnector = true;
        this.renderer.set_connector_creation_mode(this._draggingConnector);
    },
    /**
     * Handler for renderer on-create-connector event.
     *
     * @param {OdooEvent} ev
     * @returns {Promise<*>}
     * @private
     */
    async _onCreateConnector(ev) {
        ev.stopPropagation();
        await this.model.createDependency(ev.data.masterId, ev.data.slaveId);
        await this.reload();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onExpandClicked(ev) {
        ev.preventDefault();
        this.model.expandRows();
        this.update({}, { reload: false });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.rowId
     */
    _onExpandRow(ev) {
        ev.stopPropagation();
        this.model.expandRow(ev.data.rowId);
        this.renderer.updateRow(this.model.get(ev.data.rowId));
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onNextPeriodClicked(ev) {
        ev.preventDefault();
        const state = this.model.get();
        this.update({ date: state.focusDate.add(1, state.scale) });
    },
    /**
     * Opens dialog when clicked on pill to view record.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {jQuery} ev.data.target
     */
    async _onPillClicked(ev) {
        if (!this._updating) {
            ev.data.target.addClass('o_gantt_pill_editing');

            // Sync with the mutex to wait for potential changes on the view
            await this.model.mutex.getUnlockedDef();

            const props = { resId: ev.data.target.data('id') };
            const options = { onClose: () => ev.data.target.removeClass('o_gantt_pill_editing') };
            this._openDialog(props, options);
        }
    },
    /**
     * Saves pill information when dragged.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {integer} [ev.data.diff]
     * @param {integer} [ev.data.groupLevel]
     * @param {string} [ev.data.pillId]
     * @param {string} [ev.data.newRowId]
     * @param {string} [ev.data.oldRowId]
     * @param {'copy'|'reschedule'} [ev.data.action]
     */
    _onPillDropped(ev) {
        ev.stopPropagation();

        const state = this.model.get();

        const schedule = {};

        let diff = ev.data.diff;
        diff = this.isRTL ? -diff : diff;
        if (diff) {
            const pill = _.findWhere(state.records, { id: ev.data.pillId });
            schedule[state.dateStartField] = this.model.dateAdd(pill[state.dateStartField], diff, this.SCALES[state.scale].time);
            schedule[state.dateStopField] = this.model.dateAdd(pill[state.dateStopField], diff, this.SCALES[state.scale].time);
        } else if (ev.data.action === 'copy') {
            // When we copy the info on dates is sometimes mandatory (e.g. working on hr.leave, see copy_data)
            const pill = _.findWhere(state.records, { id: ev.data.pillId });
            schedule[state.dateStartField] = pill[state.dateStartField].clone();
            schedule[state.dateStopField] = pill[state.dateStopField].clone();
        }

        if (ev.data.newRowId && ev.data.newRowId !== ev.data.oldRowId) {
            const groupValue = Object.assign({}, ...JSON.parse(ev.data.newRowId));

            // if the pill is dragged in a top level group, we only want to
            // write on fields linked to this top level group
            const fieldsToWrite = state.groupedBy.slice(0, ev.data.groupLevel + 1);
            for (const fieldName of fieldsToWrite) {
                // TODO: maybe not write if the value hasn't changed?
                let valueToWrite = groupValue[fieldName];
                if (Array.isArray(valueToWrite)) {
                    const { type: fieldType } = state.fields[fieldName];
                    if (fieldType === "many2many") {
                        valueToWrite = [valueToWrite[0]];
                    } else if (fieldType === "many2one") {
                        valueToWrite = valueToWrite[0];
                    }
                }
                schedule[fieldName] = valueToWrite;
            }
        }
        if (ev.data.action === 'copy') {
            this._copy(ev.data.pillId, schedule);
        } else {
            this._reschedule(ev.data.pillId, schedule);
        }
    },
    /**
     * Handler for renderer on-connector-end-drag event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onPillHighlight(ev) {
        ev.stopPropagation();
        if (!this._updating || !ev.data.highlighted) {
            await this.renderer.togglePillHighlighting(ev.data.element, ev.data.highlighted);
        }
    },
    /**
     * Save pill information when resized
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onPillResized(ev) {
        ev.stopPropagation();
        const schedule = {};
        schedule[ev.data.field] = ev.data.date;
        this._reschedule(ev.data.id, schedule);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onPillUpdatingStarted(ev) {
        ev.stopPropagation();
        this._updating = true;
        this.renderer.togglePreventConnectorsHoverEffect(true);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onPillUpdatingStopped(ev) {
        ev.stopPropagation();
        this._updating = false;
        this.renderer.togglePreventConnectorsHoverEffect(false);
    },
    /**
     * Opens a dialog to plan records.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCellPlanClicked(ev) {
        ev.stopPropagation();
        const context = this._getDialogContext(ev.data.date, ev.data.rowId);
        this._openPlanDialog(context);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrevPeriodClicked(ev) {
        ev.preventDefault();
        const state = this.model.get();
        this.update({ date: state.focusDate.subtract(1, state.scale) });
    },
    /**
     * Handler for renderer on-remove-connector event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onRemoveConnector(ev) {
        ev.stopPropagation();
        await this.model.removeDependency(ev.data.masterId, ev.data.slaveId);
        await this.reload();
    },
    /**
     * Handler for renderer on-reschedule-according-to-dependency event.
     *
     * @param {OdooEvent} ev
     * @private
     */
    async _onRescheduleAccordingToDependency(ev) {
        ev.stopPropagation();
        const result = await this.model.rescheduleAccordingToDependency(
            ev.data.direction,
            ev.data.masterId,
            ev.data.slaveId);
        if (result === false) {
            return
        } else {
            await this.reload();
            if (result.type == 'ir.actions.client') {
                this.do_action(result);
            }
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onScaleClicked(ev) {
        ev.preventDefault();
        const $button = $(ev.currentTarget);
        if ($button.hasClass('active')) {
            return;
        }
        this.update({ scale: $button.data('value') });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onTodayClicked(ev) {
        ev.preventDefault();
        this.update({ date: moment() });
    },
});

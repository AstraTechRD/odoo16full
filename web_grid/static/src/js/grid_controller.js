odoo.define('web_grid.GridController', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');
var config = require('web.config');
var core = require('web.core');
var utils = require('web.utils');
var concurrency = require('web.concurrency');

const { escape } = require("@web/core/utils/strings");
const { FormViewDialog } = require("@web/views/view_dialogs/form_view_dialog");

var qweb = core.qweb;
var _t = core._t;

const { Component, markup } = owl;

var GridController = AbstractController.extend({
    custom_events: Object.assign({}, AbstractController.prototype.custom_events, {
        'create_inline': '_addLine',
        'cell_edited': '_onCellEdited',
        'open_cell_information': '_onOpenCellInformation',
    }),

    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.context = params.context;
        this.navigationButtons = params.navigationButtons;
        this.ranges = params.ranges;
        this.currentRange = params.currentRange;
        this.formViewID = params.formViewID;
        this.listViewID = params.listViewID;
        this.adjustment = params.adjustment;
        this.adjustName = params.adjustName;
        this.canCreate = params.activeActions.create;
        this.createInline = params.createInline;
        this.displayEmpty = params.displayEmpty;
        this.mutex = new concurrency.Mutex();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQuery} [$node]
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('grid.GridArrows', {
            widget: {
                _ranges: this.ranges,
                _buttons: this.navigationButtons,
                allowCreate: this.canCreate,
            },
            isMobile: config.device.isMobile
        }));
        this.$buttons.on('click', '.o_grid_button_add', this._onAddLine.bind(this));
        this.$buttons.on('click', '.grid_arrow_previous', this._onPaginationChange.bind(this, 'prev'));
        this.$buttons.on('click', '.grid_button_initial', this._onPaginationChange.bind(this, 'initial'));
        this.$buttons.on('click', '.grid_arrow_next', this._onPaginationChange.bind(this, 'next'));
        this.$buttons.on('click', '.grid_arrow_range', this._onRangeChange.bind(this));
        this.$buttons.on('click', '.grid_arrow_button', this._onButtonClicked.bind(this));
        this.updateButtons();
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    /**
     * @override
     */
    updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        const state = this.model.get();
        this.$buttons.find('.o_grid_button_add').toggleClass('d-none', this.createInline && (!!state.data[0].rows.length || this.displayEmpty));
        this.$buttons.find('.grid_arrow_previous').toggleClass('d-none', !state.data[0].prev);
        this.$buttons.find('.grid_arrow_next').toggleClass('d-none', !state.data[0].next);
        this.$buttons.find('.grid_button_initial').toggleClass('d-none', !state.data[0].initial);
        this.$buttons.find('.grid_arrow_range').removeClass('active');
        this.$buttons.find('.grid_arrow_range[data-name=' + this.currentRange + ']').addClass('active');
    },
    /**
     * Get the action to execute.
     */
    _getEventAction(label, cell, ctx) {
        const noActivitiesFound = _t('No activities found');
        return {
            type: 'ir.actions.act_window',
            name: label,
            res_model: this.modelName,
            views: [
                [this.listViewID, 'list'],
                [this.formViewID, 'form']
            ],
            domain: cell.domain,
            context: ctx,
            help: markup(`<p class='o_view_nocontent_smiling_face'>${escape(noActivitiesFound)}</p>`),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the context for the form view.
     * @private
     */
    _getFormContext() {
        return Object.assign({}, this.model.getContext(), { view_grid_add_line: true });
    },

    /**
     * @private
     * @returns {object}
     */
    _getFormDialogOptions() {
        const formContext = this._getFormContext();
        // TODO: document quick_create_view (?) context key
        var formViewID = formContext.quick_create_view || this.formViewID || false;
        return {
            resModel: this.modelName,
            resId: false,
            context: formContext,
            viewId: formViewID,
            title: _t("Add a Line"),
            onRecordSaved: this.reload.bind(this, {}),
        };
    },

    /**
     * Open a form View to create a new entry in the grid
     * @private
     */
    _addLine() {
        const options = this._getFormDialogOptions()
        Component.env.services.dialog.add(FormViewDialog, options);
    },
    /**
     * @private
     * @param {Object} cell
     * @param {number} newValue
     * @returns {Promise}
     */
    _adjust: function (cell, newValue) {
        var difference = newValue - cell.value;
        // 1e-6 is probably an overkill, but that way milli-values are usable
        if (Math.abs(difference) < 1e-6) {
            // cell value was set to itself, don't hit the server
            return Promise.resolve();
        }
        // convert row values to a domain, concat to action domain
        var state = this.model.get();
        var domain = this.model.domain.concat(cell.row.domain);
        // early rendering of the new value.
        // FIXME: only the model should modify the state, so in master
        // move the _adjust method in the model so that it can properly
        // handle "pending" data
        utils.into(state.data, cell.cell_path).value = newValue;

        var self = this;
        return this.mutex.exec(function () {
            if (self.adjustment === 'action') {
                const actionData = {
                    type: self.adjustment,
                    name: self.adjustName,
                    context: self.model.getContext({
                        grid_adjust: { // context for type=action
                            row_domain: domain,
                            column_field: state.colField,
                            column_value: cell.col.values[state.colField][0],
                            cell_field: state.cellField,
                            change: difference,
                        },
                    }),
                };
                return self.trigger_up('execute_action', {
                    action_data: actionData,
                    env: {
                        context: self.model.getContext(),
                        model: self.modelName
                    },
                    on_success: async function () {
                        let state = self.model.get();
                        await self.model.reloadCell(cell, state.cellField, state.colField);
                        state = self.model.get();
                        await self.renderer.update(state);
                        self.updateButtons(state);
                    },
                });
            }
            return self._rpc({
                model: self.modelName,
                method: self.adjustName,
                args: [ // args for type=object
                    [],
                    domain,
                    state.colField,
                    cell.col.values[state.colField][0],
                    state.cellField,
                    difference
                ],
                context: self.model.getContext()
            }).then(function () {
                return self.model.reloadCell(cell, state.cellField, state.colField);
            }).then(function () {
                var state = self.model.get();
                return self.renderer.update(state);
            }).then(function () {
                self.updateButtons(state);
            });
        });
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _update: function () {
        return this._super.apply(this, arguments)
            .then(this.updateButtons.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddLine: function (event) {
        event.preventDefault();
        this._addLine();
    },

    /**
     * If something needs to be done when a new value has been set, it can be done here
     * @param ev the event that triggered the update
     */
    _cellHasBeenUpdated(ev) {
        // Currently overriden in timesheet_grid.timesheet_grid_controller
    },

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onCellEdited: function (event) {
        var state = this.model.get();
        this._adjust({
            row: utils.into(state.data, event.data.row_path),
            col: utils.into(state.data, event.data.col_path),
            value: utils.into(state.data, event.data.cell_path).value,
            cell_path: event.data.cell_path,
        }, event.data.value)
        .then(() => {
            if (event.data.doneCallback !== undefined) {
                event.data.doneCallback();
            }
            this._cellHasBeenUpdated(event);
        })
        .guardedCatch(function () {
            if (event.data.doneCallback !== undefined) {
                event.data.doneCallback();
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onButtonClicked: function (e) {
        var self = this;
        e.stopPropagation();
        // TODO: maybe allow opting out of getting ids?
        var button = this.navigationButtons[$(e.target).attr('data-index')];
        var actionData = _.extend({}, button, {
            context: this.model.getContext(button.context),
        });
        this.model.getIds().then(function (ids) {
            self.trigger_up('execute_action', {
                action_data: actionData,
                env: {
                    context: self.model.getContext(),
                    model: self.modelName,
                    resIDs: ids,
                },
                on_closed: self.reload.bind(self, {}),
            });
        });
    },
    /**
     * @private
     * @param {OwlEvent} ev
     */
    _onOpenCellInformation: function (ev) {
        var cell_path = ev.data.path.split('.');
        var row_path = cell_path.slice(0, -3).concat(['rows'], cell_path.slice(-2, -1));
        var state = this.model.get();
        var cell = utils.into(state.data, cell_path);
        var row = utils.into(state.data, row_path);

        var groupFields = state.groupBy.slice(state.isGrouped ? 1 : 0);
        var label = _.filter(_.map(groupFields, function (g) {
            return row.values[g][1];
        }), function (g) {
            return g;
        }).join(' - ');
        // pass group by, section and col fields as default in context
        var cols_path = cell_path.slice(0, -3).concat(['cols'], cell_path.slice(-1));
        var col = utils.into(state.data, cols_path);
        var column_value = col.values[state.colField][0];
        if (!column_value) {
            column_value = false;
        } else if (!_.isNumber(column_value)) {
            column_value = column_value.split("/")[0];
        }
        var ctx = _.extend({}, this.context);
        if (this.model.sectionField && state.groupBy && state.groupBy[0] === this.model.sectionField) {
            var value = state.data[parseInt(cols_path[0])].__label;
            ctx['default_' + this.model.sectionField] = _.isArray(value) ? value[0] : value;
        }
        _.each(groupFields, function (field) {
            ctx['default_' + field] = row.values[field][0] || false;
        });

        ctx['default_' + state.colField] = column_value;

        ctx['create'] = this.canCreate && !cell.readonly;
        ctx['edit'] = this.activeActions.edit && !cell.readonly;
        this.do_action(this._getEventAction(label, cell, ctx));
    },
    /**
     * @private
     * @param {string} dir either 'prev', 'initial' or 'next
     */
    _onPaginationChange: function (dir) {
        var state = this.model.get();
        this.update({pagination: state.data[0][dir]});
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onRangeChange: function (e) {
        e.stopPropagation();
        var $target = $(e.target);
        if (config.device.isMobile) {
            $target.closest(".dropdown-menu").prev().dropdown("toggle");
        }
        if ($target.hasClass('active')) {
            return;
        }
        this.currentRange = $target.attr('data-name');

        this.context.grid_range = this.currentRange;
        this.update({range: this.currentRange});
    },
});

return GridController;

});

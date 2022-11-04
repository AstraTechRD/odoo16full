odoo.define('web_grid.GridView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var config = require('web.config');
var core = require('web.core');
var GridModel = require('web_grid.GridModel');
var GridController = require('web_grid.GridController');
var GridRenderer = require('web_grid.GridRenderer');
var viewRegistry = require('web.view_registry');
var pyUtils = require('web.py_utils');
const RendererWrapper = require('web.RendererWrapper');

var _t = core._t;
var _lt = core._lt;

var GridView = AbstractView.extend({
    display_name: _lt('Grid'),
    mobile_friendly: true,
    icon: 'fa fa-th',
    config: _.extend({}, AbstractView.prototype.config, {
        Model: GridModel,
        Controller: GridController,
        Renderer: GridRenderer,
    }),
    viewType: 'grid',
    init: function (viewInfo, params) {
        var self = this;
        this._super.apply(this, arguments);
        var arch = this.arch;
        var fields = this.fields;
        var rowFields = [];
        var sectionField, colField, cellField, ranges, cellComponent, cellComponentOptions, measureLabel, readonlyField;
        _.each(arch.children, function (child) {
            if (child.tag === 'field') {
                if (child.attrs.type === 'row') {
                    if (child.attrs.section === '1' && !sectionField) {
                        sectionField = child.attrs.name;
                    }
                    rowFields.push(child.attrs.name);
                }
                if (child.attrs.type === 'col') {
                    colField = child.attrs.name;
                    ranges = self._extract_ranges(child, params.context);
                }
                if (child.attrs.type === 'measure') {
                    cellField = child.attrs.name;
                    cellComponent = child.attrs.widget;
                    if (child.attrs.options) {
                        cellComponentOptions = JSON.parse(child.attrs.options.replace(/'/g, '"'));
                    }
                    measureLabel = child.attrs.string;
                }
                if (child.attrs.type === 'readonly') {
                    readonlyField = child.attrs.name;
                }
            }
        });

        // model
        this.loadParams.ranges = ranges;
        let default_range_name = config.device.isMobile ? 'day' : '';
        ranges.forEach(range => {
            if (range['name'] === 'week' && !config.device.isMobile) {
                default_range_name = range['name'];
            }
        })
        let contextRangeName = params.context.grid_range || default_range_name;
        var contextRange = contextRangeName && _.findWhere(ranges, {name: contextRangeName});
        this.loadParams.fields = this.fields;
        this.loadParams.currentRange = contextRange || ranges[0];
        this.loadParams.rowFields = rowFields;
        this.loadParams.sectionField = sectionField;
        this.loadParams.colField = colField;
        this.loadParams.cellField = cellField;
        this.loadParams.groupedBy = params.groupBy;
        this.loadParams.readonlyField = readonlyField;

        // renderer
        this.rendererParams.canCreate = this.controllerParams.activeActions.create;
        this.rendererParams.fields = fields;
        this.rendererParams.measureLabel = measureLabel;
        this.rendererParams.editableCells = !!(this.controllerParams.activeActions.edit && arch.attrs.adjustment);
        this.rendererParams.cellComponent = cellComponent;
        this.rendererParams.cellComponentOptions = cellComponentOptions;
        this.rendererParams.hideLineTotal = !!JSON.parse(arch.attrs.hide_line_total || '0');
        this.rendererParams.hideColumnTotal = !!JSON.parse(arch.attrs.hide_column_total || '0');
        this.rendererParams.hasBarChartTotal = !!JSON.parse(arch.attrs.barchart_total || '0');
        this.rendererParams.createInline = !!JSON.parse(arch.attrs.create_inline || 'false');
        this.rendererParams.displayEmpty = !!JSON.parse(arch.attrs.display_empty || 'false');
        this.rendererParams.noContentHelp = (!this.rendererParams.displayEmpty && this.rendererParams.noContentHelp) || "";

        // controller
        this.controllerParams.formViewID = false;
        this.controllerParams.listViewID = false;
        _.each(params.actionViews, function (view) {
            if (view.type === 'form') {
                self.controllerParams.formViewID = view.viewID;
            }
            if (view.type === 'list') {
                self.controllerParams.listViewID = view.viewID;
            }
        });
        this.controllerParams.context = params.context;
        this.controllerParams.ranges = ranges;
        this.controllerParams.currentRange = this.loadParams.currentRange.name;
        this.controllerParams.navigationButtons = arch.children
            .filter(function (c) { return c.tag === 'button'; })
            .map(function (c) { return c.attrs; });
        this.controllerParams.adjustment = arch.attrs.adjustment;
        this.controllerParams.adjustName = arch.attrs.adjust_name;
        this.controllerParams.createInline = this.rendererParams.createInline;
        this.controllerParams.displayEmpty = this.rendererParams.displayEmpty;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getRenderer(parent, state) {
        state = Object.assign({}, state, this.rendererParams);
        return new RendererWrapper(null, this.config.Renderer, state);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Extract the range to display on the view, and filter
     * them according they should be visible or not (attribute 'invisible')
     *
     * @private
     * @param {node} col_node - the node of 'col' in grid view arch definition
     * @param {Object} context - the context used to instanciate the view
     * @returns {Array<{name: string, string: string, span: string, step: string}>}
     */
    _extract_ranges: function(col_node, context) {
        let ranges = [];
        const pyevalContext = py.dict.fromJSON(context || {});
        for (const range of col_node.children.map(node => node.attrs)) {
            if (range.invisible && pyUtils.py_eval(range.invisible, { 'context': pyevalContext })) {
                continue;
            }
            ranges.push(range);
        }
        if (config.device.isMobile && !ranges.find(r => r.name === 'day')) {
            ranges.unshift({
                name: 'day',
                string: _t('Day'),
                span: 'day',
                step: 'day',
            });
        }
        return ranges;
    },

});

viewRegistry.add('grid', GridView);

return GridView;
});

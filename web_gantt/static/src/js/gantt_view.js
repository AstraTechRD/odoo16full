/** @odoo-module alias=web_gantt.GanttView */

import AbstractView from 'web.AbstractView';
import core from 'web.core';
import GanttModel from 'web_gantt.GanttModel';
import GanttRenderer from 'web_gantt.GanttRenderer';
import GanttController from 'web_gantt.GanttController';
import pyUtils from 'web.py_utils';
import view_registry from 'web.view_registry';

const _t = core._t;
const _lt = core._lt;

const GanttView = AbstractView.extend({
    display_name: _lt('Gantt'),
    icon: 'fa fa-tasks',
    config: _.extend({}, AbstractView.prototype.config, {
        Model: GanttModel,
        Controller: GanttController,
        Renderer: GanttRenderer,
    }),
    jsLibs: [
        '/web/static/lib/nearest/jquery.nearest.js',
    ],
    viewType: 'gantt',

    /**
     * @override
     */
    init(viewInfo, params) {
        this._super.apply(this, arguments);

        const { domain } = params.action || {};
        this.controllerParams.actionDomain = domain || [];

        this.SCALES = {
            day: { string: _t('Day'), hotkey: 'e', cellPrecisions: { full: 60, half: 30, quarter: 15 }, defaultPrecision: 'full', time: 'minutes', interval: 'hour' },
            week: { string: _t('Week'), hotkey: 'p', cellPrecisions: { full: 24, half: 12 }, defaultPrecision: 'half', time: 'hours', interval: 'day' },
            month: { string: _t('Month'), hotkey: 'm', cellPrecisions: { full: 24, half: 12 }, defaultPrecision: 'half', time: 'hours', interval: 'day' },
            year: { string: _t('Year'), hotkey: 'y', cellPrecisions: { full: 1 }, defaultPrecision: 'full', time: 'months', interval: 'month' },
        };

        const arch = this.arch;

        // Decoration fields
        const decorationFields = [];
        _.each(arch.children, (child) => {
            if (child.tag === 'field') {
                decorationFields.push(child.attrs.name);
            }
        });

        let collapseFirstLevel = !!arch.attrs.collapse_first_level;

        // Unavailability
        const displayUnavailability = !!arch.attrs.display_unavailability;

        // Colors
        const colorField = arch.attrs.color;

        // Cell precision
        // precision = {'day': 'hour:half', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}
        const precisionAttrs = arch.attrs.precision ? pyUtils.py_eval(arch.attrs.precision) : {};
        const cellPrecisions = {};
        _.each(this.SCALES, (vals, key) => {
            if (precisionAttrs[key]) {
                const precision = precisionAttrs[key].split(':'); // hour:half
                // Note that precision[0] (which is the cell interval) is not
                // taken into account right now because it is no customizable.
                if (precision[1] && _.contains(_.keys(vals.cellPrecisions), precision[1])) {
                    cellPrecisions[key] = precision[1];
                }
            }
            cellPrecisions[key] = cellPrecisions[key] || vals.defaultPrecision;
        });

        let consolidationMaxField;
        let consolidationMaxValue;
        const consolidationMax = arch.attrs.consolidation_max ? pyUtils.py_eval(arch.attrs.consolidation_max) : {};
        if (Object.keys(consolidationMax).length > 0) {
            consolidationMaxField = Object.keys(consolidationMax)[0];
            consolidationMaxValue = consolidationMax[consolidationMaxField];
            // We need to display the aggregates even if there is only one groupby
            collapseFirstLevel = !!consolidationMaxField || collapseFirstLevel;
        }

        const consolidationParams = {
            field: arch.attrs.consolidation,
            maxField: consolidationMaxField,
            maxValue: consolidationMaxValue,
            excludeField: arch.attrs.consolidation_exclude,
        };

        // form view which is opened by gantt
        let formViewId = arch.attrs.form_view_id ? parseInt(arch.attrs.form_view_id, 10) : false;
        if (params.action && !formViewId) { // fallback on form view action, or 'false'
            const result = _.findWhere(params.action.views, { type: 'form' });
            formViewId = result ? result.viewID : false;
        }
        const dialogViews = [[formViewId, 'form']];

        let allowedScales;
        if (arch.attrs.scales) {
            const possibleScales = Object.keys(this.SCALES);
            allowedScales = _.reduce(arch.attrs.scales.split(','), (allowedScales, scale) => {
                if (possibleScales.indexOf(scale) >= 0) {
                    allowedScales.push(scale.trim());
                }
                return allowedScales;
            }, []);
        } else {
            allowedScales = Object.keys(this.SCALES);
        }

        const scale = params.context.default_scale || arch.attrs.default_scale || 'month';
        const initialDate = moment(params.context.initialDate || params.initialDate || arch.attrs.initial_date || new Date());
        const offset = arch.attrs.offset;
        if (offset && scale) {
            initialDate.add(offset, scale);
        }

        // thumbnails for groups (display a thumbnail next to the group name)
        const thumbnails = this.arch.attrs.thumbnails ? pyUtils.py_eval(this.arch.attrs.thumbnails) : {};
        // plan option
        const canPlan = this.arch.attrs.plan ? !!JSON.parse(this.arch.attrs.plan) : true;
        // cell create option
        const canCellCreate = this.arch.attrs.cell_create ? !!JSON.parse(this.arch.attrs.cell_create) : true;

        // Dependencies
        const dependencyField = !!this.arch.attrs.dependency_field && this.arch.attrs.dependency_field;
        const dependencyInvertedField = !!this.arch.attrs.dependency_inverted_field && this.arch.attrs.dependency_inverted_field;
        if (dependencyField) {
            decorationFields.push(dependencyField);
        }

        this.controllerParams.context = params.context || {};
        this.controllerParams.dialogViews = dialogViews;
        this.controllerParams.SCALES = this.SCALES;
        this.controllerParams.allowedScales = allowedScales;
        this.controllerParams.collapseFirstLevel = collapseFirstLevel;
        this.controllerParams.createAction = arch.attrs.on_create || null;

        this.loadParams.initialDate = initialDate;
        this.loadParams.collapseFirstLevel = collapseFirstLevel;
        this.loadParams.colorField = colorField;
        this.loadParams.dateStartField = arch.attrs.date_start;
        this.loadParams.dateStopField = arch.attrs.date_stop;
        this.loadParams.progressField = arch.attrs.progress;
        this.loadParams.decorationFields = decorationFields;
        this.loadParams.defaultGroupBy = this.arch.attrs.default_group_by;
        this.loadParams.permanentGroupBy = this.arch.attrs.permanent_group_by;
        this.loadParams.dynamicRange = this.arch.attrs.dynamic_range;
        this.loadParams.displayUnavailability = displayUnavailability;
        this.loadParams.fields = this.fields;
        this.loadParams.scale = scale;
        this.loadParams.SCALES = this.SCALES;
        this.loadParams.consolidationParams = consolidationParams;
        this.loadParams.progressBarFields = arch.attrs.progress_bar;

        this.modelParams.dependencyField = dependencyField;
        this.modelParams.dependencyInvertedField = dependencyInvertedField;

        this.rendererParams.canCreate = this.controllerParams.activeActions.create;
        this.rendererParams.canCellCreate = canCellCreate;
        this.rendererParams.canEdit = this.controllerParams.activeActions.edit;
        this.rendererParams.canPlan = canPlan && this.rendererParams.canEdit;
        this.rendererParams.fieldsInfo = viewInfo.fields;
        this.rendererParams.SCALES = this.SCALES;
        this.rendererParams.cellPrecisions = cellPrecisions;
        this.rendererParams.totalRow = arch.attrs.total_row || false;
        this.rendererParams.string = arch.attrs.string || _t('Gantt View');
        this.rendererParams.popoverTemplate = _.findWhere(arch.children, {tag: 'templates'});
        this.rendererParams.colorField = colorField;
        this.rendererParams.disableDragdrop = arch.attrs.disable_drag_drop ? !!JSON.parse(arch.attrs.disable_drag_drop) : false;
        this.rendererParams.progressField = arch.attrs.progress;
        this.rendererParams.displayUnavailability = displayUnavailability;
        this.rendererParams.collapseFirstLevel = collapseFirstLevel;
        this.rendererParams.consolidationParams = consolidationParams;
        this.rendererParams.thumbnails = thumbnails;
        this.rendererParams.progressBarFields = arch.attrs.progress_bar;
        this.rendererParams.pillLabel = !!arch.attrs.pill_label;
        this.rendererParams.dependencyEnabled = !!this.modelParams.dependencyField
        this.rendererParams.dependencyField = this.modelParams.dependencyField
    },
});

view_registry.add('gantt', GanttView);

export default GanttView;

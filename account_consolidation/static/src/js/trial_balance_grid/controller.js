odoo.define('account_consolidation.GridController', function (require) {
    "use strict";

    var WebGridController = require('web_grid.GridController');
    const { FormViewDialog } = require("@web/views/view_dialogs/form_view_dialog");
    var core = require('web.core');

    var _t = core._t;
    const { Component } = owl;

    return WebGridController.extend({
        renderButtons(...args) {
            this._super(...args);
            if (this.context.default_period_id) {
                const $view_report_btn = $('<button class="btn btn-secondary o_grid_button_view_report" type="button" role="button"/>')
                    .text(_t('Consolidated balance'))
                    .on('click', this._onViewReport.bind(this));
                this.$buttons.prepend($view_report_btn);
                const $add_col_btn = $('<button class="btn btn-primary o_grid_button_add" type="button" role="button"/>')
                    .text(_t('Add a column'))
                    .on('click', this._onAddColumn.bind(this));
                this.$buttons.prepend($add_col_btn);
            }
        },
        _onAddColumn(e) {
            e.preventDefault();
            Component.env.services.dialog.add(FormViewDialog, {
                resModel: 'consolidation.journal',
                context: { default_period_id: this.context.default_period_id },
                title: _t('Add a column'),
                onRecordSaved: this.reload.bind(this, {})
            });
        },
        _onViewReport(e) {
            e.preventDefault();
            this.do_action('account_consolidation.trial_balance_report_action', {
                additional_context:{
                    default_period_id: this.context.default_period_id
                }
            });
        }
    });
});

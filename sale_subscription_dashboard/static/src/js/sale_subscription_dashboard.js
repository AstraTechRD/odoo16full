odoo.define('sale_subscription_dashboard.dashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var datepicker = require('web.datepicker');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var relational_fields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var ajax = require('web.ajax');
const { WarningDialog } = require("@web/legacy/js/_deprecated/crash_manager_warning_dialog");

var FieldMany2ManyTags = relational_fields.FieldMany2ManyTags;
var _t = core._t;
var QWeb = core.qweb;

var DATE_FORMAT = time.getLangDateFormat();
var FORMAT_OPTIONS = {
    // allow to decide if utils.human_number should be used
    humanReadable: function (value) {
        return Math.abs(value) >= 1000;
    },
    // with the choices below, 1236 is represented by 1.24k
    minDigits: 1,
    decimals: 2,
    // avoid comma separators for thousands in numbers when human_number is used
    formatterCallback: function (str) {
        return str;
    },
};

function dateToServer (date, fieldType) {
    date = date.clone().locale('en');
    if (fieldType === "date") {
        return date.local().format('YYYY-MM-DD');
    }
    return date.utc().format('YYYY-MM-DD HH:mm:ss');
}

/*

ABOUT

In this module, you'll find two main widgets : one that represents the Revenue KPIs dashboard
and one that represents the salesman dashboard.

In both of them, there are two steps of rendering : one that renders the main template that leaves
empty sections for the rendering of the second step. This second step can take some time to be rendered
because of the calculation and is then rendered separately.

*/

// Abstract widget with common methods
var sale_subscription_dashboard_abstract = AbstractAction.extend(StandaloneFieldManagerMixin, {
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    hasControlPanel: true,

    events: {
        'click .js_foldable_trigger': 'preventMenuFold',
        'click .js_subscription_dashboard_date_filter': 'handleDateSelection'
    },

    /**
     * @constructor
     */
    init: function (parent, action) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.$dateFilter = undefined;
        this.contract_templates = [];
        this.companies = [];
        this.tags = [];
        this.sales_team = [];
        this.dashboard_options = {
            filter: 'last_month',
            ranges: {
                this_quarter: {date_from: undefined, date_to: undefined},
                this_year: {date_from: undefined, date_to: undefined},
                last_quarter: {date_from: undefined, date_to: undefined},
                last_year: {date_from: undefined, date_to: undefined},
                this_month: {date_from: undefined, date_to: undefined},
                last_month: {date_from: undefined, date_to: undefined},
            }

        };
    },

    willStart: function() {
        return Promise.all(
            [this._super.apply(this, arguments),
            this.fetch_data()]
        );
    },

    start: async function () {
        await this._super();
        this.render_dashboard();
    },

    on_reverse_breadcrumb: function() {
        this.update_cp();
        web_client.do_push_state({action: this.main_dashboard_action_id});
    },

    load_action: function(view_xmlid, options) {
        var self = this;
        // FIXME
        // options to make the doAction should be at the root of that object
        // the info for the action itself should be in props of that object.
        // For now, put those keys everywhere....
        const doActionOptions = Object.assign({}, options, { props : _.omit(options, ['additional_context', 'push_main_state']) });
        doActionOptions.on_reverse_breadcrumb = this.on_reverse_breadcrumb;
        if (options.push_main_state && self.main_dashboard_action_id) {
            // Reset the pushState prevents a traceback when the back button is used from a detailed dashboard.
            // The forward button does nothing.
            options.pushState = false;
        }
        return this.do_action(view_xmlid, doActionOptions).then(function() {
            // ARJ: When the subscriptions dashboard will be rewritten in OWL, the current behavior have to be improved:
            // * keep the current graph when user refresh the page.
            // * Allows to use back and forward buttons.

            // The following lines allows to refresh the page when a detailed dashboard is displayed.
            // The main dashboard is then showed without error message.
            // loadstate restores the main dashboard.
            if (options.push_main_state && self.main_dashboard_action_id) {
                web_client.do_push_state({action: self.main_dashboard_action_id});
            }
        });
    },

    convert_dates: function (string_ranges) {
        /*
            Convert the dates ranges provided by the backend to javascript Moments.
            string_ranges: object containing the date ranges.
            Same properties than `this.dashboard_options.ranges`
            with the difference that the dates are formatted strings ('YYYY-MM-DD').
        */
        const ranges = {};
        for (const element in string_ranges) {
            ranges[element] = {
                'date_from': moment(string_ranges[element].date_from),
                'date_to': moment(string_ranges[element].date_to)
            };
        }
        return ranges;
    },

    on_update_options: function() {
        this.filters.template_ids = this.get_filtered_template_ids();
        this.filters.tag_ids = this.get_filtered_tag_ids();
        this.filters.sale_team_ids = this.get_filtered_sales_team_ids();

        var company_ids = this.get_filtered_company_ids();

        if (!company_ids || !company_ids.length) {
            Dialog.alert(this, _t('Select at least one company.'), {
                title: _t('Warning'),
            });
            return;
        }

        var self = this;
        return self._rpc({
                route: '/sale_subscription_dashboard/companies_check',
                params: {
                    company_ids: company_ids,
                    context: session.user_context
                },
            }, {shadow: true}).then(function (response) {
                if (response.result === true) {
                    self.currency_id = response.currency_id;
                    self.filters.company_ids = company_ids;
                    self.$('.o_content').empty();
                    self.render_dashboard();
                } else {
                    Dialog.alert(self, response.error_message, {
                        title: _t('Warning'),
                    });
                }
        });
    },

    get_filtered_template_ids: function() {
        var $contract_inputs = this.$searchview.find(".o_contract_template_filter.selected");
        return _.map($contract_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_tag_ids: function() {
        var $tag_inputs = this.$searchview.find(".o_tags_filter.selected");
        return _.map($tag_inputs, function(el) { return $(el).data('id'); });
    },

    get_filtered_company_ids: function() {
        if (this.companies && this.companies.length === 1) {
            return [this.companies[0].id];
        } else {
            var $company_inputs = this.$searchview.find(".o_companies_filter.selected");
            return _.map($company_inputs, function(el) { return $(el).data('id'); });
        }
    },

    get_filtered_sales_team_ids: function() {
        var $sales_team_inputs = this.$searchview.find(".o_sales_team_filter.selected");
        return _.map($sales_team_inputs, function(el) { return $(el).data('id'); });
    },

    render_filters: function() {
        var self = this;
        if (this.contract_templates.length || this.companies.length || this.tags.length || this.sales_team.length) {
            self.$searchview = $(QWeb.render("sale_subscription_dashboard.dashboard_option_filters", {widget: this}));
        }
        this.$searchview.on('click', '.js_tag', function(e) {
            e.preventDefault();
            $(e.target).toggleClass('selected');
        });
        // Check the boxes if it was already checked before the update
        _.each(this.filters.template_ids, function(id) {
            self.$searchview.find('.o_contract_template_filter[data-id=' + id + ']').addClass('selected');
        });
        _.each(this.filters.tag_ids, function(id) {
            self.$searchview.find('.o_tags_filter[data-id=' + id + ']').addClass('selected');
        });
        _.each(this.filters.company_ids, function(id) {
            self.$searchview.find('.o_companies_filter[data-id=' + id + ']').addClass('selected');
        });
        _.each(this.filters.sale_team_ids, function(id) {
            self.$searchview.find('.o_sales_team_filter[data-id=' + id + ']').addClass('selected');
        });
    },

    update_cp: function() {
        this.updateControlPanel({
            cp_content: this.render_controlpanel_content()
        });
    },

    render_controlpanel_content: function() {
        const PeriodChange = this.$searchview &&
        this.dashboard_options.filter !== this.$searchview.find('.o_predefined_range.selected').data('filter');
        if (!this.$searchview || PeriodChange) {
            this.render_filters();
            this.$searchview.filter('.o_update_options').on('click', this.on_update_options);
            this.set_up_datetimepickers({});
        }
        return {
            $searchview: this.$searchview,
            $buttons: this.$cpButton,
        };
    },

    set_up_datetimepickers: function (datetimeContext) {
        /*
            Datetime picker handler: create the datetime widget, render the filter.
            datetimeContext: the behavior differs if called from the KPI dashboard or the salesman
            dashboard.
            Without context: this.$searchview is a list of jquery elements, it can be filtered.
            With the salesman context: this.$searchview is a single jquery element, we can use find
            on it.
        */
        const dates_options = {
            filter: this.dashboard_options.filter,
            date_from: this.start_date.format('YYYY-MM-DD'),
            date_to: this.end_date.format('YYYY-MM-DD'),
        };
        this.$dateFilter = $(QWeb.render("sale_subscription_dashboard.date_filter", dates_options));
        if (datetimeContext.salesman) {
            this.$searchview.find('.o_subscription_dashboard_filter_date').append(this.$dateFilter);
        } else {
            this.$searchview.filter('.o_subscription_dashboard_filter_date').append(this.$dateFilter);
        }
        const $dateTimePickers = this.$searchview.find('.js_subscription_dashboard_datetimepicker');
        const options = { // Set the options for the datetimepickers
            locale : moment.locale(),
            format : 'L',
            icons: {
                date: "fa fa-calendar",
            },
        };
        const self = this;
        // attach datepicker
        $dateTimePickers.each(function () {
            const name = $(this).find('input').attr('name');
            const defaultValue = $(this).data('default-value');
            $(this).datetimepicker(options);
            const dt = new datepicker.DateWidget(options);
            dt.replace($(this)).then(function () {
                dt.$el.find('input').attr('name', name);
                if (defaultValue) { // Set its default value if there is one
                    dt.setValue(moment(defaultValue));
                }
            });
        });
         //format date that needs to be show in user lang
         this.$dateFilter.find('.js_format_date').each(function (key, dt) {
             const date_value = $(dt).html();
             $(dt).html((new moment(date_value, 'YYYY-MM-DD')).format('ll'));
         });
         // fold all menu$dateFilter
         this.$dateFilter.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$dateFilter.find('.o_foldable_menu[data-filter="' + $(this).data('filter') + '"]').toggleClass('o_closed_menu');
        });
        // render filter (add selected class to the options that are selected)
        this.$searchview.find('[data-filter="' + this.dashboard_options.filter + '"]').addClass('selected');
    },

    preventMenuFold: function (e) {
        // prevent the custom date selector menu to close the whole menu
        e.stopPropagation();
    },

    handleDateSelection: function (e) {
        /*
            Update the options upon date selection.
            Values are retrieved from the widget or the selected item in the list of predefined periods.
            dashboard_options are set accordingly.
        */
        this.dashboard_options.filter = $(e.currentTarget).data('filter');
        let error = false;
        if ($(e.currentTarget).data('filter') === 'custom') {
            const dateFrom = this.$searchview.find('.o_datepicker_input[name="date_from"]');
            const dateTo = this.$searchview.find('.o_datepicker_input[name="date_to"]');
            if (dateFrom.length > 0) {
                error = dateFrom.val() === "" || dateTo.val() === "";
                this.start_date = field_utils.parse.date(dateFrom.val());
                this.end_date = field_utils.parse.date(dateTo.val());
            } else {
                error = dateTo.val() === "";
                this.end_date = field_utils.parse.date(dateTo.val());
            }
        } else if ($(e.currentTarget).hasClass('o_predefined_range')) {
            this.start_date = this.dashboard_options.ranges[this.dashboard_options.filter].date_from;
            this.end_date = this.dashboard_options.ranges[this.dashboard_options.filter].date_to;
        }

        if (error) {
            new WarningDialog(this, {
                title: _t("Odoo Warning"),
            }, {
                message: _t("Date cannot be empty")
            }).open();
        } else {
            this.on_update_options();
        }
    },

    render_dashboard: function() {}, // Abstract

    fetch_data: function() {}, // Abstract

    format_number: function(value, symbol) {
        value = value || 0.0; // sometime, value is 'undefined'
        value = utils.human_number(value);
        if (symbol === 'currency') {
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + symbol;
        }
    },
});

// 1. Main dashboard
var sale_subscription_dashboard_main = sale_subscription_dashboard_abstract.extend({
    events: Object.assign({}, sale_subscription_dashboard_abstract.prototype.events, {
        'click .on_stat_box': 'on_stat_box',
        'click .on_forecast_box': 'on_forecast_box',
        'click .on_demo_contracts': 'on_demo_contracts',
        'click .on_demo_templates': 'on_demo_templates',
    }),

    init: function(parent, action) {
        this._super.apply(this, arguments);

        this.main_dashboard_action_id = action.id;
        this.start_date = moment().subtract(1, 'M').startOf('month');
        this.end_date = moment().subtract(1, 'M').endOf('month');

        this.filters = {
            template_ids: [],
            tag_ids: [],
            sale_team_ids: [],
            company_ids: [session.company_id],
        };

        this.defs = [];
        this.unresolved_defs_vals = [];
    },

    start: async function () {
        this.controlPanelProps.cp_content = this.render_controlpanel_content();
        return this._super();
    },

    fetch_data: async function () {
        const data = await this._rpc({
            route: '/sale_subscription_dashboard/fetch_data',
            params: {context: session.user_context},
            }, {
                shadow: true
            },
        );
        this.stat_types = data.stat_types;
        this.forecast_stat_types = data.forecast_stat_types;
        this.currency_id = data.currency_id;
        this.contract_templates = data.contract_templates;
        this.tags = data.tags;
        this.companies = data.companies;
        this.has_mrr = data.has_mrr;
        this.has_template = data.has_template;
        this.sales_team = data.sales_team;
        this.dashboard_options.ranges = this.convert_dates(data.dates_ranges);
    },

    populateBoxes: function ($stat_boxes, $forecast_boxes) {
        var self = this;
        $stat_boxes.each(function (key, box) {
            self.defs.push(new SaleSubscriptionDashboardStatBox(
                self,
                self.start_date,
                self.end_date,
                self.filters,
                self.currency_id,
                self.stat_types,
                box.getAttribute('name'),
                box.getAttribute('code'),
                self.has_mrr
            ).replace($(box)));
        });

        $forecast_boxes.each(function (key, box) {
            self.defs.push(new SaleSubscriptionDashboardForecastBox(
                self,
                self.end_date,
                self.filters,
                self.forecast_stat_types,
                box.getAttribute("name"),
                box.getAttribute("code"),
                self.currency_id,
                self.has_mrr
            ).replace($(box)));
        });
    },

    on_reverse_breadcrumb: function () {
        this._super();

        if(this.$main_dashboard) {
            this.defs = [];
            // If there is unresolved defs, we need to replace the uncompleted boxes
            if (this.unresolved_defs_vals.length) {
                const $stat_boxes = this.$main_dashboard.find('.o_stat_box');
                const $forecast_boxes = this.$main_dashboard.find('.o_forecast_box');
                this.populateBoxes($stat_boxes, $forecast_boxes);
            }
        } else {
            this.render_dashboard();
        }
    },

    render_dashboard: function() {
        this.$main_dashboard = $(QWeb.render("sale_subscription_dashboard.dashboard", {
            has_mrr: this.has_mrr,
            has_template: this.has_template,
            stat_types: _.sortBy(_.values(this.stat_types), 'prior'),
            forecast_stat_types:  _.sortBy(_.values(this.forecast_stat_types), 'prior'),
            start_date: this.start_date,
            end_date: this.end_date,
        }));
        this.$('.o_content').append(this.$main_dashboard);

        var $stat_boxes = this.$main_dashboard.find('.o_stat_box');
        var $forecast_boxes = this.$main_dashboard.find('.o_forecast_box');
        this.defs = [];
        this.populateBoxes($stat_boxes, $forecast_boxes);
        this.defs.push(this.update_cp());
        return Promise.all(this.defs);
    },

    store_unresolved_defs: function() {
        this.unresolved_defs_vals = [];
        var self = this;
        _.each(this.defs, function(v, k){
            if (v && v.state !== "resolved"){
                self.unresolved_defs_vals.push(k);
            }
        });
    },

    on_stat_box: function(ev) {
        ev.preventDefault();
        this.selected_stat = $(ev.currentTarget).attr('data-stat');

        this.store_unresolved_defs();

        var options = {
            'stat_types': this.stat_types,
            'selected_stat': this.selected_stat,
            'start_date': this.start_date,
            'end_date': this.end_date,
            'contract_templates': this.contract_templates,
            'tags': this.tags,
            'companies': this.companies,
            'filters': this.filters,
            'currency_id': this.currency_id,
            'push_main_state': true,
            'sales_team': this.sales_team,
            'dashboard_options': this.dashboard_options,
        };
        this.load_action("sale_subscription_dashboard.action_subscription_dashboard_report_detailed", options);
    },

    on_forecast_box: function(ev) {
        ev.preventDefault();

        var options = {
            'forecast_types': this.forecast_types,
            'start_date': this.start_date,
            'end_date': this.end_date,
            'contract_templates': this.contract_templates,
            'tags': this.tags,
            'companies': this.companies,
            'filters': this.filters,
            'currency_id': this.currency_id,
            'push_main_state': true,
            'sales_team': this.sale_team_ids,
        };
        this.load_action("sale_subscription_dashboard.action_subscription_dashboard_report_forecast", options);
    },

    on_demo_contracts: function(ev) {
        ev.preventDefault();
        this.load_action("sale_subscription.sale_subscription_action", {});
    },

    on_demo_templates: function(ev) {
        ev.preventDefault();
        this.load_action("sale_subscription.sale_subscription_template_action", {});
    },
});


// 2. Detailed dashboard
var sale_subscription_dashboard_detailed = sale_subscription_dashboard_abstract.extend({
    events: Object.assign({}, sale_subscription_dashboard_abstract.prototype.events, {
        'click .o_detailed_analysis': 'on_detailed_analysis',
    }),

    init: function(parent, action, options) {
        this._super.apply(this, arguments);

        this.main_dashboard_action_id = options.main_dashboard_action_id;
        this.stat_types = options.stat_types;
        this.start_date = options.start_date;
        this.end_date = options.end_date;
        this.selected_stat = options.selected_stat;
        this.contract_templates = options.contract_templates;
        this.tags = options.tags;
        this.companies = options.companies;
        this.filters = options.filters;
        this.currency_id = options.currency_id;
        this.sales_team = options.sales_team;
        this.dashboard_options = options.dashboard_options;

        this.display_stats_by_plan = !_.contains(['nrr', 'arpu', 'logo_churn'], this.selected_stat);
        this.report_name = this.stat_types[this.selected_stat].name;
    },

    fetch_computed_stat: async function () {
        const data = await this._rpc({
                route: '/sale_subscription_dashboard/compute_stat',
                params: {
                    stat_type: this.selected_stat,
                    start_date: dateToServer(this.start_date, 'date'),
                    end_date: dateToServer(this.end_date, 'date'),
                    filters: this.filters,
                    context: session.user_context,
                },
            }, {shadow: true});
        this.value = data;
    },

    update_cp: function () {
        this.$cpButton = $(QWeb.render("sale_subscription_dashboard.detailed_analysis_btn", {
            stat_type: this.selected_stat,
        }));
        this._super.apply(this);
    },

    render_dashboard: function() {
        var self = this;
        return this.fetch_computed_stat()
        .then(function(){

            self.$('.o_content').append(QWeb.render("sale_subscription_dashboard.detailed_dashboard", {
                selected_stat_values: _.findWhere(self.stat_types, {code: self.selected_stat}),
                start_date: self.start_date,
                end_date: self.end_date,
                stat_type: self.selected_stat,
                currency_id: self.currency_id,
                report_name: self.report_name,
                value: self.value,
                display_stats_by_plan: self.display_stats_by_plan,
                format_number: self.format_number,
            }));

            const defs = [];
            defs.push(self.render_detailed_dashboard_stats_history());
            defs.push(self.render_detailed_dashboard_graph());

            if (self.selected_stat === 'mrr') {
                defs.push(self.render_detailed_dashboard_mrr_growth());
            }

            if (self.display_stats_by_plan){
                defs.push(self.render_detailed_dashboard_stats_by_plan());
            }

            defs.push(self.update_cp());
            return Promise.all(defs);
        });
    },

    render_detailed_dashboard_stats_history: function() {

        var self = this;
        self._rpc({
                route: '/sale_subscription_dashboard/get_stats_history',
                params: {
                    stat_type: this.selected_stat,
                    start_date: dateToServer(this.start_date, 'date'),
                    end_date: dateToServer(this.end_date, 'date'),
                    filters: this.filters,
                    context: session.user_context,
                },
            }, {shadow: true}).then(function (result) {
                // Rounding of result
                _.map(result, function(v, k, dict) {
                    dict[k] = Math.round(v * 100) / 100;
                });
                var html = QWeb.render('sale_subscription_dashboard.stats_history', {
                    stats_history: result,
                    stat_type: self.selected_stat,
                    stat_types: self.stat_types,
                    currency_id: self.currency_id,
                    rate: self.compute_rate,
                    get_color_class: get_color_class,
                    value: Math.round(self.value * 100) / 100,
                    format_number: self.format_number,
                });
                self.$('#o-stat-history-box').empty();
                self.$('#o-stat-history-box').append(html);
        });
        addLoader(this.$('#o-stat-history-box'));
    },

    render_detailed_dashboard_stats_by_plan: function() {
        var self = this;
        self._rpc({
                route: '/sale_subscription_dashboard/get_stats_by_plan',
                params: {
                    stat_type: this.selected_stat,
                    start_date: dateToServer(this.start_date, 'date'),
                    end_date: dateToServer(this.end_date, 'date'),
                    filters: this.filters,
                    context: session.user_context,
                },
            }, {shadow: true}).then(function (result) {
                var html = QWeb.render('sale_subscription_dashboard.stats_by_plan', {
                    stats_by_plan: result,
                    stat_type: self.selected_stat,
                    stat_types: self.stat_types,
                    currency_id: self.currency_id,
                    value: self.value,
                    format_number: self.format_number,
                });
                self.$('.o_stats_by_plan').replaceWith(html);
        });
        addLoader(this.$('.o_stats_by_plan'));
    },

    compute_rate: function(old_value, new_value) {
        return old_value === 0 ? 0 : parseInt(100.0 * (new_value-old_value) / old_value);
    },

    render_detailed_dashboard_graph: function() {

        addLoader(this.$('#stat_chart_div'));

        var self = this;
        self._rpc({
                route: '/sale_subscription_dashboard/compute_graph',
                params: {
                    stat_type: this.selected_stat,
                    start_date: dateToServer(this.start_date, 'date'),
                    end_date: dateToServer(this.end_date, 'date'),
                    points_limit: 0,
                    filters: this.filters,
                    context: session.user_context,
                },
            }).then(function(result) {
                load_chart('#stat_chart_div', self.stat_types[self.selected_stat].name, result, true);
                self.$('#stat_chart_div div.o_loader').hide();
        });
    },

    render_detailed_dashboard_mrr_growth: function() {

        addLoader(this.$('#mrr_growth_chart_div'));
        var self = this;

        self._rpc({
                route: '/sale_subscription_dashboard/compute_graph_mrr_growth',
                params: {
                    start_date: dateToServer(this.start_date, 'date'),
                    end_date: dateToServer(this.end_date, 'date'),
                    points_limit: 0,
                    filters: this.filters,
                    context: session.user_context,
                },
            }, {shadow: true}).then(function (result) {
                self.load_chart_mrr_growth_stat('#mrr_growth_chart_div', result);
                self.$('#mrr_growth_chart_div div.o_loader').hide();
        });
    },

    on_detailed_analysis: function() {

        var additional_context = {};
        var view_xmlid = '';

        // To get the same numbers as in the dashboard, we need to give the filters to the backend
        if (this.selected_stat === 'mrr') {
            additional_context = {
                'search_default_subscription_end_date': moment(this.end_date).format('YYYY-MM-DD'),
                'search_default_subscription_start_date': moment(this.start_date).format('YYYY-MM-DD'),
                // TODO: add contract_ids as another filter
            };
            view_xmlid = "sale_subscription_dashboard.action_move_line_entries_report";
        }
        else if (this.selected_stat === 'nrr' || this.selected_stat  === 'net_revenue') {
            // TODO: add filters
            additional_context = {};
            view_xmlid = "account.action_account_invoice_report_all";
        }

        this.load_action(view_xmlid, {additional_context: additional_context});
    },

    load_chart_mrr_growth_stat: function(div_to_display, result) {
        if (!result.new_mrr) {
            return;  // no data, no graph, no crash
        }

        var labels = result.new_mrr.map(function (point) {
            return moment(point[0], "YYYY-MM-DD", 'en');
        });
        var datasets = [
            {
                label: _t('New MRR'),
                data: result.new_mrr.map(getValue),
                borderColor: '#26b548',
                fill: false,
            },
            {
                label: _t('Churned MRR'),
                data: result.churned_mrr.map(getValue),
                borderColor: '#df2e28',
                fill: false,
            },
            {
                label: _t('Expansion MRR'),
                data: result.expansion_mrr.map(getValue),
                borderColor: '#fed049',
                fill: false,
            },
            {
                label: _t('Down MRR'),
                data: result.down_mrr.map(getValue),
                borderColor: '#ffa500',
                fill: false,
            },
            {
                label: _t('Net New MRR'),
                data: result.net_new_mrr.map(getValue),
                borderColor: '#2693d5',
                fill: false,
            }
        ];

        var $div_to_display = $(div_to_display).css({position: 'relative', height: '20em'});
        $div_to_display.empty();
        var $canvas = $('<canvas/>');
        $div_to_display.append($canvas);

        var ctx = $canvas.get(0).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                layout: {
                    padding: {bottom: 30},
                },
                maintainAspectRatio: false,
                tooltips: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    yAxes: [{
                        scaleLabel: {
                            display: true,
                            labelString: 'MRR',
                        },
                        type: 'linear',
                        ticks: {
                            callback: formatValue,
                        },
                    }],
                    xAxes: [{
                        ticks: {
                            callback:  function (value) {
                                return moment(value).format(DATE_FORMAT);
                            }
                        },
                    }],
                },
            }
        });
    },
});

// 3. Forecast dashboard
var sale_subscription_dashboard_forecast = sale_subscription_dashboard_abstract.extend({
    events: {
        'change .o_forecast_input': 'on_forecast_input',
        'change input.growth_type': 'on_growth_type_change',
    },

    init: function(parent, action, options) {
        this._super.apply(this, arguments);

        this.main_dashboard_action_id = options.main_dashboard_action_id;
        this.start_date = options.start_date;
        this.end_date = options.end_date;
        this.contract_templates = options.contract_templates;
        this.tags = options.tags;
        this.companies = options.companies;
        this.filters = options.filters;
        this.currency_id = options.currency_id;
        this.sales_team = options.sales_team;

        this.values = {};
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return Promise.all([
                self.fetch_default_values_forecast('mrr'),
                self.fetch_default_values_forecast('contracts')
            ]);
        });
    },

    render_dashboard: function() {
        this.$('.o_content').append(QWeb.render("sale_subscription_dashboard.forecast", {
            start_date: this.start_date,
            end_date: this.end_date,
            values: this.values,
            currency_id: this.currency_id,
            get_currency: this.get_currency,
        }));

        this.values.mrr.growth_type = 'linear';
        this.values.contracts.growth_type = 'linear';
        this.reload_chart('mrr');
        this.reload_chart('contracts');

        this.update_cp();
    },

    on_forecast_input: function(ev) {
        var forecast_type = $(ev.target).data().forecast;
        var data_type = $(ev.target).data().type;
        this.values[forecast_type][data_type] = parseInt($(ev.target).val());
        this.reload_chart(forecast_type);
    },

    on_growth_type_change: function(ev) {
        var forecast_type = $(ev.target).data().type;

        this.values[forecast_type].growth_type = this.$("input:radio[name=growth_type_"+forecast_type+"]:checked").val();
        if (this.values[forecast_type].growth_type === 'linear') {
            this.$('#linear_growth_' + forecast_type).show();
            this.$('#expon_growth_' + forecast_type).hide();
        }
        else {
            this.$('#linear_growth_' + forecast_type).hide();
            this.$('#expon_growth_' + forecast_type).show();
        }
        this.reload_chart(forecast_type);
    },

    fetch_default_values_forecast: async function(forecast_type) {
        const data = await  this._rpc({
            route: '/sale_subscription_dashboard/get_default_values_forecast',
            params: {
                end_date: dateToServer(this.end_date, 'date'),
                forecast_type: forecast_type,
                filters: this.filters,
                context: session.user_context,
            },
        }, {shadow: true});
        this.values[forecast_type] = data;
    },

    reload_chart: function(chart_type) {
        var computed_values = compute_forecast_values(
            this.values[chart_type].starting_value,
            this.values[chart_type].projection_time,
            this.values[chart_type].growth_type,
            this.values[chart_type].churn,
            this.values[chart_type].linear_growth,
            this.values[chart_type].expon_growth
        );
        this.load_chart_forecast('#forecast_chart_div_' + chart_type, computed_values);

        var content = QWeb.render('sale_subscription_dashboard.forecast_summary_' + chart_type, {
            values: this.values[chart_type],
            computed_value: parseInt(computed_values[computed_values.length - 1][1]),
            currency_id: this.currency_id,
            format_number: this.format_number,
        });

        this.$('#forecast_summary_' + chart_type).replaceWith(content);
    },

    get_currency: function() {
        var currency = session.get_currency(this.currency_id);
        return currency.symbol;
    },

    format_number: function(value) {
        value = utils.human_number(value);
        return render_monetary_field(value, this.currency_id);
    },

    load_chart_forecast: function(div_to_display, values) {
        var labels = values.map(function (point) {
            return point[0];
        });
        var datasets = [{
            data: values.map(getValue),
            backgroundColor: 'rgba(38,147,213,0.2)',
            borderColor: 'rgba(38,147,213,0.2)',
            borderWidth: 3,
            pointBorderWidth: 1,
            cubicInterpolationMode: 'monotone',
            fill: 'origin',
        }];

        var $div_to_display = this.$(div_to_display).css({position: 'relative', height: '20em'});
        $div_to_display.empty();
        var $canvas = $('<canvas/>');
        $div_to_display.append($canvas);

        var ctx = $canvas.get(0).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                layout: {
                    padding: {bottom: 30},
                },
                legend: {
                    display: false,
                },
                maintainAspectRatio: false,
                tooltips: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    yAxes: [{
                        type: 'linear',
                        ticks: {
                            callback: formatValue,
                        },
                    }],
                    xAxes: [{
                        ticks: {
                            callback:  function (value) {
                                return moment(value).format(DATE_FORMAT);
                            }
                        },
                    }],
                },
            }
        });
    },

    update_cp: function() { // Redefinition to not show anything in controlpanel for forecast dashboard
        this.updateControlPanel({});
    },
});

// These are two smalls widgets to display all the stat boxes in the main dashboard
var SaleSubscriptionDashboardStatBox = Widget.extend({
    template: 'sale_subscription_dashboard.stat_box_content',

    init: function(parent, start_date, end_date, filters, currency_id, stat_types, box_name, stat_type, has_mrr) {
        this._super(parent);

        this.start_date = start_date;
        this.end_date = end_date;

        this.filters = filters;
        this.currency_id = currency_id;
        this.stat_types = stat_types;
        this.box_name = box_name;
        this.stat_type = stat_type;
        this.tooltip = stat_types[stat_type].tooltip;
        this.has_mrr = has_mrr;

        this.chart_div_id = 'chart_div_' + this.stat_type;
        this.added_symbol = this.stat_types[this.stat_type].add_symbol;
        this.is_monetary = this.added_symbol === 'currency';
        this.render_monetary_field = render_monetary_field;

        this.demo_values = {
            'mrr': 1000,
            'net_revenue': 55000,
            'nrr': 27000,
            'arpu': 20,
            'arr': 12000,
            'ltv': 120,
            'logo_churn': 7,
            'revenue_churn': 5,
            'nb_contracts': 50,
        };
    },

    start: async function() {
        await this.compute_graph();
        const display_tooltip = '<b>' + this.box_name + '</b><br/>' + _t('Current Value: ') + this.format_number(this.value);
        this.$el.tooltip({title: display_tooltip, trigger: 'hover'});
        this.$('[data-bs-toggle="popover"]').popover({trigger: 'hover'});
        const options = {
            has_mrr: this.has_mrr, format_number: this.format_number,
            value: this.value, demo_values: this.demo_values,
            stat_type: this.stat_type, currency_id: this.currency_id,
            added_symbol: this.added_symbol,
        };
        const $boxName = $(QWeb.render("sale_subscription_dashboard.box_name", options));
        this.$('.o_stat_box_card_amount').append($boxName);
        const $boxPerc = $(QWeb.render("sale_subscription_dashboard.box_trend", {color: this.color, perc: this.perc}));
        this.$('.o_trend').append($boxPerc);
        load_chart('#' + this.chart_div_id, false, this.computed_graph, false, !this.has_mrr);
        this.$('.o_loader').remove();
    },

    compute_graph: async function() {
        const data = await this._rpc({
                route: '/sale_subscription_dashboard/compute_graph_and_stats',
                    params: {
                        stat_type: this.stat_type,
                        start_date: dateToServer(this.start_date, 'date'),
                        end_date: dateToServer(this.end_date, 'date'),
                        points_limit: 30,
                        filters: this.filters,
                        context: session.user_context,
                    },
                }, {shadow: true},
            );
        this.value = data.stats.value_2;
        this.perc = data.stats.perc;
        this.color = get_color_class(data.stats.perc, this.stat_types[this.stat_type].dir);
        this.computed_graph = data.graph;
    },

    format_number: function(value, currency_id) {
        value = utils.human_number(value);
        if ((currency_id || this.is_monetary) && this.added_symbol) {
            this.currency_id = (currency_id) ? currency_id : this.currency_id;
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + this.added_symbol;
        }
    },
});

var SaleSubscriptionDashboardForecastBox = Widget.extend({
    template: 'sale_subscription_dashboard.forecast_stat_box_content',

    init: function(parent, end_date, filters, forecast_stat_types, box_name, stat_type, currency_id, has_mrr) {
        this._super(parent);
        this.end_date = end_date;
        this.filters = filters;

        this.currency_id = currency_id;
        this.forecast_stat_types = forecast_stat_types;
        this.box_name = box_name;
        this.stat_type = stat_type;
        this.has_mrr = has_mrr;

        this.added_symbol = this.forecast_stat_types[this.stat_type].add_symbol;
        this.is_monetary = this.added_symbol === 'currency';
        this.chart_div_id = 'chart_div_' + this.stat_type;
        this.render_monetary_field = render_monetary_field;

        this.demo_values = {
            'mrr_forecast': 12000,
            'contracts_forecast': 240,
        };
    },
    start: async function() {
        await this.compute_numbers();
        const display_tooltip = '<b>' + this.box_name + '</b><br/>' + _t('Current Value: ') + this.format_number(this.value);
        this.$el.tooltip({title: display_tooltip, trigger: 'hover'});
        const options = {
            has_mrr: this.has_mrr, format_number: this.format_number,
            value: this.value, demo_values: this.demo_values,
            stat_type: this.stat_type, currency_id: this.currency_id,
            added_symbol: this.added_symbol,
        };
        const $boxName = $(QWeb.render("sale_subscription_dashboard.box_name", options));
        this.$('.o_stat_box_card_amount').append($boxName);
        load_chart('#' + this.chart_div_id, false, this.computed_graph, false, !this.has_mrr);
        this.$('.o_loader').remove();
    },

    compute_numbers: async function () {
        const data = await this._rpc({
                    route: '/sale_subscription_dashboard/get_default_values_forecast',
                    params: {
                        forecast_type: this.stat_type,
                        end_date: dateToServer(this.end_date, 'date'),
                        filters: this.filters,
                        context: session.user_context,
                    },
                }, {shadow: true},
            );
        this.computed_graph = compute_forecast_values(
            data.starting_value,
            data.projection_time,
            'linear',
            data.churn,
            data.linear_growth,
            0
        );
        this.value = this.computed_graph[this.computed_graph.length - 1][1];
    },

    format_number: function(value, currency_id) {
        value = utils.human_number(value);
        if ((currency_id || this.is_monetary) && this.added_symbol) {
            this.currency_id = (currency_id) ? currency_id : this.currency_id;
            return render_monetary_field(value, this.currency_id);
        } else {
            return value + this.added_symbol;
        }
    },
});

var sale_subscription_dashboard_salesman = sale_subscription_dashboard_abstract.extend({

    init: function() {
        this._super.apply(this, arguments);
        this.start_date = moment().subtract(1,'months').startOf('month'); // last month values by default
        this.end_date = moment().subtract(1,'months').endOf('month');
        this.barGraph = {};
        this.migrationDate = false;
        this.currentCompany = $.bbq.getState('cids') && parseInt($.bbq.getState('cids').split(',')[0]);
        this.pdf_values = {'salespersons_statistics': {}, 'salesman_ids': [],'graphs': {}, 'company': this.currentCompany}

        // Chart.js requires the canvas to be in the DOM when the chart is rendered (s.t. it is able
        // to compute positions and stuff), so we use the following promise to ensure that we don't
        // try to render a chart before being in the DOM.
        this._mountedProm = new Promise((r) => {
            this._resolveMountedProm = r;
        });
    },

    on_attach_callback() {
        this._super(...arguments);
        this._resolveMountedProm();
    },
    on_detach_callback() {
        this._super(...arguments);
        this._mountedProm = new Promise((r) => {
            this._resolveMountedProm = r;
        });
    },

    willStart: function() {
        return Promise.all(
            [this._super.apply(this, arguments),
            this.fetch_salesmen()]
        );
    },

    start: async function () {
        this.controlPanelProps.cp_content = this.render_controlpanel_content();
        const res = await this._super(...arguments);
        return res;
    },

    fetch_salesmen: function() {
        var self = this;
        return self._rpc({
                route: '/sale_subscription_dashboard/fetch_salesmen',
                params: {context: session.user_context,},
            }).then(function(result) {
                self.salesman_ids = result.salesman_ids;
                self.pdf_values.salesman_ids = result.salesman_ids;
                self.salesman = result.default_salesman || [];
                self.currency_id = result.currency_id;
                self.migrationDate = moment(result.migration_date, 'YYYY-MM-DD');
                self.dashboard_options.ranges = self.convert_dates(result.dates_ranges);
        }, {shadow: true});
    },

    render_dashboard: function() {
        this.update_cp();
        this.$('.o_content').empty().append(QWeb.render("sale_subscription_dashboard.salesmen", {
            salesman_ids: this.salesman_ids,
            salesman: this.salesman,
            start_date: this.start_date,
            end_date: this.end_date,
            migration_date: this.migrationDate,
        }));
        if (!jQuery.isEmptyObject(this.salesman)) {
            this.render_dashboard_additionnal();
        }
    },

    render_dashboard_additionnal: function() {
        var self = this;
        addLoader(this.$('#mrr_growth_salesman'));

        this._rpc({
            route: '/sale_subscription_dashboard/get_values_salesmen',
            params: {
                start_date: dateToServer(this.start_date, 'date'),
                end_date: dateToServer(this.end_date, 'date'),
                salesman_ids: this.salesman,
                context: session.user_context,
            },
        }, {shadow: true}).then(async function (result) {
            await self._mountedProm;
            var salespersons_statistics = result.salespersons_statistics;
            self.pdf_values['salespersons_statistics'] = result.salespersons_statistics;
            Object.keys(salespersons_statistics).forEach(element => {
                var cur_salesman = self.salesman_ids.find(val => val.id === Number(element));
                self.$('.o_salesman_loop').append(QWeb.render("sale_subscription_dashboard.salesman", {
                    salesman: cur_salesman,
                }));
                self.render_section(cur_salesman, salespersons_statistics[Number(element)]);
            });
            $('.o_subscription_row').each(function (index, value) {
                $(this).on('click', function () {
                    var subscription_id = $(this).data().id;
                    var model = $(this).data().model;
                    var action = {
                        type: 'ir.actions.act_window',
                        res_model: model,
                        res_id: subscription_id,
                        views: [[false, 'form']],
                    };
                    self.do_action(action);
                });
            });
        });
    },

    render_section: function (cur_salesman, salesman_data) {
        addLoader(this.$('#mrr_growth_salesman_' + cur_salesman.id));
        this.barGraph[cur_salesman.id] = load_chart_mrr_salesman(
            '#mrr_growth_salesman_' + cur_salesman.id, salesman_data, this.currency_id);
        this.$('#mrr_growth_salesman_' + cur_salesman.id + ' div.o_loader').hide();

        // 1. Subscriptions modifcations
        var ICON_BY_TYPE = {
            'churn': 'o_red fa fa-remove',
            'new': 'o_green fa fa-plus',
            'down': 'o_red fa fa-arrow-down',
            'up': 'o_green fa fa-arrow-up',
        };

        _.each(salesman_data.contract_modifications, function(v) {
            v.class_type = ICON_BY_TYPE[v.type];
        });
        const nCompanies = new Set([this.currentCompany].
            concat(salesman_data.contract_modifications.
                map(value => value.company_id))
                .concat(salesman_data.nrr_invoices
                    .map(value => value.company_id))).size;

        var html_modifications = QWeb.render('sale_subscription_dashboard.contract_modifications', {
            modifications: salesman_data.contract_modifications,
            get_color_class: get_color_class,
            format_number: this.format_number,
            company_currency_id: this.currency_id,
            nCompanies: nCompanies,
        });
        this.$('#contract_modifications_' + cur_salesman.id).append(html_modifications);

        // 2. NRR invoices
        var html_nrr_invoices = QWeb.render('sale_subscription_dashboard.nrr_invoices', {
            invoices: salesman_data.nrr_invoices,
            company_currency_id: this.currency_id,
            format_number: this.format_number,
            nCompanies: nCompanies,
        });
        this.$('#NRR_invoices_' + cur_salesman.id).append(html_nrr_invoices);

        // 3. Summary
        var html_summary = QWeb.render('sale_subscription_dashboard.salesman_summary', {
            mrr: salesman_data.net_new,
            nrr: salesman_data.nrr,
            company_currency_id: this.currency_id,
            format_number: this.format_number,
        });
        this.$('#mrr_growth_salesman_' + cur_salesman.id).before(html_summary);

        function load_chart_mrr_salesman (div_to_display, result, currency_id) {
            var labels = [_t("New MRR"), _t("Churned MRR"), _t("Expansion MRR"),
                            _t("Down MRR"),  _t("Net New MRR"), _t("NRR")];
            var datasets = [{
                label: _t("MRR Growth"),
                data: [result.new, result.churn, result.up,
                        result.down, result.net_new, result.nrr],
                backgroundColor: ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a"],
            }];

            var $div_to_display = $(div_to_display).css({position: 'relative', height: '16em'});
            $div_to_display.empty();
            var $canvas = $('<canvas class="canvas_'+ cur_salesman.id + '"/>');
            $div_to_display.append($canvas);

            var ctx = $canvas.get(0).getContext('2d');
            ctx.currency_id = currency_id;
            let ChartValuePlugin = {
                updated: false,
                afterDraw: function(chart) {
                var ctx = chart.ctx;
                ctx.font = chart.config.options.defaultFontFamily;
                ctx.fillStyle = chart.config.options.defaultFontColor;
                var chartdatasets = chart.data.datasets;
                // Clear the area where values are drawn to avoid rendering multiple times and glitches
                ctx.clearRect(50, -5, 2000, 20);
                Chart.helpers.each(chartdatasets.forEach(function (dataset, i) {
                    var meta = chart.controller.getDatasetMeta(i);
                    Chart.helpers.each(meta.data.forEach(function (bar, index) {
                        var value = utils.human_number(dataset.data[index]);
                        ctx.fillText(render_monetary_field(value, ctx.currency_id), bar._model.x, 15);
                    }), this);
                  }), this);
                }
            };
            var barGraph = new Chart(ctx, {
                type: 'bar',
                plugins : [ChartValuePlugin],
                data: {
                    labels: labels,
                    datasets: datasets,
                },
                options: {
                    layout: {
                        padding: {bottom: 15, top: 17},
                    },
                    legend: {
                        display: false,
                    },
                    maintainAspectRatio: false,
                    tooltips: {
                        enabled: false,
                    },
                },
            });
            return barGraph;
        }
    },

    format_number: function(value, currency_id) {
        if (!currency_id) {
            currency_id = this.currency_id;
        }
        value = utils.human_number(value);
        return render_monetary_field(value, currency_id);
    },

    on_update_options: function () {
        this.render_dashboard();
    },

    render_controlpanel_content() {
        this.$searchview = $(QWeb.render("sale_subscription_dashboard.salesman_searchview"));
        this.set_up_datetimepickers({salesman: true});
        this.$cpButton = $(QWeb.render("sale_subscription_dashboard.export"));
        const self = this;
        this.$cpButton.on('click', function () {
            ajax.rpc('/web/dataset/call_kw/sale.subscription/print_pdf', {
            model: 'sale.order',
            method: 'print_pdf',
            args: [],
            kwargs: {},
            }, {shadow: true})
            .then(function (result) {
                for (var key in self.barGraph) {
                    var base64Image = self.barGraph[key].toBase64Image();
                    self.pdf_values.graphs[key] = base64Image;
                }
                result.data.rendering_values = JSON.stringify(self.pdf_values);
                var doActionProm = self.do_action(result);
                return doActionProm;
            });
        });
        this.$searchview.on('click', '.o_update_options', this.on_update_options);
        // We need the many2many widget to limit the available users to the ones returned by the `fetch_salesmen` RPC call.
        let domainList = [];
        // The available users in the dropdown are synched with the available salesman_ids.
        // Note: self.salesman may already contains the current user (default salesman) when the dashboard is launched.
        if (this.many2manytags) {
            let values = [];
            for (let index = 0; index < self.many2manytags.value.res_ids.length; index++) {
                values.push(self.salesman_ids.find(val => val.id === self.many2manytags.value.res_ids[index]));
            }
           this.salesman = values;
        }
        this.salesman_ids.forEach(saleman => {
            domainList.push(saleman.id);
        });
        // Make a dummy record to attach the salesman selector widget
        let def = self.model.makeRecord('ir.actions.act_window', [{
            name: 'model',
            relation: 'res.users',
            type: 'many2many',
            domain: [['id', 'in', domainList]]
        }]);
        Promise.all([def]).then(function (recordID) {
            var record = self.model.get(recordID);
            var options = {
                mode: 'edit',
            };
            self.many2manytags = new FieldMany2ManyTags(self, 'model', record, options);
            self.many2manytags.nodeOptions.create = false;
            if (Object.keys(self.salesman).length > 0) {
                self.many2manytags._addTag(self.salesman);
            }
            self._registerWidget(recordID, 'model', self.many2manytags);
            self.many2manytags.appendTo(self.$searchview.find('.salesman_tags'));
        });
        return {
            $searchview: this.$searchview,
            $buttons: this.$cpButton,
        };
    },
});

// Utility functions

function addLoader(selector) {
    var loader = '<span class="fa fa-3x fa-spin fa-circle-o-notch fa-spin"/>';
    selector.html("<div class='o_loader'>" + loader + "</div>");
}

function formatValue (value) {
    var formatter = field_utils.format.float;
    return formatter(value, undefined, FORMAT_OPTIONS);
}

function getValue(d) { return d[1]; }

function compute_forecast_values(starting_value, projection_time, growth_type, churn, linear_growth, expon_growth) {
    var values = [];
    var cur_value = starting_value;

    for(var i = 1; i <= projection_time ; i++) {
        var cur_date = moment().add(i, 'months');
        if (growth_type === 'linear') {
            cur_value = cur_value*(1-churn/100) + linear_growth;
        }
        else {
            cur_value = cur_value*(1-churn/100)*(1+expon_growth/100);
        }
        values.push({
            '0': cur_date,
            '1': cur_value,
        });
    }
    return values;
}

function load_chart(div_to_display, key_name, result, show_legend, show_demo) {

    if (show_demo) {
        // As we do not show legend for demo graphs, we do not care about the dates.
        result = [
          {
            "0": "2015-08-01",
            "1": 10
          },
          {
            "0": "2015-08-02",
            "1": 20
          },
          {
            "0": "2015-08-03",
            "1": 29
          },
          {
            "0": "2015-08-04",
            "1": 37
          },
          {
            "0": "2015-08-05",
            "1": 44
          },
          {
            "0": "2015-08-06",
            "1": 50
          },
          {
            "0": "2015-08-07",
            "1": 55
          },
          {
            "0": "2015-08-08",
            "1": 59
          },
          {
            "0": "2015-08-09",
            "1": 62
          },
          {
            "0": "2015-08-10",
            "1": 64
          },
          {
            "0": "2015-08-11",
            "1": 65
          },
          {
            "0": "2015-08-12",
            "1": 66
          },
          {
            "0": "2015-08-13",
            "1": 67
          },
          {
            "0": "2015-08-14",
            "1": 68
          },
          {
            "0": "2015-08-15",
            "1": 69
          },
        ];
    }

    var labels = result.map(function (point) {
        return point[0];
    });

    var datasets = [{
        label: key_name,
        data: result.map(function (point) {
            return point[1];
        }),
        backgroundColor: "rgba(38,147,213,0.2)",
        borderColor: "rgba(38,147,213,0.8)",
        borderWidth: 3,
        pointBorderWidth: 1,
        cubicInterpolationMode: 'monotone',
        fill: 'origin',
    }];

    var $div_to_display = $(div_to_display).css({position: 'relative'});
    if (show_legend) {
        $div_to_display.css({height: '20em'});
    }
    $div_to_display.empty();
    var $canvas = $('<canvas/>');
    $div_to_display.append($canvas);

    var ctx = $canvas.get(0).getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets,
        },
        options: {
            layout: {
                padding: {bottom: 10},
            },
            legend: {
                display: show_legend,
            },
            maintainAspectRatio: false,
            tooltips: {
                enabled: show_legend,
                intersect: false,
            },
            scales: {
                yAxes: [{
                    scaleLabel: {
                        display: show_legend,
                        labelString: show_legend ? key_name : '',
                    },
                    display: show_legend,
                    type: 'linear',
                    ticks: {
                        callback: field_utils.format.float,
                    },
                }],
                xAxes: [{
                    display: show_legend,
                    ticks: {
                        callback:  function (value) {
                            return moment(value).format(DATE_FORMAT);
                        }
                    },
                }],
            },
        }
    });
}

function render_monetary_field(value, currency_id) {
    var currency = session.get_currency(currency_id);
    if (currency) {
        if (currency.position === "after") {
            value += currency.symbol;
        } else {
            value = currency.symbol + value;
        }
    }
    return value;
}

function get_color_class(value, direction) {
    var color = 'o_black';

    if (value !== 0 && direction === 'up') {
        color = (value > 0) && 'o_green' || 'o_red';
    }
    if (value !== 0 && direction !== 'up') {
        color = (value < 0) && 'o_green' || 'o_red';
    }

    return color;
}

// Add client actions

core.action_registry.add('sale_subscription_dashboard_main', sale_subscription_dashboard_main);
core.action_registry.add('sale_subscription_dashboard_detailed', sale_subscription_dashboard_detailed);
core.action_registry.add('sale_subscription_dashboard_forecast', sale_subscription_dashboard_forecast);
core.action_registry.add('sale_subscription_dashboard_salesman', sale_subscription_dashboard_salesman);

return {sale_subscription_dashboard_main: sale_subscription_dashboard_main,
        sale_subscription_dashboard_detailed: sale_subscription_dashboard_detailed,
        sale_subscription_dashboard_salesman: sale_subscription_dashboard_salesman,
        sale_subscription_dashboard_forecast: sale_subscription_dashboard_forecast
    };
});

odoo.define('sale_subscription_dashboard.sale_subscription_tests', function (require) {
    "use strict";

    var testUtils = require('web.test_utils');
    const { patchWithCleanup } = require("@web/../tests/helpers/utils");

    var SubscriptionDashBoard = require('sale_subscription_dashboard.dashboard');

    QUnit.module('sale_subscription_dashboard', {
        beforeEach: function () {
            this.data = {
                dashboard_options : {
                    filter: 'this_month',
                    ranges: {
                        this_quarter: {date_from: undefined, date_to: undefined},
                        this_year: {date_from: undefined, date_to: undefined},
                        last_quarter: {date_from: undefined, date_to: undefined},
                        last_year: {date_from: undefined, date_to: undefined},
                        this_month: {date_from: undefined, date_to: undefined},
                        last_month: {date_from: undefined, date_to: undefined},
                    }
                },
                fetch_data: {
                    stat_types: {
                        net_revenue: {
                            prior: 1,
                            add_symbol: "currency",
                            code: "net_revenue",
                            name: "Net Revenue",
                            dir: "up",
                            type: "sum"
                        }
                    },
                    forecast_stat_types: {
                        mrr_forecast: {
                            prior: 1,
                            add_symbol: "currency",
                            code: "mrr_forecast",
                            name: "Forecasted Annual MRR Growth"
                        },
                    },
                    currency_id: 2,
                    contract_templates: [{
                        id: 1,
                        name: "Odoo Monthly"
                    }, {
                        id: 2,
                        name: "Odoo Yearly"
                    }],
                    tags: [{
                        id: 1,
                        name: "Contracts"
                    }, {
                        id: 2,
                        name: "Odoo Online"
                    }],
                    companies: {
                        id: 1,
                        name: "YourCompany"
                    },
                    has_mrr: true,
                    has_template: true,
                    dates_ranges: {
                        'this_year': {'date_from':  '2020-01-01', 'date_to': '2020-12-31'},
                        'last_year': {'date_from': '2019-01-01' , 'date_to': '2019-12-31'},
                        'this_quarter': {'date_from':  '2019-12-01' , 'date_to': '2020-02-01'},
                        'last_quarter': {'date_from': '2019-09-01', 'date_to': '2019-11-31'},
                        'this_month': {'date_from': '2020-02-01', 'date_to':  '2020-02-29'},
                        'last_month':  {'date_from': '2020-01-01', 'date_to': '2020-01-31' },
                    }

                },
                compute_stats_graph: {
                    graph: [{
                        0: "2017-08-15",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-16",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-17",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-18",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-19",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-20",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-21",
                        1: 0,
                        series: 0
                    }, {
                        0: "2017-08-22",
                        1: 240,
                        series: 0
                    }, {
                        0: "2017-08-23",
                        1: 40,
                        series: 0
                    }, {
                        0: "2017-08-24",
                        1: 0,
                        series: 0
                    }],
                    stats: {
                        perc: 0,
                        value_1: "0",
                        value_2: "280"
                    }

                },
                forecast_values: {
                    starting_value: 1056,
                    projection_time: 12,
                    churn: 0,
                    expon_growth: 15,
                    linear_growth: 0
                },
                fetch_salesmen: {
                    currency_id: 2,
                    migration_date: '2020-01-01',
                    default_salesman: [{
                        id: 1,
                        name: "Mitchell Admin"
                    }],
                    salesman_ids: [{
                        id: 1,
                        name: "Mitchell Admin"
                    }, {
                        id: 5,
                        name: "Marc Demo"
                    }],
                    dates_ranges: {
                        'this_year': {'date_from':  '2020-01-01', 'date_to': '2020-12-31'},
                        'last_year': {'date_from': '2019-01-01' , 'date_to': '2019-12-31'},
                        'this_quarter': {'date_from':  '2019-12-01' , 'date_to': '2020-02-01'},
                        'last_quarter': {'date_from': '2019-09-01', 'date_to': '2019-11-31'},
                        'this_month': {'date_from': '2020-02-01', 'date_to':  '2020-02-29'},
                        'last_month':  {'date_from': '2020-01-01', 'date_to': '2020-01-31' },
                    }
                },
                salesman_values: {
                    salespersons_statistics: {1: {
                        new: 625,
                        churn: 0,
                        up: 50,
                        down: 0,
                        net_new: 600,
                        contract_modifications: [{
                            partner: "Agrolait",
                            account_analytic: "Agrolait",
                            account_analytic_template: "Odoo Monthly",
                            previous_mrr: 500,
                            current_mrr: 800,
                            diff: 300,
                            type: 'up',
                        }],
                        nrr: 1195,
                        nrr_invoices: [{
                            partner: "Joel Willis",
                            account_analytic_template: "Odoo Monthly",
                            nrr: "20.0",
                            account_analytic: false
                        }, {
                            partner: "Agrolait",
                            account_analytic_template: "Odoo Monthly",
                            nrr: "525.0",
                            account_analytic: false
                        }, {
                            partner: "Agrolait",
                            account_analytic_template: "Odoo Monthly",
                            nrr: "650.0",
                            account_analytic: false
                        }]
                    }}
                },
                get_stats_by_plan: [{
                    name: "Odoo Monthly",
                    nb_customers: 0,
                    value: 0
                }, {
                    name: "Odoo Yearly",
                    nb_customers: 0,
                    value: 0
                }],
                get_stats_history: {
                    value_1_months_ago: 0,
                    value_3_months_ago: 0,
                    value_12_months_ago: 0
                },
                compute_stat: 10495,
            };

            patchWithCleanup(SubscriptionDashBoard.sale_subscription_dashboard_main, {
                update_cp() {}
            });
            patchWithCleanup(SubscriptionDashBoard.sale_subscription_dashboard_salesman, {
                update_cp() {}
            });
        }
    }, function () {

        QUnit.test('sale_subscription_test', async function (assert) {
            var self = this;
            assert.expect(2);
            var subscription_dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_main(null, {
                id: 1,
                dashboard_options: this.data.dashboard_options,
            });
            await testUtils.nextTick();
            await testUtils.mock.addMockEnvironment(subscription_dashboard, {
                mockRPC: function (route, args) {
                    if (route === '/sale_subscription_dashboard/fetch_data') {
                        return Promise.resolve(self.data.fetch_data);
                    }
                    if (route === '/sale_subscription_dashboard/compute_graph_and_stats') {
                        return Promise.resolve(self.data.compute_stats_graph);
                    }
                    if (route === '/sale_subscription_dashboard/get_default_values_forecast') {
                        return Promise.resolve(self.data.forecast_values);
                    }
                    return Promise.resolve();
                },
            });
            await subscription_dashboard.appendTo($('#qunit-fixture'));
            await testUtils.nextTick();
            assert.strictEqual(subscription_dashboard.$('.on_stat_box .o_stat_box_card_amount').text().trim(), "280", "Should contain net revenue amount '280'");
            assert.strictEqual(subscription_dashboard.$('.on_forecast_box .o_stat_box_card_amount').text().trim(), "1k", "Should contain forecasted annual amount '1k'");
            subscription_dashboard.destroy();
        });

        QUnit.test('sale_subscription_forecast', async function (assert) {
            var self = this;
            assert.expect(10);
            var dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_forecast(null, {}, {
                main_dashboard_action_id: null,
                start_date: moment(),
                end_date: moment().add(1, 'month'),
                currency_id: 3,
                contract_templates: null,
                tags: null,
                companies: null,
                filters: null,
                dashboard_options: this.data.dashboard_options,
            });
            await testUtils.mock.addMockEnvironment(dashboard, {
                mockRPC: function (route, args) {
                    if (route === '/sale_subscription_dashboard/get_default_values_forecast') {
                        assert.deepEqual(_.keys(args).sort(), ['context', 'end_date', 'filters', 'forecast_type'],
                                                                "should be requested only with defined parameters");
                        return Promise.resolve(self.data.forecast_values);
                    }
                    return Promise.resolve();
                },
                session: {
                    currencies: {
                        3: {
                            digits: [69, 2],
                            position: "before",
                            symbol: "$"
                        }
                    }
                },
            });
            await dashboard.appendTo($('#qunit-fixture'));
            await testUtils.nextTick();
            assert.containsOnce(dashboard, '.o_account_contract_dashboard', "should have a dashboard");
            assert.containsN(dashboard, '.o_account_contract_dashboard .box', 2, "should have a dashboard with 2 forecasts");

            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:first #forecast_summary_mrr', "first forecast should have summary header");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:first .o_forecast_options', "first forecast should have options");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:first #forecast_chart_div_mrr', "first forecast should have chart");

            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:last #forecast_summary_contracts', "last forecast should have summary header");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:last .o_forecast_options', "last forecast should have options");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box:last #forecast_chart_div_contracts', "last forecast should have chart");
            dashboard.destroy();
        });

        QUnit.test('sale_subscription_detailed', async function (assert) {
            var self = this;
            assert.expect(8);
            var dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_detailed(null, {}, {
                main_dashboard_action_id: null,
                stat_types: this.data.fetch_data.stat_types,
                start_date: moment(),
                end_date: moment().add(1, 'month'),
                selected_stat: 'net_revenue',
                currency_id: 3,
                contract_templates: this.data.fetch_data.contract_templates,
                tags: null,
                companies: null,
                filters: {},
                dashboard_options: this.data.dashboard_options,
            });
            await testUtils.mock.addMockEnvironment(dashboard, {
                mockRPC: function (route, args) {
                    if (route === '/sale_subscription_dashboard/compute_stat') {
                        return Promise.resolve(self.data.compute_stat);
                    }
                    if (route === '/sale_subscription_dashboard/get_stats_history') {
                        return Promise.resolve(self.data.get_stats_history);
                    }
                    if (route === '/sale_subscription_dashboard/compute_graph') {
                        return Promise.resolve(self.data.compute_stats_graph.graph);
                    }
                    if (route === '/sale_subscription_dashboard/get_stats_by_plan') {
                        return Promise.resolve(self.data.get_stats_by_plan);
                    }
                    return Promise.resolve();
                },
                session: {
                    currencies: {
                        3: {
                            digits: [69, 2],
                            position: "before",
                            symbol: "$"
                        }
                    }
                },
            });
            await dashboard.appendTo($('#qunit-fixture'));
            await testUtils.nextTick();
            assert.containsOnce(dashboard, '.o_account_contract_dashboard', "should have a dashboard");
            assert.containsN(dashboard, '.o_account_contract_dashboard .box', 3, "should have a dashboard with 3 boxes");

            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box.o_graph_detailed', "should have in first a graph box");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box.o_graph_detailed .o_metric_current', "should have the current metric");
            assert.strictEqual(dashboard.$('.o_account_contract_dashboard .box.o_graph_detailed .o_metric_current').text().trim(), "$10k", "should format correctly the current metric value");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box.o_graph_detailed #stat_chart_div', "should display a chart");

            assert.containsOnce(dashboard, '.o_account_contract_dashboard #o-stat-history-box.box', "should have in second a history box");
            assert.containsOnce(dashboard, '.o_account_contract_dashboard .box table', "should have in third a table box");

            dashboard.destroy();
        });

        QUnit.test('sale_subscription_salesman', async function (assert) {
            var self = this;
            assert.expect(11);
            var salesman_dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_salesman(null, {});
            salesman_dashboard.salesman =  self.data.fetch_salesmen.default_salesman;
            await testUtils.mock.addMockEnvironment(salesman_dashboard, {
                mockRPC: function (route, args) {
                    if (route === '/sale_subscription_dashboard/fetch_salesmen') {
                        return Promise.resolve(self.data.fetch_salesmen);
                    }
                    if (route === '/sale_subscription_dashboard/get_values_salesmen') {
                        return Promise.resolve(self.data.salesman_values);
                    }
                    return Promise.resolve();
                },
            });
            await salesman_dashboard.appendTo($('#qunit-fixture'));
            salesman_dashboard.on_attach_callback();
            await testUtils.nextTick();
            var id = self.data.fetch_salesmen.salesman_ids[0].id;
            assert.containsOnce(salesman_dashboard, '#mrr_growth_salesman_' + id, " should display the salesman graph");
            assert.strictEqual(salesman_dashboard.$('h2').first().text(), "Monthly Recurring Revenue : 600", "should contain the Monthly Recurring Revenue Amount '600'");
            assert.strictEqual(salesman_dashboard.$('h2').eq(1).text(), "Non-Recurring Revenue : 1k", "should contain the Non-Recurring Revenue Amount '1k'");
            assert.containsOnce(salesman_dashboard, '#contract_modifications_' + id, "should display the list of subscription");
            assert.strictEqual(salesman_dashboard.$('.o_subscription_row td:eq(2)').text() , "Agrolait", "should contain subscription modifications partner 'Agrolait'");
            assert.strictEqual(salesman_dashboard.$('.o_subscription_row td:eq(5)').text() , "500", "should contain previous MRR Amount '500'");
            assert.strictEqual(salesman_dashboard.$('.o_subscription_row td:eq(6)').text() , "800", "should contain current MRR Amount '800'");
            assert.strictEqual(salesman_dashboard.$('.o_subscription_row td:eq(7)').text() , "300", "should contain delta '300'");
            assert.containsOnce(salesman_dashboard, '#NRR_invoices_' + id, "should display the list of NRR Invoices");
            assert.strictEqual(salesman_dashboard.$('#NRR_invoices_' + id + ' tr:eq(2) td:eq(1)').text(), "Agrolait", "should contain NRR Invoices partner 'Agrolait'");
            assert.strictEqual(salesman_dashboard.$('#NRR_invoices_' + id + ' tr:eq(2) td:eq(3)').text(), "525", "should contain NRR Invoices Amount '525'");
            salesman_dashboard.destroy();
        });

        QUnit.test('can renderer the sale_subscription_salesman in a fragment', async function (assert) {
            // With owl (and the compatibility layer), the client action is rendered in memory and
            // inserted in the DOM before the next animation frame. With this in mind, code using
            // Chart.js must ensure to be in the DOM before trying to use it to render a chart,
            // otherwise it crashes when the lib tries to compute positions in the DOM.
            assert.expect(1);

            const self = this;
            const salesman_dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_salesman(null, {});
            salesman_dashboard.salesman = this.data.fetch_salesmen.default_salesman;
            await testUtils.mock.addMockEnvironment(salesman_dashboard, {
                mockRPC(route) {
                    if (route === '/sale_subscription_dashboard/fetch_salesmen') {
                        return Promise.resolve(self.data.fetch_salesmen);
                    }
                    if (route === '/sale_subscription_dashboard/get_values_salesmen') {
                        return Promise.resolve(self.data.salesman_values);
                    }
                    return Promise.resolve();
                },
            });
            await salesman_dashboard.appendTo(document.createDocumentFragment());
            await testUtils.nextTick();

            salesman_dashboard.$el.appendTo($('#qunit-fixture'));
            salesman_dashboard.on_attach_callback();
            await testUtils.nextTick();

            const id = this.data.fetch_salesmen.salesman_ids[0].id;
            assert.containsOnce(
                salesman_dashboard, '#mrr_growth_salesman_' + id,
                " should display the salesman graph"
            );

            salesman_dashboard.destroy();
        });

        QUnit.test('clicking on a box make the right doAction', async function (assert) {
            assert.expect(3);

            const self = this;
            const dashboard = new SubscriptionDashBoard.sale_subscription_dashboard_main(null, {});
            dashboard.salesman = this.data.fetch_salesmen.default_salesman;
            await testUtils.mock.addMockEnvironment(dashboard, {
                mockRPC(route) {
                    if (route === '/sale_subscription_dashboard/fetch_data') {
                        return Promise.resolve(self.data.fetch_data);
                    }
                    if (route === '/sale_subscription_dashboard/compute_graph_and_stats') {
                        return Promise.resolve(self.data.compute_stats_graph);
                    }
                    if (route === '/sale_subscription_dashboard/get_default_values_forecast') {
                        return Promise.resolve(self.data.forecast_values);
                    }
                },
                intercepts: {
                    do_action({ data }) {
                        assert.strictEqual(data.action, "sale_subscription_dashboard.action_subscription_dashboard_report_detailed");

                        // checking only the keys as the value contain dates that are painful
                        // to deal with in tests due to timzeones.
                        assert.deepEqual(Object.keys(data.options), [
                            "stat_types",
                            "selected_stat",
                            "start_date",
                            "end_date",
                            "contract_templates",
                            "tags",
                            "companies",
                            "filters",
                            "currency_id",
                            "push_main_state",
                            "sales_team",
                            "dashboard_options",
                            "props",
                            "on_reverse_breadcrumb",
                        ]);
                        assert.deepEqual(Object.keys(data.options.props), [
                            "stat_types",
                            "selected_stat",
                            "start_date",
                            "end_date",
                            "contract_templates",
                            "tags",
                            "companies",
                            "filters",
                            "currency_id",
                            "sales_team",
                            "dashboard_options"
                        ]);
                    }
                }
            });
            await dashboard.appendTo(testUtils.prepareTarget());
            dashboard.on_attach_callback();
            await testUtils.nextTick();
            await testUtils.dom.click(dashboard.$(".on_stat_box"));

            dashboard.destroy();
        });
    });
});

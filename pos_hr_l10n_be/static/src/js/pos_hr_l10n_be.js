odoo.define('pos_hr_l10n_be.pos_hr_l10n_be', function (require) {
    var core = require('web.core');
    var { Gui } = require('point_of_sale.Gui');
    var models = require('point_of_sale.models');
    var devices = require('point_of_sale.devices');

    var _t = core._t;

     devices.ProxyDevice.include({
        //allow the use of the employee INSZ number
        _get_insz_or_bis_number: function() {
            if(this.pos.config.module_pos_hr) {
                var insz = this.pos.get_cashier().insz_or_bis_number;
                if (! insz) {
                    Gui.showPopup('ErrorPopup',{
                        'title': _t("Fiscal Data Module error"),
                        'body': _t("INSZ or BIS number not set for current cashier."),
                    });
                    return false;
                }
                return insz;
            }
            else
                return this._super();
        }
     });

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        check_if_user_clocked: function() {
            if(!this.config.module_pos_hr)
                return posmodel_super.check_if_user_clocked.apply(this,arguments);
            var employee_id = this.get_cashier().id;
            return this.pos_session.employees_clocked_ids.find(function(elem) { return elem === employee_id });
        },
        get_args_for_clocking: function() {
            if(!this.config.module_pos_hr)
                return posmodel_super.get_args_for_clocking.apply(this,arguments);
            return [this.pos_session.id, this.get_cashier().id];
        },
        set_clock_values: function(values) {
            if(!this.config.module_pos_hr)
                return posmodel_super.set_clock_values.apply(this,arguments);
            this.pos_session.employees_clocked_ids = values;
        },
        get_method_call_for_clocking: function() {
            if(!this.config.module_pos_hr)
               return posmodel_super.get_method_call_for_clocking.apply(this,arguments);
            return 'get_employee_session_work_status';
        },
        set_method_call_for_clocking: function() {
            if(!this.config.module_pos_hr)
               return posmodel_super.set_method_call_for_clocking.apply(this,arguments);
            return 'set_employee_session_work_status';
        }
    });

    models.load_models({
        model: "pos.order",
        domain: function (self) { return [['config_id', '=', self.config.id]]; },
        fields: ['name', 'hash_chain'],
        order:  _.map(['date_order'], function (name) { return {name: name, asc: false}; }),
        limit: 1,  // TODO this works?
        loaded: function (self, params) {
            self.config.backend_sequence_number = self._extract_order_number(params);
            self.config.blackbox_most_recent_hash = self._get_hash_chain(params);
        }
    }, {
        'after': "pos.config"
    });

    // pro forma and regular orders share numbers, so we also need to check the pro forma orders and pick the max
    models.load_models({
        model: "pos.order_pro_forma",
        domain: function (self) { return [['config_id', '=', self.config.id]]; },
        fields: ['name', 'hash_chain'],
        order:  _.map(['date_order'], function (name) { return {name: name, asc: false}; }),
        limit: 1,
        loaded: function (self, params) {
            var pro_forma_number = self._extract_order_number(params);

            if (pro_forma_number > self.config.backend_sequence_number) {
                self.config.backend_sequence_number = pro_forma_number;
                self.config.most_recent_hash = self._get_hash_chain(params);
            }
        }
    }, {
        'after': "pos.order"
    });

    models.load_models({
        'model': "ir.model.data",
        'domain': ['|', ['name', '=', 'product_product_work_in'], ['name', '=', 'product_product_work_out']],
        'fields': ['name', 'res_id'],
        'loaded': function (self, params) {
            params.forEach(function (current, index, array) {
                if (current.name === "product_product_work_in") {
                    self.work_in_product = self.db.product_by_id[current['res_id']];
                } else if (current.name === "product_product_work_out") {
                    self.work_out_product = self.db.product_by_id[current['res_id']];
                }
            });
        }
    }, {
        'after': "product.product"
    });

    models.load_fields("hr.employee", "insz_or_bis_number");
    models.load_fields("pos.session", "employees_clocked_ids");
});

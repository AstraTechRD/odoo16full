odoo.define('account_base_import.import', function (require) {
    "use strict";
    var core = require("web.core");
    var BaseImport = require("base_import.import");

    var _t = core._t;

    BaseImport.DataImport.include({
        import_options: function () {
            var options = this._super();
            if (this.res_model == "account.move.line") {
                var enabled_fields = {
                    "journal_id": true,
                    "account_id": true,
                    "partner_id": true,
                }
                options["name_create_enabled_fields"] = { ...options["name_create_enabled_fields"], ...enabled_fields }
            }
            return options;
        },

        exit: function () {
            if (this.current === "imported" && ["account.move.line", "account.account", "res.partner"].includes(this.res_model)) {
                const names = {
                    "account.move.line": _t("Journal Items"),
                    "account.account": _t("Chart of Accounts"),
                    "res.partner": _t("Customers"),
                }
                var action = {
                    name: names[this.res_model],
                    res_model: this.res_model,
                    type: "ir.actions.act_window",
                    views: [[false, "list"], [false, "form"]],
                    view_mode: "list",
                }
                if (this.res_model == "account.move.line") {
                    action.context = { "search_default_posted": 0 };
                }
                this.do_action(action);
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
});

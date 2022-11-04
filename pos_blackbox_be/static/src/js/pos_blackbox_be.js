/* global Sha1 */
odoo.define('pos_blackbox_be.pos_blackbox_be', function (require) {
    var models = require('point_of_sale.models');
    const { Gui } = require('point_of_sale.Gui');
    var core    = require('web.core');
    var Class = require('web.Class');
    var devices = require('point_of_sale.devices');
    var _t      = core._t;
    const utils = require('web.utils');
    const round_pr = utils.round_precision;

    var orderline_super = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        // generates a table of the form
        // {..., 'char_to_translate': translation_of_char, ...}
        _generate_translation_table: function () {
            var replacements = [
                ["ÄÅÂÁÀâäáàã", "A"],
                ["Ææ", "AE"],
                ["ß", "SS"],
                ["çÇ", "C"],
                ["ÎÏÍÌïîìí", "I"],
                ["€", "E"],
                ["ÊËÉÈêëéè", "E"],
                ["ÛÜÚÙüûúù", "U"],
                ["ÔÖÓÒöôóò", "O"],
                ["Œœ", "OE"],
                ["ñÑ", "N"],
                ["ýÝÿ", "Y"]
            ];

            var lowercase_to_uppercase = _.range("a".charCodeAt(0), "z".charCodeAt(0) + 1).map(function (lowercase_ascii_code) {
                return [String.fromCharCode(lowercase_ascii_code), String.fromCharCode(lowercase_ascii_code).toUpperCase()];
            });
            replacements = replacements.concat(lowercase_to_uppercase);

            var lookup_table = {};

            _.forEach(replacements, function (letter_group) {
                _.forEach(letter_group[0], function (special_char) {
                    lookup_table[special_char] = letter_group[1];
                });
            });

            return lookup_table;
        },

        _replace_hash_and_sign_chars: function (str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var translation_table = this._generate_translation_table();

            var replaced_char_array = _.map(str, function (char, index, str) {
                var translation = translation_table[char];
                if (translation) {
                    return translation;
                } else {
                    return char;
                }
            });

            return replaced_char_array.join("");
        },

        // for hash and sign the allowed range for DATA is:
        //   - A-Z
        //   - 0-9
        // and SPACE as well. We filter SPACE out here though, because
        // SPACE will only be used in DATA of hash and sign as description
        // padding
        _filter_allowed_hash_and_sign_chars: function (str) {
            if (typeof str !== 'string') {
                throw "Can only handle strings";
            }

            var filtered_char_array = _.filter(str, function (char) {
                var ascii_code = char.charCodeAt(0);

                if ((ascii_code >= "A".charCodeAt(0) && ascii_code <= "Z".charCodeAt(0)) ||
                    (ascii_code >= "0".charCodeAt(0) && ascii_code <= "9".charCodeAt(0))) {
                    return true;
                } else {
                    return false;
                }
            });

            return filtered_char_array.join("");
        },

        // for both amount and price
        // price should be in eurocent
        // amount should be in gram
        _prepare_number_for_plu: function (number, field_length) {
            number = Math.abs(number);
            number = Math.round(number); // todo jov: don't like this

            var number_string = number.toFixed(0);

            number_string = this._replace_hash_and_sign_chars(number_string);
            number_string = this._filter_allowed_hash_and_sign_chars(number_string);

            // get the required amount of least significant characters
            number_string = number_string.substr(-field_length);

            // pad left with 0 to required size
            while (number_string.length < field_length) {
                number_string = "0" + number_string;
            }

            return number_string;
        },

        _prepare_description_for_plu: function (description) {
            description = this._replace_hash_and_sign_chars(description);
            description = this._filter_allowed_hash_and_sign_chars(description);

            // get the 20 most significant characters
            description = description.substr(0, 20);

            // pad right with SPACE to required size of 20
            while (description.length < 20) {
                description = description + " ";
            }

            return description;
        },

        _get_amount_for_plu: function () {
            // three options:
            // 1. unit => need integer
            // 2. weight => need integer gram
            // 3. volume => need integer milliliter

            var amount = this.get_quantity();
            var uom = this.get_unit();

            if (uom.is_unit) {
                return amount;
            } else {
                if (uom.category_id[1] === "Weight") {
                    var uom_gram = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Weight" && unit.name === "g";
                    });
                    amount = (amount / uom.factor) * uom_gram.factor;
                } else if (uom.category_id[1] === "Volume") {
                    var uom_milliliter = _.find(this.pos.units_by_id, function (unit) {
                        return unit.category_id[1] === "Volume" && unit.name === "Milliliter(s)";
                    });
                    amount = (amount / uom.factor) * uom_milliliter.factor;
                }

                return amount;
            }
        },

        get_vat_letter: async function () {
            if(this.pos.useBlackBoxBe()) {
                const firstTax = this.get_taxes()[0];
                const taxes = this.pos.get_taxes_after_fp(firstTax ? [firstTax.id] : [], this.order.fiscal_position);

                 if (!taxes) {
                    if (this.pos.gui.popup_instances.error) {
                        await Gui.showPopup('ErrorPopup', {
                            'title': _t("POS error"),
                            'body': _t("Product has no tax associated with it."),
                        });

                         return false;
                    }
                }

                var vat_letter = taxes[0].identification_letter;
                if (!vat_letter) {
                    if (this.pos.gui.popup_instances.error) {
                        await Gui.showPopup('ErrorPopup', {
                            'title': _t("POS error"),
                            'body': _t("Product has an invalid tax amount. Only 21%, 12%, 6% and 0% are allowed."),
                        });

                        return false;
                    }
                }
            }

            return vat_letter;
        },

        generate_plu_line: function () {
            // |--------+-------------+-------+-----|
            // | AMOUNT | DESCRIPTION | PRICE | VAT |
            // |      4 |          20 |     8 |   1 |
            // |--------+-------------+-------+-----|

            // steps:
            // 1. replace all chars
            // 2. filter out forbidden chars
            // 3. build PLU line

            var amount = this._get_amount_for_plu();
            var description = this.get_product().display_name;
            var price_in_eurocent = this.get_display_price() * 100;
            var vat_letter = this.get_vat_letter();

            amount = this._prepare_number_for_plu(amount, 4);
            description = this._prepare_description_for_plu(description);
            price_in_eurocent = this._prepare_number_for_plu(price_in_eurocent, 8);

            return amount + description + price_in_eurocent + vat_letter;
        },

        can_be_merged_with: function(orderline) {
            var order = this.pos.get_order();
            var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1];

            if(this.pos.useBlackBoxBe() && (order.orderlines._byId[last_id].product.id !== orderline.product.id || order.orderlines._byId[last_id].quantity < 0) && this.blackbox_pro_forma_finalized) {
                return false;
            } else {
                return orderline_super.can_be_merged_with.apply(this, arguments);
            }
        },

        _show_finalized_error: async function () {
            await Gui.showPopup("ErrorPopup", {
                'title': _t("Order error"),
                'body':  _t("This orderline has already been finalized in a pro forma order and can no longer be modified. Please create a new line with eg. a negative quantity."),
            });
        },

        set_discount: function (discount) {
            if (this.blackbox_pro_forma_finalized) {
                this._show_finalized_error();
            } else {
                orderline_super.set_discount.apply(this, arguments);
            }
        },

        set_unit_price: function (price) {
            if (this.blackbox_pro_forma_finalized) {
                this._show_finalized_error();
            } else {
                orderline_super.set_unit_price.apply(this, arguments);
            }
        },

        init_from_JSON: function (json) {
            orderline_super.init_from_JSON.apply(this, arguments);
            this.blackbox_pro_forma_finalized = json.blackbox_pro_forma_finalized;
        },

        export_as_JSON: function () {
            var json = orderline_super.export_as_JSON.apply(this, arguments);

            return _.extend(json, {
                'vat_letter': this.get_vat_letter(),
                'blackbox_pro_forma_finalized': this.blackbox_pro_forma_finalized
            });
        },

        export_for_printing: function () {
            var json = orderline_super.export_for_printing.apply(this, arguments);

            return _.extend(json, {
                'vat_letter': this.get_vat_letter()
            });
        }
    });


    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        useBlackBoxBe: function() {
            return true;
        },
        check_if_user_clocked: function() {
            return this.pos_session.users_clocked_ids.find(elem => elem === this.user.id);
        },
        extract_order_number: function (records) {
            if (records.length) {
                return parseInt(records[0]['name'].match(/\d+$/)[0], 10);
            } else {
                return 0;
            }
        },

        _get_hash_chain: function (records) {
            if (records.length) {
                return records[0]['hash_chain'];
            } else {
                return "";
            }
        },

        _prepare_date_for_ticket: function (date) {
            // format of date coming from blackbox is YYYYMMDD
            var year = date.substr(0, 4);
            var month = date.substr(4, 2);
            var day = date.substr(6, 2);

            return day + "/" + month + "/" + year;
        },

        _prepare_time_for_ticket: function (time) {
            // format of time coming from blackbox is HHMMSS
            var hours = time.substr(0, 2);
            var minutes = time.substr(2, 2);
            var seconds = time.substr(4, 2);

            return hours + ":" + minutes + ":" + seconds;
        },

        _prepare_ticket_counter_for_ticket: function (counter, total_counter, event_type) {
            return counter + "/" + total_counter + " " + event_type;
        },

        _prepare_hash_for_ticket: function (hash) {
            var amount_of_least_significant_characters = 8;

            return hash.substr(-amount_of_least_significant_characters);
        },

        _check_validation_constraints: async function () {
            if (! this.company.street) {
                await Gui.showPopup('ErrorPopup', {
                    'title': _t("Fiscal Data Module error"),
                    'body':  _t("Company address must be set."),
                });

                return false;
            } else if (! this.company.vat) {
                await Gui.showPopup('ErrorPopup', {
                    'title': _t("Fiscal Data Module error"),
                    'body':  _t("VAT number must be set."),
                });

                return false;
            }

            return true;
        },

                _check_iotbox_serial: function (data) {
            var self = this;
            if (!data.value) {
                this.proxy._show_could_not_connect_error(_t("Unreachable FDM"));
            } else if ("BODO001" + data.value.toUpperCase() != this.config.blackbox_pos_production_id.toUpperCase()) {
                this.proxy._show_could_not_connect_error(
                    _t("Incorrect PosBox serial") + ' ' + this.config.blackbox_pos_production_id.toUpperCase()
                );
            } else {
                this.chrome.ready.then(function () {
                    $(self.chrome.$el).find('.placeholder-posVersion').text(' Ver: ' + self.version.server_version + "1807BE_FDM");
                    $(self.chrome.$el).find('.placeholder-posID').text(' ID: ' + self.config.blackbox_pos_production_id);
                });
            }
        },

        connect_to_proxy: function () {
            if(this.config.blackbox_pos_production_id) {
                var self = this;
                var fdm = this.iot_device_proxies.fiscal_data_module;
                return posmodel_super.connect_to_proxy.apply(this, arguments).then(function () {
                    fdm.add_listener(self._check_iotbox_serial.bind(self));
                    fdm.action({ action: 'request_serial' });
                });
            } else {
                return Promise.resolve();
            }
        },

        push_order_to_blackbox: function (order) {
            var self = this;

            if (! this._check_validation_constraints()) {
                return Promise.reject();
            }

            order.set_validation_time();
            order.blackbox_amount_total = order.get_total_with_tax();
            order.blackbox_base_price_in_euro_per_tax_letter = order.get_base_price_in_euro_per_tax_letter_list();

            var packet = this.proxy._build_fdm_hash_and_sign_request(order);
            if (!packet) {
                return Promise.reject();
            }
            var prom = this.proxy.request_fdm_hash_and_sign(packet).then(function (parsed_response) {
                return new Promise(function (resolve, reject) {
                    if (parsed_response) {
                        // put fields that we need on tickets on order
                        order.blackbox_order_name = self.config.name + "/" + self.config.backend_sequence_number;
                        order.blackbox_date = self._prepare_date_for_ticket(parsed_response.date);
                        order.blackbox_time = self._prepare_time_for_ticket(parsed_response.time);
                        order.blackbox_ticket_counters =
                        self._prepare_ticket_counter_for_ticket(parsed_response.vsc_ticket_counter,
                                                                parsed_response.vsc_total_ticket_counter,
                                                                parsed_response.event_label);
                        order.blackbox_signature = parsed_response.signature;
                        order.blackbox_vsc_identification_number = parsed_response.vsc_identification_number;
                        order.blackbox_unique_fdm_production_number = parsed_response.fdm_unique_production_number;
                        order.blackbox_plu_hash = self._prepare_hash_for_ticket(packet.fields[packet.fields.length - 1].content);
                        order.blackbox_pos_version = "Odoo " + self.version.server_version + "1807BE_FDM";
                        order.blackbox_pos_production_id = self.config.blackbox_pos_production_id;
                        order.blackbox_terminal_id = self.blackbox_terminal_id;

                        self.config.blackbox_most_recent_hash = self._prepare_hash_for_ticket(Sha1.hash(self.config.blackbox_most_recent_hash + order.blackbox_plu_hash));
                        order.blackbox_hash_chain = self.config.blackbox_most_recent_hash;


                        resolve();
                    } else {
                        reject();
                    }
                });
            });

            return prom;
        },

        _push_pro_forma: function () {
            var old_order = this.get_order();

            // Only push orders with something in them as pro forma.
            // Also don't push orders which have pro_forma set to
            // false. Because those are 'real orders' that we already
            // handled.
            if (old_order && old_order.get_orderlines().length && old_order.blackbox_pro_forma !== false) {
                return this.push_orders(old_order, {'pro_forma': true});
            } else {
                return Promise.reject();
            }
        },

        // for pos_loyalty
        _split_discount_lines: function () {
            var self = this;
            var order = this.get_order();
            var lines_to_delete = [];
            var lines_to_add = [];

            order.get_orderlines().forEach(function (line) {
                // discount or resale
                if (line.reward_id && line.get_price_with_tax() < 0) {
                    var discount_line = line;
                    lines_to_delete.push(line);

                    var price_per_tax_letter = order.get_price_in_eurocent_per_tax_letter();

                    // we need to filter out negative orderlines
                    var order_total = self.get_order().get_total_with_tax_without_discounts();
                    var resale_quantity = discount_line.get_quantity();

                    // 1. delete line
                    // 2. re-add lines with the same product id but with modified taxes
                    //    essentially just adding a discount_percentage_on_order% per tax

                    _.forEach(_.pairs(price_per_tax_letter), function (tax) {
                        tax[1] = tax[1] / 100; // was in eurocents
                        if (tax[1] > 0.00001) {
                            var percentage_of_this_tax_in_total = round_pr(tax[1] / order_total, 0.01);

                            // add correct tax on product
                            var new_line_tax = _.find(self.taxes, function (pos_tax) {
                                return tax[0] === pos_tax.identification_letter;
                            });

                            var cloned_product = _.clone(discount_line.product);

                            cloned_product.taxes_id = [new_line_tax.id];

                            lines_to_add.push([cloned_product, {
                                quantity: resale_quantity * percentage_of_this_tax_in_total,
                                merge: false,
                                extras: { reward_id: discount_line.reward_id },
                            }]);
                        }
                    });
                }
            });

            _.map(lines_to_delete, function (line) { self.get_order().remove_orderline(line); });
            _.map(lines_to_add, function (line) { self.get_order().add_product.apply(self.get_order(), line); });
        },

        add_new_order: function () {
            this._push_pro_forma();

            return posmodel_super.add_new_order.apply(this, arguments);
        },

        set_order: function (order) {
            this._push_pro_forma();

            return posmodel_super.set_order.apply(this, arguments);
        },

        // we need to be able to identify devices that do
        // transactions, the best we can do is to generate a terminal
        // id per device in localstorage and use that. We don't use
        // the PosDB because it uses a name prefix that allows
        // multiple db's per browser (in theory).
        get_blackbox_terminal_id: function () {
            if (!localStorage.odoo_pos_blackbox_pos_production_id) {
                // the production id needs to be 14 characters long,
                // so we can generate a 64 bit id and encode it in
                // base 36, which gives us a max size of 13.
                var production_id = Math.floor(Math.random() * Math.pow(2, 64)) + 1;

                // represent it as a string with base 36 for compactness
                production_id = production_id.toString(36);

                // pad it with 0 so it's exactly 14 characters
                while (production_id.length < 14) {
                    production_id = "0" + production_id;
                }

                localStorage.odoo_pos_blackbox_pos_production_id = production_id;
            }

            return localStorage.odoo_pos_blackbox_pos_production_id;
        },

//        after_load_server_data: function () {
//            var self = this;
//            // with this module we will always have to connect to the
//            // proxy, regardless of user preferences
//            this.config.use_proxy = true;
//            this.blackbox_terminal_id = this.get_blackbox_terminal_id() || false;
//
//            this.chrome.ready.then(function () {
//                var current = $(self.chrome.$el).find('.placeholder-terminalID').text();
//                $(self.chrome.$el).find('.placeholder-terminalID').text(' TID: ' + self.blackbox_terminal_id);
//            });
//
//            // With pos_cache product.product isn't loaded the normal uncached way.
//            // So there are no products in pos.db when models are loaded and
//            // work_in_product / work_out_product end up unidentified.
//            if (!self.work_in_product) {
//                var products = this.db.product_by_id;
//                for (var id in products) {
//                    if (products[id].display_name === 'WORK IN') {
//                        self.work_in_product = products[id];
//                    } else if (products[id].display_name === 'WORK OUT') {
//                        self.work_out_product = products[id];
//                    }
//                }
//            }
//
//            return posmodel_super.after_load_server_data.apply(this, arguments);
//        },

        removeOrder: async function (order) {
            if (this.useBlackBoxBe() && this.get_order().get_orderlines().length) {
                await Gui.showPopup('ErrorPopup', {
                    'title': _t("Fiscal Data Module error"),
                    'body':  _t("Deleting of orders is not allowed."),
                });
            } else {
                posmodel_super.removeOrder.apply(this, arguments);
            }
        },

        transfer_order_to_different_table: function () {
            if(this.config.blackbox_pos_production_id) {
                var self = this;
                var old_order = this.get_order();
                var new_order = this.add_new_order();
                new_order.draft = true;
                // remove all lines of the previous order and create a new one
                old_order.get_orderlines().forEach(function (current) {
                    var decrease_line = current.clone();
                    decrease_line.order = old_order;
                    decrease_line.set_quantity(-current.get_quantity());
                    old_order.add_orderline(decrease_line);

                    var moved_line = current.clone();
                    moved_line.order = new_order;
                    new_order.add_orderline(moved_line);
                });

                // save the order with canceled lines
                posmodel_super.set_order.call(this, old_order);
                this.push_order(old_order).then(function () {

                    posmodel_super.set_order.call(self, new_order);
                    // disable blackbox_pro_forma to avoid saving a pro forma on set_order(null) call
                    new_order.blackbox_pro_forma = false;
                    new_order.table = null;

                    // show table selection screen
                    posmodel_super.transfer_order_to_different_table.apply(self, arguments);
                    new_order.blackbox_pro_forma = true;
                });
            } else {
                posmodel_super.transfer_order_to_different_table();
            }
         },

//        set_table: function(table) {
//            if(this.config.blackbox_pos_production_id) {
//                if (!table) { // no table ? go back to the floor plan, see ScreenSelector
//                    this.set_order(null);
//                } else if (this.order_to_transfer_to_different_table) {
//                    this.order_to_transfer_to_different_table.table = table;
//                    this.order_to_transfer_to_different_table.save_to_db();
//                    this.order_to_transfer_to_different_table = null;
//
//                    // set this table
//                    this.set_table(table);
//
//                } else {
//                    this.table = table;
//                    var orders = this.get_order_list();
//                    if (orders.length) {
//                        this.set_order(orders[0]); // and go to the first one ...
//                    } else {
//                        this.add_new_order();  // or create a new order with the current table
//                    }
//                }
//            } else {
//                return posmodel_super.set_table.apply(this, table);
//            }
//        },
    });


    var order_model_super = models.Order.prototype;
    models.Order = models.Order.extend({
        export_as_JSON: function () {
            var json = order_model_super.export_as_JSON.bind(this)();

            var to_return = _.extend(json, {
                'blackbox_date': this.blackbox_date,
                'blackbox_time': this.blackbox_time,
                'blackbox_amount_total': this.blackbox_amount_total,
                'blackbox_ticket_counters': this.blackbox_ticket_counters,
                'blackbox_unique_fdm_production_number': this.blackbox_unique_fdm_production_number,
                'blackbox_vsc_identification_number': this.blackbox_vsc_identification_number,
                'blackbox_signature': this.blackbox_signature,
                'blackbox_plu_hash': this.blackbox_plu_hash,
                'blackbox_pos_version': this.blackbox_pos_version,
                'blackbox_pos_production_id': this.blackbox_pos_production_id,
                'blackbox_terminal_id': this.blackbox_terminal_id,
                'blackbox_pro_forma': this.blackbox_pro_forma,
                'blackbox_hash_chain': this.blackbox_hash_chain,
            });

            if (this.blackbox_base_price_in_euro_per_tax_letter) {
                to_return = _.extend(to_return, {
                    'blackbox_tax_category_a': this.blackbox_base_price_in_euro_per_tax_letter[0].amount,
                    'blackbox_tax_category_b': this.blackbox_base_price_in_euro_per_tax_letter[1].amount,
                    'blackbox_tax_category_c': this.blackbox_base_price_in_euro_per_tax_letter[2].amount,
                    'blackbox_tax_category_d': this.blackbox_base_price_in_euro_per_tax_letter[3].amount,
                });
            }

            if (this.blackbox_pos_receipt_time) {
                var DEFAULT_SERVER_DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss";
                var original_zone = this.blackbox_pos_receipt_time.utcOffset();

                this.blackbox_pos_receipt_time.utcOffset(0); // server expects UTC
                to_return['blackbox_pos_receipt_time'] = this.blackbox_pos_receipt_time.format(DEFAULT_SERVER_DATETIME_FORMAT);
                this.blackbox_pos_receipt_time.utcOffset(original_zone);
            }

            return to_return;
        },

        export_for_printing: function () {
            var receipt = order_model_super.export_for_printing.bind(this)();

            receipt = _.extend(receipt, {
                'company': _.extend(receipt.company, {
                    'street': this.pos.company.street
                })
            });

            return receipt;
        },

        export_for_printing: function () {
            var receipt = order_model_super.export_for_printing.bind(this)();

            receipt = _.extend(receipt, {
                'company': _.extend(receipt.company, {
                    'street': this.pos.company.street
                })
            });

            return receipt;
        },

        // don't allow to add orderlines without a vat letter
        add_orderline: function (line) {
            if (line.get_vat_letter()) {
                order_model_super.add_orderline.apply(this, arguments);
            }
        },

        add_product: async function (product, options) {
            if (this.pos.useBlackBoxBe() && !this.pos.check_if_user_clocked() && product !== this.pos.work_in_product) {
                await Gui.showPopup('ErrorPopup', {
                    title: _t("POS error"),
                    body: _t("Session is not initialized yet. Register a Work In event first."),
                });
            } else if (this.pos.useBlackBoxBe && product.taxes_id.length === 0) {
                await Gui.showPopup('ErrorPopup', {
                    title: _t("POS error"),
                    body: _t("Product has no tax associated with it."),
                });
            } else if (this.pos.useBlackBoxBe && !this.pos.taxes_by_id[product.taxes_id[0]].identification_letter) {
                await Gui.showPopup('ErrorPopup', {
                    title: _t("POS error"),
                    body: _t("Product has an invalid tax amount. Only 21%, 12%, 6% and 0% are allowed."),
                });
            } else {
                return order_model_super.add_product.apply(this, arguments);
            }

            return false;
        },

        _hash_and_sign_string: function () {
            var order_str = "";

            this.get_orderlines().forEach(function (current, index, array) {
                order_str += current.generate_plu_line();
            });

            return order_str;
        },

        get_total_with_tax_without_discounts: function () {
            var positive_orderlines = _.filter(this.get_orderlines(), function (line) {
                return line.get_price_without_tax() > 0;
            });

            var total_without_tax = round_pr(positive_orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_price_without_tax();
            }), 0), this.pos.currency.rounding);

            var total_tax = round_pr(positive_orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_tax();
            }), 0), this.pos.currency.rounding);

            return total_without_tax + total_tax;
        },

        get_tax_percentage_for_tax_letter: function (tax_letter) {
            var percentage_per_letter = {
                'A': 21,
                'B': 12,
                'C': 6,
                'D': 0
            };

            return percentage_per_letter[tax_letter];
        },

        get_price_in_eurocent_per_tax_letter: function (base) {
            var price_per_tax_letter = {
                'A': 0,
                'B': 0,
                'C': 0,
                'D': 0
            };

            this.get_orderlines().forEach(function (current, index, array) {
                var tax_letter = current.get_vat_letter();

                if (tax_letter) {
                    if (base) {
                        price_per_tax_letter[tax_letter] += Math.round(current.get_price_without_tax() * 100);
                    } else {
                        price_per_tax_letter[tax_letter] += Math.round(current.get_price_with_tax() * 100);
                    }
                }
            });

            return price_per_tax_letter;
        },

        // returns an array of the form:
        // [{'letter', 'amount'}, {'letter', 'amount'}, ...]
        get_base_price_in_euro_per_tax_letter_list: function () {
            var base_price_per_tax_letter = this.get_price_in_eurocent_per_tax_letter("base price");
            var base_price_per_tax_letter_list = _.map(_.keys(base_price_per_tax_letter), function (key) {
                return {
                    'letter': key,
                    'amount': base_price_per_tax_letter[key] / 100
                };
            });

            return base_price_per_tax_letter_list;
        },

        calculate_hash: function () {
            return Sha1.hash(this._hash_and_sign_string());
        },

        set_validation_time: function () {
            this.blackbox_pos_receipt_time = moment();
        },
        wait_for_push_order: function () {
            var result = order_model_super.wait_for_push_order.apply(this,arguments);
            result = Boolean(this.pos.useBlackBoxBe() || result);
            return result;
        },
    });

        var FDMPacketField = Class.extend({
        init: function (name, length, content, pad_character) {
            if (typeof content !== 'string') {
                throw "Can only handle string contents";
            }

            if (content.length > length) {
                throw "Content (" + content + ") too long (should be max " + length + ")";
            }

            this.name = name;
            this.length = length;

            this.content = this._pad_left_to_length(content, pad_character);
        },

        _pad_left_to_length: function (content, pad_character) {
            if (content.length < this.length && ! pad_character) {
                throw "Can't pad without a pad character";
            }

            while (content.length < this.length) {
                content = pad_character + content;
            }

            return content;
        },

        to_string: function () {
            return this.content;
        }
    });

    var FDMPacket = Class.extend({
        init: function () {
            this.fields = [];
        },

        add_field: function (field) {
            this.fields.push(field);
        },

        to_string: function () {
            return _.map(this.fields, function (field) {
                return field.to_string();
            }).join("");
        },

        to_human_readable_string: function () {
            return _.map(this.fields, function (field) {
                return field.name + ": " + field.to_string();
            }).join("\n");
        }
    });

    devices.ProxyDevice.include({
        _get_sequence_number: function () {
            var sequence_number = this.pos.db.load('sequence_number', 0);
            this.pos.db.save('sequence_number', (sequence_number + 1) % 100);

            return sequence_number;
        },

        build_request: function (id) {
            var packet = new FDMPacket();

            packet.add_field(new FDMPacketField("id", 1, id));
            packet.add_field(new FDMPacketField("sequence number", 2, this._get_sequence_number().toString(), "0"));
            packet.add_field(new FDMPacketField("retry number", 1, "0"));

            return packet;
        },

        // ignore_non_critical: will ignore warnings and will ignore
        // certain 'real' errors defined in non_critical_errors
        _handle_fdm_errors: async function (parsed_response, ignore_non_critical) {
            var self = this;
            var error_1 = parsed_response.error_1;
            var error_2 = parsed_response.error_2;

            var non_critical_errors = [
                1, // no vat signing card
                2, // initialize vat signing card with pin
                3, // vsc blocked
                5, // memory full
                9, // real time clock corrupt
                10, // vsc not compatible
            ];


            // TODO: check after migration all error 1 by 1.

            if (error_1 === 0) { // no errors
                if (error_2 === 1) {
                    this.pos.gui.show_popup("confirm", {
                        'title': _t("Fiscal Data Module"),
                        'body':  _t("PIN accepted."),
                    });
                }

                return true;
            } else if (error_1 === 1 && ! ignore_non_critical) { // warnings
                if (error_2 === 1) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module warning"),
                        'body':  _t("Fiscal Data Module memory 90% full."),
                    });
                } else if (error_2 === 2) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module warning"),
                        'body':  _t("Already handled request."),
                    });
                } else if (error_2 === 3) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module warning"),
                        'body':  _t("No record."),
                    });
                } else if (error_2 === 99) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module warning"),
                        'body':  _t("Unspecified warning."),
                    });
                }

                return true;
            } else { // errors
                if (ignore_non_critical && non_critical_errors.indexOf(error_2) !== -1) {
                    return true;
                }

                if (error_2 === 1) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("No Vat Signing Card or Vat Signing Card broken."),
                    });
                } else if (error_2 === 2) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Please initialize the Vat Signing Card with PIN."),
                        'confirm': function (pin) {
                            self.pos.proxy.request_fdm_pin_verification(pin);
                        }
                    });
                } else if (error_2 === 3) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Vat Signing Card blocked."),
                    });
                } else if (error_2 === 4) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Invalid PIN."),
                    });
                } else if (error_2 === 5) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Fiscal Data Module memory full."),
                    });
                } else if (error_2 === 6) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Unknown identifier."),
                    });
                } else if (error_2 === 7) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Invalid data in message."),
                    });
                } else if (error_2 === 8) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Fiscal Data Module not operational."),
                    });
                } else if (error_2 === 9) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Fiscal Data Module real time clock corrupt."),
                    });
                } else if (error_2 === 10) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Vat Signing Card not compatible with Fiscal Data Module."),
                    });
                } else if (error_2 === 99) {
                    await Gui.showPopup('ErrorPopup', {
                        'title': _t("Fiscal Data Module error"),
                        'body':  _t("Unspecified error."),
                    });
                }

                return false;
            }
        },

        _parse_fdm_common_response: function (response) {
            return {
                identifier: response[0],
                sequence_number: parseInt(response.substr(1, 2), 10),
                retry_counter: parseInt(response[3], 10),
                error_1: parseInt(response[4], 10),
                error_2: parseInt(response.substr(5, 2), 10),
                error_3: parseInt(response.substr(7, 3), 10),
                fdm_unique_production_number: response.substr(10, 11),
            };
        },

        parse_fdm_identification_response: function (response) {
            return _.extend(this._parse_fdm_common_response(response),
                            {
                                fdm_firmware_version_number: response.substr(21, 20),
                                fdm_communication_protocol_version: response[41],
                                vsc_identification_number: response.substr(42, 14),
                                vsc_version_number: parseInt(response.substr(56, 3), 10)
                            });
        },

        parse_fdm_pin_response: function (response) {
            return _.extend(this._parse_fdm_common_response(response),
                            {
                                vsc_identification_number: response.substr(21, 14),
                            });
        },

        parse_fdm_hash_and_sign_response: function (response) {
            return _.extend(this._parse_fdm_common_response(response),
                            {
                                vsc_identification_number: response.substr(21, 14),
                                date: response.substr(35, 8),
                                time: response.substr(43, 6),
                                event_label: response.substr(49, 2),
                                vsc_ticket_counter: parseInt(response.substr(51, 9)),
                                vsc_total_ticket_counter: parseInt(response.substr(60, 9)),
                                signature: response.substr(69, 40)
                            });
        },

        _build_fdm_identification_request: function () {
            return this.build_request("I");
        },

        _build_fdm_pin_request: function (pin) {
            var packet = this.build_request("P");
            packet.add_field(new FDMPacketField("pin code", 5, pin.toString(), "0"));

            return packet;
        },

        // fdm needs amounts in cents with at least 3 numbers (eg. 0.5
        // euro => '050') and encoded as a string
        _amount_to_fdm_amount_string: function (amount) {
            amount *= 100; // to eurocent
            amount = round_pr(amount, 0.01); // make sure it's properly rounded (to avoid eg. x.9999999999999999999)
            amount = amount.toString();

            while (amount.length < 3) {
                amount = "0" + amount;
            }

            return amount;
        },

        _get_insz_or_bis_number: function() {
            var insz = this.pos.user.insz_or_bis_number;
            if (! insz) {
                this.pos.gui.show_popup('error',{
                    'title': _t("Fiscal Data Module error"),
                    'body': _t("INSZ or BIS number not set for current cashier."),
                });
                return false;
            }
            return insz;
        },

        // todo jov: p77
        _build_fdm_hash_and_sign_request: function (order) {
            var packet = this.build_request("H");
            var insz_or_bis_number = this._get_insz_or_bis_number();

            if (! insz_or_bis_number) {
                return false;
            }

            packet.add_field(new FDMPacketField("ticket date", 8, order.blackbox_pos_receipt_time.format("YYYYMMDD")));
            packet.add_field(new FDMPacketField("ticket time", 6, order.blackbox_pos_receipt_time.format("HHmmss")));
            packet.add_field(new FDMPacketField("insz or bis number", 11, insz_or_bis_number));
            packet.add_field(new FDMPacketField("production number POS", 14, this.pos.config.blackbox_pos_production_id));
            packet.add_field(new FDMPacketField("ticket number", 6, (++this.pos.config.backend_sequence_number).toString(), " "));

            if (order.blackbox_pro_forma) {
                packet.add_field(new FDMPacketField("event label", 2, "PS"));
            } else {
                packet.add_field(new FDMPacketField("event label", 2, "NS"));
            }

            packet.add_field(new FDMPacketField("total amount to pay in eurocent", 11, this._amount_to_fdm_amount_string(order.blackbox_amount_total), " "));

            packet.add_field(new FDMPacketField("tax percentage 1", 4, "2100"));
            packet.add_field(new FDMPacketField("amount at tax percentage 1 in eurocent", 11, this._amount_to_fdm_amount_string(order.blackbox_base_price_in_euro_per_tax_letter[0].amount), " "));
            packet.add_field(new FDMPacketField("tax percentage 2", 4, "1200"));
            packet.add_field(new FDMPacketField("amount at tax percentage 2 in eurocent", 11, this._amount_to_fdm_amount_string(order.blackbox_base_price_in_euro_per_tax_letter[1].amount), " "));
            packet.add_field(new FDMPacketField("tax percentage 3", 4, " 600"));
            packet.add_field(new FDMPacketField("amount at tax percentage 3 in eurocent", 11, this._amount_to_fdm_amount_string(order.blackbox_base_price_in_euro_per_tax_letter[2].amount), " "));
            packet.add_field(new FDMPacketField("tax percentage 4", 4, " 000"));
            packet.add_field(new FDMPacketField("amount at tax percentage 4 in eurocent", 11, this._amount_to_fdm_amount_string(order.blackbox_base_price_in_euro_per_tax_letter[3].amount), " "));
            packet.add_field(new FDMPacketField("PLU hash", 40, order.calculate_hash()));

            return packet;
        },

        _show_could_not_connect_error: async function (reason) {
            var body = _t("Could not connect to the Fiscal Data Module.");
            var self = this;
            if (reason) {
                body = body + ' ' + reason;
            }
            setTimeout(function(){self.pos.gui.close()}, 5000);
            await Gui.showPopup('ErrorPopup', {
                'title': _t("Fiscal Data Module error"),
                'body':  body,
            });
        },

        _verify_pin: function (data) {
            if (!data.value) {
                this._show_could_not_connect_error();
            } else {
                // Everything will be changed in 14.0 soon, so we skip the eslint test on this line
                // eslint-disable-next-line no-undef
                var parsed_response = this.parse_fdm_pin_response(response);

                 // pin being verified will show up as 'error'
                this._handle_fdm_errors(parsed_response);
            }
        },

        _check_and_parse_fdm_identification_response: function (resolve, reject, data) {
            if (!data.value) {
                this._show_could_not_connect_error();
                return "";
            } else {
                var parsed_response = this.parse_fdm_identification_response(data.value);
                if (this._handle_fdm_errors(parsed_response, true)) {
                    resolve(parsed_response);
                } else {
                    reject("");
                }
            }
        },

        request_fdm_identification: function () {
            var self = this;
            var fdm = this.pos.iot_device_proxies.fiscal_data_module;
            return new Promise(function (resolve, reject) {
                fdm.add_listener(self._check_and_parse_fdm_identification_response.bind(self, resolve, reject));
                fdm.action({
                    action: 'request',
                    high_level_message: self._build_fdm_identification_request().to_string(),
                    response_size: 59
                });
            });
        },

        request_fdm_pin_verification: function (pin) {
            var self = this;
            var fdm = this.pos.iot_device_proxies.fiscal_data_module;
            fdm.add_listener(self._verify_pin.bind(self));
            fdm.action({
                action: 'request',
                high_level_message: self._build_fdm_pin_request(pin).to_string(),
                response_size: 35
            });
        },

        _check_and_parse_fdm_hash_and_sign_response: function (resolve, reject, hide_error, data) {
            if (!data.value) {
                // Everything will be changed in 14.0 soon, so we skip the eslint test on this line
                // eslint-disable-next-line no-undef
                return this._retry_request_fdm_hash_and_sign(packet, hide_error);
            } else {
                var parsed_response = this.parse_fdm_hash_and_sign_response(data.value);

                 // close any blocking-error popup
                 // TODO: check after migration to owl.
                this.pos.gui.close_popup();

                 if (this._handle_fdm_errors(parsed_response)) {
                    resolve(parsed_response);
                } else {
                    reject("");
                }
            }
        }
    });

    // TODO: Split bill

    models.load_fields("res.users", "insz_or_bis_number");
    models.load_fields("account.tax", "identification_letter");
    models.load_fields("res.company", "street");
    models.load_fields("pos.session", "users_clocked_ids");
});

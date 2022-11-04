odoo.define('l10n_de_pos_cert.pos', function(require) {
    "use strict";

    const { PosGlobalState, Order } = require('point_of_sale.models');
    const { uuidv4 } = require('point_of_sale.utils');
    const { convertFromEpoch } = require('l10n_de_pos_cert.utils');
    const { TaxError } = require('l10n_de_pos_cert.errors');
    var utils = require('web.utils');
    const round_di = utils.round_decimals;
    const Registries = require('point_of_sale.Registries');

    const RATE_ID_MAPPING = {
        1: 'NORMAL',
        2: 'REDUCED_1',
        3: 'SPECIAL_RATE_1',
        4: 'SPECIAL_RATE_2',
        5: 'NULL',
    };


    const L10nDePosGlobalState = (PosGlobalState) => class L10nDePosGlobalState extends PosGlobalState {
        // @Override
        constructor() {
            super(...arguments);
            this.token = '';
            this.vatRateMapping = {};
        }
        //@Override
        async after_load_server_data() {
            if (this.isCountryGermanyAndFiskaly()) {
                await this.env.services.rpc({
                    model: 'pos.config',
                    method: 'l10n_de_get_fiskaly_urls_and_keys',
                    args: [this.config.id]
                }).then(data => {
                    this.company.l10n_de_fiskaly_api_key = data['api_key'];
                    this.company.l10n_de_fiskaly_api_secret = data['api_secret'];
                    this.useKassensichvVersion2 = this.config.l10n_de_fiskaly_tss_id.includes('|');
                    this.apiUrl = data['kassensichv_url'] + '/api/v' + (this.useKassensichvVersion2 ? '2' : '1'); // use correct version
                    this.initVatRates(data['dsfinvk_url'] + '/api/v0');
                })
            }
            return super.after_load_server_data(...arguments);
        }
        getApiToken() {
            return this.token;
        }
        setApiToken(token) {
            this.token = token;
        }
        getApiUrl() {
            return this.apiUrl;
        }
        getApiKey() {
            return this.company.l10n_de_fiskaly_api_key;
        }
        getApiSecret() {
            return this.company.l10n_de_fiskaly_api_secret;
        }
        getTssId() {
            return this.config.l10n_de_fiskaly_tss_id && this.config.l10n_de_fiskaly_tss_id.split('|')[0];
        }
        getClientId() {
            return this.config.l10n_de_fiskaly_client_id;
        }
        isUsingApiV2() {
            return this.useKassensichvVersion2;
        }
        isCountryGermany() {
            return this.config.is_company_country_germany;
        }
        isCountryGermanyAndFiskaly() {
            return this.isCountryGermany() && !!this.getTssId();
        }
        format_round_decimals_currency(value) {
            const decimals = this.currency.decimal_places;
            return round_di(value, decimals).toFixed(decimals);
        }
        initVatRates(url) {
            const data = {
                'api_key': this.getApiKey(),
                'api_secret': this.getApiSecret()
            }

            $.ajax({
                url: url + '/auth',
                method: 'POST',
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).then((data) => {
                const token = data.access_token;
                $.ajax({
                    url: url + '/vat_definitions',
                    method: 'GET',
                    headers: { 'Authorization': `Bearer ${token}` },
                    timeout: 5000
                }).then((vat_data) => {
                    vat_data.data.forEach(vat_definition => {
                        if (!(vat_definition.percentage in this.vatRateMapping)) {
                            this.vatRateMapping[vat_definition.percentage] = RATE_ID_MAPPING[vat_definition.vat_definition_export_id];
                        }
                    })
                }).catch((error) => {
                    // This is a fallback where we hardcode the taxes hoping that they didn't change ...
                    this.vatRateMapping = {
                        19: 'NORMAL',
                        7: 'REDUCED_1',
                        10.70: 'SPECIAL_RATE_1',
                        5.50: 'SPECIAL_RATE_2',
                        0: 'NULL'
                    };
                })
            })
        }
        //@Override
        /**
         * This function first attempts to send the orders remaining in the queue to Fiskaly before trying to
         * send it to Odoo. Two cases can happen:
         * - Failure to send to Fiskaly => we assume that if one order fails, EVERY order will fail
         * - Failure to send to Odoo => the order is already sent to Fiskaly, we store them locally with the TSS info
         */
        async _flush_orders(orders, options) {
            if (!this.isCountryGermanyAndFiskaly()) {
                return super._flush_orders(...arguments);
            }
            if (!orders || !orders.length) {
                return Promise.resolve([]);
            }

            const orderObjectMap = {};
            for (const orderJson of orders) {
                orderObjectMap[orderJson['id']] = Order.create({}, {pos: this, json: orderJson['data']});
            }

            let fiskalyError;
            const sentToFiskaly = [];
            const fiskalyFailure = [];
            const ordersToUpdate = {}
            for (const orderJson of orders) {
                try {
                    const orderObject = orderObjectMap[orderJson['id']];
                    if (!fiskalyError) {
                        if (orderObject.isTransactionInactive()) {
                            await orderObject.createTransaction();
                            ordersToUpdate[orderJson['id']] = true;
                        }
                        if (orderObject.isTransactionStarted()) {
                            await orderObject.finishShortTransaction();
                            ordersToUpdate[orderJson['id']] = true;
                        }
                    }
                    if (orderObject.isTransactionFinished()) {
                        sentToFiskaly.push(orderJson);
                    } else {
                        fiskalyFailure.push(orderJson);
                    }
                } catch (error) {
                    fiskalyError = error;
                    fiskalyError.code = 'fiskaly';
                    fiskalyFailure.push(orderJson);
                }
            }

            let result, odooError;
            if (sentToFiskaly.length > 0) {
                for (const orderJson of sentToFiskaly) {
                    if (ordersToUpdate[orderJson['id']]) {
                        orderJson['data'] = orderObjectMap[orderJson['id']].export_as_JSON();
                    }
                }
                try {
                    result = await super._flush_orders(...arguments);
                } catch (error) {
                    odooError = error;
                }
            }
            if (result && fiskalyFailure.length === 0) {
                return result;
            } else {
                if (Object.keys(ordersToUpdate).length) {
                    for (const orderJson of fiskalyFailure) {
                        if (ordersToUpdate[orderJson['id']]) {
                            orderJson['data'] = orderObjectMap[orderJson['id']].export_as_JSON();
                        }
                    }
                    const ordersToSave = result && result.length ? fiskalyFailure : fiskalyFailure.concat(sentToFiskaly);
                    this.db.save('orders',ordersToSave);
                }
                this.set_synch('disconnected');
                throw odooError || fiskalyError;
            }
        }
    }
    Registries.Model.extend(PosGlobalState, L10nDePosGlobalState);


    const L10nDeOrder = (Order) => class L10nDeOrder extends Order {
        // @Override
        constructor() {
            super(...arguments);
            if (this.pos.isCountryGermanyAndFiskaly()) {
                this.fiskalyUuid = this.fiskalyUuid || null;
                this.transactionState = this.transactionState || 'inactive'; // Used to know when we need to create the fiskaly transaction
                this.tssInformation = this.tssInformation || this._initTssInformation();
                this.save_to_db();
            }
        }
        _initTssInformation() {
            return {
                'transaction_number': { 'name': 'TSE-Transaktion', 'value': null },
                'time_start': { 'name': 'TSE-Start', 'value': null },
                'time_end': { 'name': 'TSE-Stop', 'value': null },
                'certificate_serial': { 'name': 'TSE-Seriennummer', 'value': null },
                'timestamp_format': { 'name': 'TSE-Zeitformat', 'value': null },
                'signature_value': { 'name': 'TSE-Signatur', 'value': null },
                'signature_algorithm': { 'name': 'TSE-Hashalgorithmus', 'value': null },
                'signature_public_key': { 'name': 'TSE-PublicKey', 'value': null },
                'client_serial_number': { 'name': 'ClientID / KassenID', 'value': null },
                'erstBestellung': { 'name': 'TSE-Erstbestellung', 'value': null }
            };
        }
        isTransactionInactive() {
            return this.transactionState === 'inactive';
        }
        transactionStarted() {
            this.transactionState = 'started';
        }
        isTransactionStarted() {
            return this.transactionState === 'started';
        }
        transactionFinished() {
            this.transactionState = 'finished';
        }
        isTransactionFinished() {
            return this.transactionState === 'finished' || this.tssInformation.time_start.value;
        }
        // @Override
        export_for_printing() {
            const receipt = super.export_for_printing(...arguments);
            if (this.pos.isCountryGermanyAndFiskaly()) {
                if (this.isTransactionFinished()) {
                    receipt['tss'] = {};
                    $.extend(true, receipt['tss'], this.tssInformation);
                } else {
                    receipt['tss_issue'] = true;
                }
            } else if (this.pos.isCountryGermany() && !this.pos.getTssId()) {
                receipt['test_environment'] = true;
            }
            return receipt;
        }
        //@Override
        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            if (this.pos.isCountryGermanyAndFiskaly()) {
                json['fiskaly_uuid'] = this.fiskalyUuid;
                json['transaction_state'] = this.transactionState;
                json['tss_info'] = {};
                for (var key in this.tssInformation) {
                    if (key !== 'erstBestellung') {
                        json['tss_info'][key] = this.tssInformation[key].value;
                    }
                }
            }
            return json;
        }
        //@Override
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            if (this.pos.isCountryGermanyAndFiskaly()) {
                this.fiskalyUuid = json.fiskaly_uuid;
                this.transactionState = json.transaction_state;
                if (json.tss_info) {
                    this.tssInformation = this._initTssInformation();
                    for (var key in json.tss_info) {
                        this.tssInformation[key].value = json.tss_info[key];
                    }
                    if (this.get_orderlines().length > 0) {
                        this.tssInformation.erstBestellung.value = this.get_orderlines()[0].get_product().display_name;
                    }
                }
            }
        }
        //@Override
        add_product(product, options) {
            if (this.pos.isCountryGermanyAndFiskaly()) {
                if (product.taxes_id.length === 0 || !(this.pos.taxes_by_id[product.taxes_id[0]].amount in this.pos.vatRateMapping)) {
                    throw new TaxError(product);
                }
            }
            super.add_product(...arguments);
        }
        _authenticate() {
            const data = {
                'api_key': this.pos.getApiKey(),
                'api_secret': this.pos.getApiSecret()
            }

            return $.ajax({
                url: this.pos.getApiUrl() + '/auth',
                method: 'POST',
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).then((data) => {
                this.pos.setApiToken(data.access_token);
            }).catch((error) => {
                error.source = 'authenticate';
                return Promise.reject(error);
            });
        }
        async createTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate(); //  If there's an error, a promise is created with a rejected value
            }

            const transactionUuid = uuidv4();
            const data = {
                'state': 'ACTIVE',
                'client_id': this.pos.getClientId()
            };

            return $.ajax({
                url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}${this.pos.isUsingApiV2() ? '?tx_revision=1' : ''}`,
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${this.pos.getApiToken()}` },
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).then((data) => {
                this.fiskalyUuid = transactionUuid;
                this.transactionStarted();
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.createTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });
        }
        /*
         *  Return an array of { 'vat_rate': ..., 'amount': ...}
         */
        _createAmountPerVatRateArray() {
            const rateIds = {
                'NORMAL': [],
                'REDUCED_1': [],
                'SPECIAL_RATE_1': [],
                'SPECIAL_RATE_2': [],
                'NULL': [],
            };
            this.get_tax_details().forEach((detail) => {
                rateIds[this.pos.vatRateMapping[detail.tax.amount]].push(detail.tax.id);
            });
            const amountPerVatRate = { 'NORMAL': 0, 'REDUCED_1': 0, 'SPECIAL_RATE_1': 0, 'SPECIAL_RATE_2': 0, 'NULL': 0 };
            for (var rate in rateIds) {
                rateIds[rate].forEach((id) => {
                    amountPerVatRate[rate] += this.get_total_for_taxes(id);
                });
            }
            return Object.keys(amountPerVatRate).filter((rate) => !!amountPerVatRate[rate])
                .map((rate) => ({ 'vat_rate': rate, 'amount': this.pos.format_round_decimals_currency(amountPerVatRate[rate])}));
        }
        /*
         *  Return an array of { 'payment_type': ..., 'amount': ...}
         */
        _createAmountPerPaymentTypeArray() {
            const amountPerPaymentTypeArray = [];
            this.get_paymentlines().forEach((line) => {
                amountPerPaymentTypeArray.push({
                    'payment_type': line.payment_method.name.toLowerCase() === 'cash' ? 'CASH' : 'NON_CASH',
                    'amount' : this.pos.format_round_decimals_currency(line.amount)
                 });
            });
            const change = this.get_change();
            if (!!change) {
                amountPerPaymentTypeArray.push({
                    'payment_type': 'CASH',
                    'amount': this.pos.format_round_decimals_currency(-change)
                });
            }
            return amountPerPaymentTypeArray;
        }
        _updateTimeStart(seconds) {
            this.tssInformation.time_start.value = convertFromEpoch(seconds);
        }
        _updateTssInfo(data) {
            this.tssInformation.transaction_number.value = data.number;
            this._updateTimeStart(data.time_start);
            this.tssInformation.time_end.value = convertFromEpoch(data.time_end);
            // certificate_serial is now called tss_serial_number in the v2 api
            this.tssInformation.certificate_serial.value = data.tss_serial_number ? data.tss_serial_number : data.certificate_serial;
            this.tssInformation.timestamp_format.value = data.log.timestamp_format;
            this.tssInformation.signature_value.value = data.signature.value;
            this.tssInformation.signature_algorithm.value = data.signature.algorithm;
            this.tssInformation.signature_public_key.value = data.signature.public_key;
            this.tssInformation.client_serial_number.value = data.client_serial_number;
            this.tssInformation.erstBestellung.value = this.get_orderlines()[0] ? this.get_orderlines()[0].get_product().display_name : undefined;
            this.transactionFinished();
        }
        async finishShortTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate();
            }

            const amountPerVatRateArray = this._createAmountPerVatRateArray();
            const amountPerPaymentTypeArray = this._createAmountPerPaymentTypeArray();
            const data = {
                'state': 'FINISHED',
                'client_id': this.pos.getClientId(),
                'schema': {
                    'standard_v1': {
                        'receipt': {
                            'receipt_type': 'RECEIPT',
                            'amounts_per_vat_rate': amountPerVatRateArray,
                            'amounts_per_payment_type': amountPerPaymentTypeArray
                        }
                    }
                }
            };
            return $.ajax({
                headers: { 'Authorization': `Bearer ${this.pos.getApiToken()}` },
                url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?${this.pos.isUsingApiV2() ? 'tx_revision=2' : 'last_revision=1'}`,
                method: 'PUT',
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).then((data) => {
                this._updateTssInfo(data);
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.finishShortTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });;
        }
        async cancelTransaction() {
            if (!this.pos.getApiToken()) {
                await this._authenticate();
            }

            const data = {
                'state': 'CANCELLED',
                'client_id': this.pos.getClientId(),
                'schema': {
                    'standard_v1': {
                        'receipt': {
                            'receipt_type': 'CANCELLATION',
                            'amounts_per_vat_rate': []
                       }
                    }
                }
            };

            return $.ajax({
                url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${this.fiskalyUuid}?${this.pos.isUsingApiV2() ? 'tx_revision=2' : 'last_revision=1'}`,
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${this.pos.getApiToken()}` },
                data: JSON.stringify(data),
                contentType: 'application/json',
                timeout: 5000
            }).catch(async (error) => {
                if (error.status === 401) {  // Need to update the token
                    await this._authenticate();
                    return this.cancelTransaction();
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });;
        }
    }
    Registries.Model.extend(Order, L10nDeOrder);
});

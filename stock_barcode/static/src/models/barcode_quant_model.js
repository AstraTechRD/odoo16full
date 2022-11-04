/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import {_t} from "web.core";
import { sprintf } from '@web/core/utils/strings';

export default class BarcodeQuantModel extends BarcodeModel {
    constructor(params) {
        super(...arguments);
        this.lineModel = params.model;
        this.validateMessage = _t("The inventory adjustment has been validated");
        this.validateMethod = 'action_validate';
    }

    /**
     * Validates only the quants of the current inventory page and don't close it.
     *
     * @returns {Promise}
     */
    async apply() {
        await this.save();
        const linesToApply = this.pageLines.filter(line => line.inventory_quantity_set);
        if (linesToApply.length === 0) {
            const message = _t("There is nothing to apply in this page.");
            return this.notification.add(message, { type: 'warning' });
        }
        const action = await this.orm.call('stock.quant', 'action_validate',
            [linesToApply.map(quant => quant.id)]
        );
        const notifyAndGoAhead = res => {
            if (res && res.special) { // Do nothing if come from a discarded wizard.
                return this.trigger('refresh');
            }
            this.notification.add(_t("The inventory adjustment has been validated"), { type: 'success' });
            this.trigger('history-back');
        };
        if (action && action.res_model) {
            const options = { on_close: notifyAndGoAhead };
            return this.trigger('do-action', { action, options });
        }
        notifyAndGoAhead();
    }

    get applyOn() {
        return this.pageLines.filter(line => line.inventory_quantity_set).length;
    }

    get barcodeInfo() {
        // Takes the parent line if the current line is part of a group.
        let line = this._getParentLine(this.selectedLine) || this.selectedLine;
        if (!line && this.lastScanned.packageId) {
            const lines = this._moveEntirePackage() ? this.packageLines : this.pageLines;
            line = lines.find(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }

        if (line) { // Message depends of the selected line's state.
            const { tracking } = line.product_id;
            const trackingNumber = (line.lot_id && line.lot_id.name) || line.lot_name;
            if (this._lineIsNotComplete(line)) {
                if (tracking === 'none') {
                    this.messageType = 'scan_product';
                } else {
                    this.messageType = tracking === 'lot' ? 'scan_lot' : 'scan_serial';
                }
            } else if (tracking !== 'none' && !trackingNumber) {
                // Line's quantity is fulfilled but still waiting a tracking number.
                this.messageType = tracking === 'lot' ? 'scan_lot' : 'scan_serial';
            } else { // Line's quantity is fulfilled.
                this.messageType = this.groups.group_stock_multi_locations && line.location_id.id === this.location.id ?
                    "scan_product_or_src" :
                    "scan_product";
            }
        } else { // Message depends if multilocation is enabled.
            this.messageType = this.groups.group_stock_multi_locations && !this.lastScanned.sourceLocation ?
                'scan_src' :
                'scan_product';
        }

        const barcodeInformations = { class: this.messageType, warning: false, icon: 'barcode' };
        switch (this.messageType) {
            case 'scan_product':
                barcodeInformations.message = this.groups.group_stock_multi_locations ?
                    sprintf(_t("Scan a product in %s or scan another location"), this.location.display_name) :
                    _t("Scan a product");
                break;
            case 'scan_src':
                barcodeInformations.message = _t("Scan a location");
                barcodeInformations.icon = 'sign-out';
                break;
            case 'scan_product_or_src':
                barcodeInformations.message = sprintf(
                    _t("Scan more products in %s or scan another location"),
                    this.location.display_name);
                break;
            case 'scan_product_or_dest':
                barcodeInformations.message = _t("Scan more products, or scan the destination location");
                barcodeInformations.icon = 'sign-in';
                break;
            case 'scan_lot':
                barcodeInformations.message = sprintf(
                    _t("Scan lot numbers for product %s to change their quantity"),
                    line.product_id.display_name
                );
                break;
            case 'scan_serial':
                barcodeInformations.message = sprintf(
                    _t("Scan serial numbers for product %s to change their quantity"),
                    line.product_id.display_name
                );
                break;
        }
        return barcodeInformations;
    }

    get displayByUnitButton () {
        return true;
    }

    get displaySetButton() {
        return true;
    }

    setData(data) {
        this.userId = data.data.user_id;
        super.setData(...arguments);
        const companies = data.data.records['res.company'];
        this.companyIds = companies.map(company => company.id);
        this.lineFormViewId = data.data.line_view_id;
    }

    get displayApplyButton() {
        return true;
    }

    getDisplayIncrementBtn(line) {
        return line.product_id.tracking !== 'serial' && this.selectedLine &&
            line.virtual_id === this.selectedLine.virtual_id;
    }

    getDisplayDecrementBtn(line) {
        return this.getDisplayIncrementBtn(line);
    }

    getQtyDone(line) {
        return line.inventory_quantity;
    }

    getQtyDemand(line) {
        return line.quantity;
    }

    getActionRefresh(newId) {
        const action = super.getActionRefresh(newId);
        action.params.res_id = this.currentState.lines.map(l => l.id);
        if (newId) {
            action.params.res_id.push(newId);
        }
        return action;
    }

    get highlightValidateButton() {
        return this.applyOn > 0 && this.applyOn === this.pageLines.length;
    }

    get incrementButtonsDisplayStyle() {
        return "d-block my-3";
    }

    IsNotSet(line) {
        return !line.inventory_quantity_set;
    }

    lineIsFaulty(line) {
        return line.inventory_quantity_set && line.inventory_quantity !== line.quantity;
    }

    get printButtons() {
        return [{
            name: _t("Print Inventory"),
            class: 'o_print_inventory',
            action: 'stock.action_report_inventory',
        }];
    }

    get recordIds() {
        return this.currentState.lines.map(l => l.id);
    }

    /**
     * Marks the line as set and set its inventory quantity if it was unset, or
     * unset it if the line was already set.
     *
     * @param {Object} line
     */
    setOnHandQuantity(line) {
        if (line.product_id.tracking === 'serial') { // Special case for product tracked by SN.
            const quantity = !(line.lot_name || line.lot_id) && line.quantity || 1;
            if (line.inventory_quantity_set) {
                line.inventory_quantity = line.inventory_quantity ? 0 : quantity;
                line.inventory_quantity_set = line.inventory_quantity != quantity;
            } else {
                line.inventory_quantity = quantity;
                line.inventory_quantity_set = true;
            }
            this._markLineAsDirty(line);
        } else {
            if (line.inventory_quantity_set) {
                line.inventory_quantity = 0;
                line.inventory_quantity_set = false;
                this._markLineAsDirty(line);
            } else {
                const inventory_quantity = line.quantity - line.inventory_quantity;
                this.updateLine(line, { inventory_quantity });
                line.inventory_quantity_set = true;
            }
        }
        this.trigger('update');
    }

    updateLineQty(virtualId, qty = 1) {
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {inventory_quantity: qty});
            this.trigger('update');
        });
    }

    // --------------------------------------------------------------------------
    // Private
    // --------------------------------------------------------------------------

    _getCommands() {
        return Object.assign(super._getCommands(), {
            'O-BTN.apply': this.apply.bind(this),
        });
    }

    _getNewLineDefaultContext() {
        return {
            default_company_id: this.companyIds[0],
            default_location_id: this._defaultLocation().id,
            default_inventory_quantity: 1,
            default_user_id: this.userId,
            inventory_mode: true,
        };
    }

    _createCommandVals(line) {
        const values = {
            dummy_id: line.virtual_id,
            inventory_date: line.inventory_date,
            inventory_quantity: line.inventory_quantity,
            inventory_quantity_set: line.inventory_quantity_set,
            location_id: line.location_id,
            lot_id: line.lot_id,
            lot_name: line.lot_name,
            package_id: line.package_id,
            product_id: line.product_id,
            owner_id: line.owner_id,
            user_id: this.userId,
        };
        for (const [key, value] of Object.entries(values)) {
            values[key] = this._fieldToValue(value);
        }
        return values;
    }

    async _createNewLine(params) {
        // When creating a new line, we need to know if a quant already exists
        // for this line, and in this case, update the new line fields.
        const product = params.fieldsParams.product_id;
        if (product.detailed_type != 'product') {
            const productName = (product.default_code ? `[${product.default_code}] ` : '') + product.display_name;
            const message = sprintf(
                _t("%s can't be inventoried. Only storable products can be inventoried."), productName);
            this.notification.add(message, { type: 'warning' });
            return false;
        }
        const domain = [
            ['location_id', '=', this.location.id],
            ['product_id', '=', product.id],
        ];
        if (product.tracking !== 'none') {
            if (params.fieldsParams.lot_name) { // Search for a quant with the exact same lot.
                domain.push(['lot_id.name', '=', params.fieldsParams.lot_name]);
            } else { // Search for a quant with no lot.
                domain.push(['lot_id', '=', false]);
            }
        }
        if (params.fieldsParams.package_id) {
            domain.push(['package_id', '=', params.fieldsParams.package_id]);
        }
        const quant = await this.orm.searchRead(
            'stock.quant',
            domain,
            ['id', 'inventory_date', 'inventory_quantity', 'inventory_quantity_set', 'quantity', 'user_id'],
            { limit: 1 }
        );
        if (quant.length) {
            Object.assign(params.fieldsParams, quant[0], { inventory_quantity: 1 });
        }
        const newLine = await super._createNewLine(params);
        if (quant.length) {
            // If the quant already exits, we add it into the `initialState` to
            // avoid comparison issue with the `currentState` when the save occurs.
            this.initialState.lines.push(Object.assign({}, newLine, quant[0]));
        }
        return newLine;
    }

    _convertDataToFieldsParams(args) {
        const params = {
            inventory_quantity: args.quantity,
            lot_id: args.lot,
            lot_name: args.lotName,
            owner_id: args.owner,
            package_id: args.package || args.resultPackage,
            product_id: args.product,
            product_uom_id: args.product && args.product.uom_id,
        };
        return params;
    }

    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        return Object.assign(defaultValues, {
            inventory_date: new Date().toISOString().slice(0, 10),
            inventory_quantity: 0,
            inventory_quantity_set: true,
            quantity: (fieldsParams && fieldsParams.quantity) || 0,
            user_id: this.userId,
        });
    }

    _getFieldToWrite() {
        return [
            'inventory_date',
            'inventory_quantity',
            'inventory_quantity_set',
            'user_id',
            'location_id',
            'lot_name',
            'lot_id',
            'package_id',
            'owner_id',
        ];
    }

    _getSaveCommand() {
        const commands = this._getSaveLineCommand();
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.params.model,
                    res_id: false,
                    write_field: false,
                    write_vals: commands,
                },
            };
        }
        return {};
    }

    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        return Object.assign(super._groupSublines(...arguments), {
            inventory_quantity: qtyDone,
            quantity: qtyDemand,
        });
    }

    _lineIsNotComplete(line) {
        return line.inventory_quantity === 0;
    }

    async _processPackage(barcodeData) {
        const { packageType, packageName } = barcodeData;
        let recPackage = barcodeData.package;
        this.lastScanned.packageId = false;
        if (!recPackage && !packageType && !packageName) {
            return; // No Package data to process.
        }
        // Scan a new package and/or a package type -> Create a new package with those parameters.
        const currentLine = this.selectedLine || this.lastScannedLine;
        if (currentLine.package_id && packageType &&
            !recPackage && ! packageName &&
            currentLine.package_id.id !== packageType) {
            // Changes the package type for the scanned one.
            await this.orm.write('stock.quant.package', [currentLine.package_id.id], {
                package_type_id: packageType.id,
            });
            const message = sprintf(
                _t("Package type %s was correctly applied to the package %s"),
                packageType.name, currentLine.package_id.name
            );
            barcodeData.stopped = true;
            return this.notification.add(message, { type: 'success' });
        }
        if (!recPackage) {
            if (currentLine && !currentLine.package_id) {
                const valueList = {};
                if (packageName) {
                    valueList.name = packageName;
                }
                if (packageType) {
                    valueList.package_type_id = packageType.id;
                }
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [valueList]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        if (!recPackage && packageName) {
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id) {
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [{ name: packageName }]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        if (!recPackage || (
            recPackage.location_id && recPackage.location_id != this.location.id
        )) {
            return;
        }
        // TODO: can check if quants already in cache to avoid to make a RPC if
        // there is all in it (or make the RPC only on missing quants).
        const res = await this.orm.call(
            'stock.quant',
            'get_stock_barcode_data_records',
            [recPackage.quant_ids]
        );
        const quants = res.records['stock.quant'];
        if (!quants.length) { // Empty package => Assigns it to the last scanned line.
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id && !currentLine.result_package_id) {
                const fieldsParams = this._convertDataToFieldsParams({
                    resultPackage: recPackage,
                });
                await this.updateLine(currentLine, fieldsParams);
                barcodeData.stopped = true;
                this.selectedLineVirtualId = false;
                this.lastScanned.packageId = recPackage.id;
                this.trigger('update');
            }
            return;
        }
        this.cache.setCache(res.records);

        // Checks if the package is already scanned.
        let alreadyExisting = 0;
        for (const line of this.pageLines) {
            if (line.package_id && line.package_id.id === recPackage.id &&
                this.getQtyDone(line) > 0) {
                alreadyExisting++;
            }
        }
        if (alreadyExisting === quants.length) {
            barcodeData.error = _t("This package is already scanned.");
            return;
        }
        // For each quants, creates or increments a barcode line.
        for (const quant of quants) {
            const product = this.cache.getRecord('product.product', quant.product_id);
            const searchLineParams = Object.assign({}, barcodeData, { product });
            const currentLine = this._findLine(searchLineParams);
            if (currentLine) { // Updates an existing line.
                const fieldsParams = this._convertDataToFieldsParams({
                    quantity: quant.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: recPackage,
                    owner: barcodeData.owner,
                });
                await this.updateLine(currentLine, fieldsParams);
            } else { // Creates a new line.
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    quantity: quant.quantity,
                    lot: quant.lot_id,
                    package: quant.package_id,
                    resultPackage: quant.package_id,
                    owner: quant.owner_id,
                });
                const newLine = await this._createNewLine({ fieldsParams });
                newLine.inventory_quantity = quant.quantity;
            }
        }
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = recPackage.id;
        this.trigger('update');
    }

    _updateLineQty(line, args) {
        if (args.quantity) { // Set stock quantity.
            line.quantity = args.quantity;
        }
        if (args.inventory_quantity) { // Increments inventory quantity.
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const productUOM = this.cache.getRecord('uom.uom', line.product_id.uom_id);
                if (args.uom.category_id !== productUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the product's one (%s)."),
                        args.uom.name, productUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'warning' });
                } else if (args.uom.id !== productUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.inventory_quantity = (args.inventory_quantity / args.uom.factor) * productUOM.factor;
                }
            }
            line.inventory_quantity += args.inventory_quantity;
            line.inventory_quantity_set = true;
            if (line.product_id.tracking === 'serial' && (line.lot_name || line.lot_id)) {
                line.inventory_quantity = Math.max(0, Math.min(1, line.inventory_quantity));
            }
        }
    }

    async _updateLotName(line, lotName) {
        if (line.lot_name === lotName) {
            // No need to update the line's tracking number if it's already set.
            return Promise.resolve();
        }
        line.lot_name = lotName;
        // Checks if a quant exists for this line and updates the line in this case.
        const domain = [
            ['location_id', '=', line.location_id.id],
            ['product_id', '=', line.product_id.id],
            ['lot_id.name', '=', lotName],
            ['owner_id', '=', line.owner_id && line.owner_id.id],
            ['package_id', '=', line.package_id && line.package_id.id],
        ];
        const existingQuant = await this.orm.searchRead(
            'stock.quant',
            domain,
            ['id', 'quantity'],
            { limit: 1, load: false }
        );
        if (existingQuant.length) {
            Object.assign(line, existingQuant[0]);
            if (line.lot_id) {
                line.lot_id = await this.cache.getRecordByBarcode(lotName, 'stock.lot');
            }
        }
    }

    _createLinesState() {
        const today = new Date().toISOString().slice(0, 10);
        const lines = [];
        for (const id of Object.keys(this.cache.dbIdCache['stock.quant']).map(id => Number(id))) {
            const quant = this.cache.getRecord('stock.quant', id);
            if (quant.user_id !== this.userId || quant.inventory_date > today) {
                // Doesn't take quants who must be counted by another user or in the future.
                continue;
            }
            // Checks if this line is already in the quant state to get back
            // its `virtual_id` (and so, avoid to set a new `virtual_id`).
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            quant.virtual_id = quant.dummy_id || previousVirtualId || this._uniqueVirtualId;
            quant.product_id = this.cache.getRecord('product.product', quant.product_id);
            quant.location_id = this.cache.getRecord('stock.location', quant.location_id);
            quant.lot_id = quant.lot_id && this.cache.getRecord('stock.lot', quant.lot_id);
            quant.package_id = quant.package_id && this.cache.getRecord('stock.quant.package', quant.package_id);
            quant.owner_id = quant.owner_id && this.cache.getRecord('res.partner', quant.owner_id);
            lines.push(Object.assign({}, quant));
        }
        return lines;
    }

    _getName() {
        return _t("Inventory Adjustment");
    }

    _getPrintOptions() {
        const options = super._getPrintOptions();
        const quantsToPrint = this.pageLines.filter(quant => quant.inventory_quantity_set);
        if (quantsToPrint.length === 0) {
            return { warning: _t("There is nothing to print in this page.") };
        }
        options.additional_context = { active_ids: quantsToPrint.map(quant => quant.id) };
        return options;
    }
}

/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import {_t, _lt} from "web.core";
import { sprintf } from '@web/core/utils/strings';
import { session } from '@web/session';

export default class BarcodePickingModel extends BarcodeModel {
    constructor(params) {
        super(...arguments);
        this.lineModel = 'stock.move.line';
        this.validateMessage = _t("The transfer has been validated");
        this.validateMethod = 'button_validate';
        this.lastScanned.destLocation = false;
        this.shouldShortenLocationName = true;
    }

    setData(data) {
        super.setData(...arguments);
        this._useReservation = this.initialState.lines.some(line => line.reserved_uom_qty);
        this.config = data.data.config || {}; // Picking type's scan restrictions configuration.
        if (!this.displayDestinationLocation) {
            this.config.restrict_scan_dest_location = 'no';
        }
        this.lineFormViewId = data.data.line_view_id;
        this.formViewId = data.data.form_view_id;
        this.packageKanbanViewId = data.data.package_view_id;
    }

    askBeforeNewLinesCreation(product) {
        return !this.record.immediate_transfer && product &&
            !this.currentState.lines.some(line => line.product_id.id === product.id);
    }

    getDisplayIncrementBtn(line) {
        if (this.config.restrict_scan_product && line.product_id.barcode && !this.getQtyDone(line) && (
            !this.lastScanned.product || this.lastScanned.product.id != line.product_id.id
        )) {
            return false;
        }
        return super.getDisplayIncrementBtn(...arguments);
    }

    getDisplayIncrementBtnForSerial(line) {
        return !this.config.restrict_scan_tracking_number && super.getDisplayIncrementBtnForSerial(...arguments);
    }

    getIncrementQuantity(line) {
        return Math.max(this.getQtyDemand(line) - this.getQtyDone(line), 1);
    }

    getQtyDone(line) {
        return line.qty_done;
    }

    getQtyDemand(line) {
        return line.reserved_uom_qty;
    }

    getEditedLineParams(line) {
        return Object.assign(super.getEditedLineParams(...arguments), { canBeDeleted: !line.reserved_uom_qty });
    }

    getDisplayIncrementPackagingBtn(line) {
        const packagingQty = line.product_packaging_uom_qty;
        return packagingQty &&
            (!this.getQtyDemand(line) || this.getQtyDemand(line) >= this.getQtyDone(line) + packagingQty);
    }

    groupKey(line) {
        return super.groupKey(...arguments) + `_${line.location_dest_id.id}`;
    }

    lineCanBeSelected(line) {
        if (this.selectedLine && this.selectedLine.virtual_id === line.virtual_id) {
            return true; // We consider an already selected line can always be re-selected.
        }
        if (this.config.restrict_scan_source_location && !this.lastScanned.sourceLocation && !line.qty_done) {
            return false; // Can't select a line if source is mandatory and wasn't scanned yet.
        }
        if (line.isPackageLine) {
            // The next conditions concern product, skips them in case of package line.
            return super.lineCanBeSelected(...arguments);
        }
        const product = line.product_id;
        if (this.config.restrict_put_in_pack === 'mandatory' && this.selectedLine &&
            this.selectedLine.qty_done && !this.selectedLine.result_package_id &&
            this.selectedLine.product_id.id != product.id) {
            return false; // Can't select another product if a package must be scanned first.
        }
        if (this.config.restrict_scan_product && product.barcode) {
            // If the product scan is mandatory, a line can't be selected if its product isn't
            // scanned first (as we can't keep track of each line's product scanned state, we
            // consider a product was scanned if the line has a qty. greater than zero).
            if (product.tracking === 'none' || !this.config.restrict_scan_tracking_number) {
                return !this.getQtyDemand(line) || this.getQtyDone(line) || (
                    this.lastScanned.product && this.lastScanned.product.id === line.product_id.id
                );
            } else if (product.tracking != 'none') {
                return line.lot_name || (line.lot_id && line.qty_done);
            }
        }
        return super.lineCanBeSelected(...arguments);
    }

    lineCanBeEdited(line) {
        if (line.product_id.tracking !== 'none' && this.config.restrict_scan_tracking_number &&
            !((line.lot_id && line.qty_done) || line.lot_name)) {
            return false;
        }
        return this.lineCanBeSelected(line);
    }

    async updateLine(line, args) {
        await super.updateLine(...arguments);
        let { location_dest_id, result_package_id } = args;
        if (result_package_id) {
            if (typeof result_package_id === 'number') {
                result_package_id = this.cache.getRecord('stock.quant.package', result_package_id);
                if (result_package_id.package_type_id && typeof result_package_id === 'number') {
                    result_package_id.package_type_id = this.cache.getRecord('stock.package.type', result_package_id.package_type_id);
                }
            }
            line.result_package_id = result_package_id;
        }

        if (location_dest_id) {
            if (typeof location_dest_id === 'number') {
                location_dest_id = this.cache.getRecord('stock.location', args.location_dest_id);
            }
            line.location_dest_id = location_dest_id;
        }
    }

    updateLineQty(virtualId, qty = 1) {
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {qty_done: qty});
            this.trigger('update');
        });
    }

    get barcodeInfo() {
        if (this.isCancelled || this.isDone) {
            return {
                class: this.isDone ? 'picking_already_done' : 'picking_already_cancelled',
                message: this.isDone ?
                    _t("This picking is already done") :
                    _t("This picking is cancelled"),
                warning: true,
            };
        }
        let barcodeInfo = super.barcodeInfo;
        // Takes the parent line if the current line is part of a group.
        const line = this._getParentLine(this.selectedLine) || this.selectedLine;
        // Defines some messages who can appear in multiple cases.
        const infos = {
            scanScrLoc: {
                message: this.considerPackageLines && !this.config.restrict_scan_source_location ?
                    _lt("Scan the source location or a package") :
                    _lt("Scan the source location"),
                class: 'scan_src',
                icon: 'sign-out',
            },
            scanDestLoc: {
                message: _lt("Scan the destination location"),
                class: 'scan_dest',
                icon: 'sign-in',
            },
            scanProductOrDestLoc: {
                message: this.considerPackageLines ?
                    _lt("Scan a product, a package or the destination location.") :
                    _lt("Scan a product or the destination location."),
                class: 'scan_product_or_dest',
            },
            scanPackage: {
                message: this._getScanPackageMessage(line),
                class: "scan_package",
                icon: 'archive',
            },
            scanLot: {
                message: _lt("Scan a lot number"),
                class: "scan_lot",
                icon: "barcode",
            },
            scanSerial: {
                message: _lt("Scan a serial number"),
                class: "scan_serial",
                icon: "barcode",
            },
            pressValidateBtn: {
                message: _lt("Press Validate or scan another product"),
                class: 'scan_validate',
                icon: 'check-square',
            },
        };

        if (!line && this._moveEntirePackage()) { // About package lines.
            const packageLine = this.selectedPackageLine;
            if (packageLine) {
                if (this._lineIsComplete(packageLine)) {
                    if (this.config.restrict_scan_source_location && !this.lastScanned.sourceLocation) {
                        return infos.scanScrLoc;
                    } else if (this.config.restrict_scan_dest_location != 'no' && !this.lastScanned.destLocation) {
                        return this.config.restrict_scan_dest_location == 'mandatory' ?
                            infos.scanDestLoc :
                            infos.scanProductOrDestLoc;
                    } else if (this.pageIsDone) {
                        return infos.pressValidateBtn;
                    } else {
                        barcodeInfo.message = _lt("Scan a product or another package");
                        barcodeInfo.class = 'scan_product_or_package';
                    }
                } else {
                    barcodeInfo.message = sprintf(_t("Scan the package %s"), packageLine.result_package_id.name);
                    barcodeInfo.icon = 'archive';
                }
                return barcodeInfo;
            } else if (this.considerPackageLines && barcodeInfo.class == 'scan_product') {
                barcodeInfo.message = _lt("Scan a product or a package");
                barcodeInfo.class = 'scan_product_or_package';
            }
        }
        if (this.messageType === "scan_product" && !line &&
            this.config.restrict_scan_source_location && this.lastScanned.sourceLocation) {
            barcodeInfo.message = sprintf(
                _lt("Scan a product from %s"),
                this.lastScanned.sourceLocation.name);
        }

        // About source location.
        if (this.displaySourceLocation) {
            if (!this.lastScanned.sourceLocation && !this.pageIsDone) {
                return infos.scanScrLoc;
            } else if (this.lastScanned.sourceLocation && this.lastScanned.destLocation == 'no' &&
                       line && this._lineIsComplete(line)) {
                if (this.config.restrict_put_in_pack === 'mandatory' && !line.result_package_id) {
                    return {
                        message: _lt("Scan a package"),
                        class: 'scan_package',
                        icon: 'archive',
                    };
                }
                return infos.scanScrLoc;
            }
        }

        if (!line) {
            if (this.pageIsDone) { // All is done, says to validate the transfer.
                return infos.pressValidateBtn;
            } else if (this.config.lines_need_to_be_packed) {
                const lines = new Array(...this.pageLines, ...this.packageLines);
                if (lines.every(line => !this._lineIsNotComplete(line)) &&
                    lines.some(line => this._lineNeedsToBePacked(line))) {
                        return infos.scanPackage;
                }
            }
            return barcodeInfo;
        }
        const product = line.product_id;

        // About tracking numbers.
        if (product.tracking !== 'none') {
            const isLot = product.tracking === "lot";
            if (this.getQtyDemand(line) && (line.lot_id || line.lot_name)) { // Reserved.
                if (this.getQtyDone(line) === 0) { // Lot/SN not scanned yet.
                    return isLot ? infos.scanLot : infos.scanSerial;
                } else if (this.getQtyDone(line) < this.getQtyDemand(line)) { // Lot/SN scanned but not enough.
                    barcodeInfo = isLot ? infos.scanLot : infos.scanSerial;
                    barcodeInfo.message = isLot ?
                        _t("Scan more lot numbers") :
                        _t("Scan another serial number");
                    return barcodeInfo;
                }
            } else if (!(line.lot_id || line.lot_name)) { // Not reserved.
                return isLot ? infos.scanLot : infos.scanSerial;
            }
        }

        // About package.
        if (this._lineNeedsToBePacked(line)) {
            if (this._lineIsComplete(line)) {
                return infos.scanPackage;
            }
            if (product.tracking == 'serial') {
                barcodeInfo.message = _t("Scan a serial number or a package");
            } else if (product.tracking == 'lot') {
                barcodeInfo.message = line.qty_done == 0 ?
                    _t("Scan a lot number") :
                    _t("Scan more lot numbers or a package");
                    barcodeInfo.class = "scan_lot";
            } else {
                barcodeInfo.message = _t("Scan more products or a package");
            }
            return barcodeInfo;
        }

        if (this.pageIsDone) {
            Object.assign(barcodeInfo, infos.pressValidateBtn);
        }

        // About destination location.
        const lineWaitingPackage = this.groups.group_tracking_lot && this.config.restrict_put_in_pack != "no" && !line.result_package_id;
        if (this.config.restrict_scan_dest_location != 'no' && line.qty_done) {
            if (this.pageIsDone) {
                if (this.lastScanned.destLocation) {
                    return infos.pressValidateBtn;
                } else {
                    return this.config.restrict_scan_dest_location == 'mandatory' && this._lineIsComplete(line) ?
                        infos.scanDestLoc :
                        infos.scanProductOrDestLoc;
                }
            } else if (this._lineIsComplete(line)) {
                if (lineWaitingPackage) {
                    barcodeInfo.message = this.config.restrict_scan_dest_location == 'mandatory' ?
                        _t("Scan a package or the destination location") :
                        _t("Scan a package, the destination location or another product");
                } else {
                    return this.config.restrict_scan_dest_location == 'mandatory' ?
                        infos.scanDestLoc :
                        infos.scanProductOrDestLoc;
                }
            } else {
                if (product.tracking == 'serial') {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a serial number or a package then the destination location") :
                        _t("Scan a serial number then the destination location");
                } else if (product.tracking == 'lot') {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a lot number or a packages then the destination location") :
                        _t("Scan a lot number then the destination location");
                } else {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a product, a package or the destination location") :
                        _t("Scan a product then the destination location");
                }
            }
        }

        return barcodeInfo;
    }

    get canBeProcessed() {
        return !['cancel', 'done'].includes(this.record.state);
    }

    /**
     * Depending of the config, a transfer can be fully validate even if nothing was scanned (like
     * with an immediate transfer) or if at least one product was scanned.
     * @returns {boolean}
     */
    get canBeValidate() {
        if (this.record.immediate_transfer) {
            return super.canBeValidate; // For immediate transfers, doesn't care about any special condition.
        } else if (!this.config.barcode_validation_full && !this.currentState.lines.some(line => line.qty_done)) {
            return false; // Can't be validate because "full validation" is forbidden and nothing was processed yet.
        }
        return super.canBeValidate;
    }

    get canCreateNewLot() {
        return this.record.use_create_lots;
    }

    get canPutInPack() {
        if (this.config.restrict_scan_product) {
            return this.pageLines.some(line => line.qty_done && !line.result_package_id);
        }
        return true;
    }

    get canSelectLocation() {
        return !(this.config.restrict_scan_source_location || this.config.restrict_scan_dest_location != 'optional');
    }

    /**
     * Must be overridden to make something when the user selects a specific destination location.
     *
     * @param {int} id location's id
     */
    changeDestinationLocation(id, selectedLine) {
        selectedLine = this._getParentLine(selectedLine) || selectedLine;
        if (selectedLine) {
            if (selectedLine.lines) {
                // Grouped lines, applies the location to all sublines with the
                // same current location than the real selected line.
                for (const line of selectedLine.lines) {
                    if (line.location_dest_id.id === selectedLine.location_dest_id.id &&
                        line.location_dest_id.id != id && line.qty_done) {
                        line.location_dest_id = this.cache.getRecord('stock.location', id);
                        this._markLineAsDirty(line);
                    }
                }
            } else if (selectedLine.location_dest_id.id != id) {
                selectedLine.location_dest_id = this.cache.getRecord('stock.location', id);
                this._markLineAsDirty(selectedLine);
            }
            // Clear selection and scan data.
            this.selectedLineVirtualId = false;
            this.location = false;
            this.lastScanned.packageId = false;
            this.lastScanned.product = false;
            this.scannedLinesVirtualId = [];
        }
    }

    get considerPackageLines() {
        return this._moveEntirePackage() && this.packageLines.length;
    }

    get displayCancelButton() {
        return !['done', 'cancel'].includes(this.record.state);
    }

    get displayDestinationLocation() {
        return this.groups.group_stock_multi_locations &&
            ['incoming', 'internal'].includes(this.record.picking_type_code) &&
            this.config.restrict_scan_dest_location != 'no';
    }

    get displayPutInPackButton() {
        return this.groups.group_tracking_lot && this.config.restrict_put_in_pack != 'no';
    }

    get displayResultPackage() {
        return true;
    }

    get displaySourceLocation() {
        return super.displaySourceLocation && this.config.restrict_scan_source_location &&
            ['internal', 'outgoing'].includes(this.record.picking_type_code);
    }

    get displayValidateButton() {
        return true;
    }

    get highlightValidateButton() {
        if (!this.pageLines.length && !this.packageLines.length) {
            return false;
        }
        if (this.config.restrict_scan_dest_location == 'mandatory' &&
            !this.lastScanned.destLocation && this.selectedLine) {
            return false;
        }
        for (let line of this.pageLines) {
            line = this._getParentLine(line) || line;
            if (this._lineIsNotComplete(line)) {
                return false;
            }
        }
        for (const packageLine of this.packageLines) {
            if (this._lineIsNotComplete(packageLine)) {
                return false;
            }
        }
        return Boolean([...this.pageLines, ...this.packageLines].length);
    }

    get isDone() {
        return this.record.state === 'done';
    }

    get isCancelled() {
        return this.record.state === 'cancel';
    }

    lineIsFaulty(line) {
        return this._useReservation && line.qty_done > line.reserved_uom_qty;
    }

    get packageLines() {
        if (!this.record.picking_type_entire_packs) {
            return [];
        }
        const linesWithPackage = this.currentState.lines.filter(line => line.package_id && line.result_package_id);
        // Groups lines by package.
        const groupedLines = {};
        for (const line of linesWithPackage) {
            const packageId = line.package_id.id;
            if (!groupedLines[packageId]) {
                groupedLines[packageId] = [];
            }
            groupedLines[packageId].push(line);
        }
        const packageLines = [];
        for (const key in groupedLines) {
            // Check if the package is reserved.
            const reservedPackage = groupedLines[key].every(line => line.reserved_uom_qty);
            groupedLines[key][0].reservedPackage = reservedPackage;
            const packageLine = Object.assign({}, groupedLines[key][0], {
                lines: groupedLines[key],
                isPackageLine: true,
            });
            packageLines.push(packageLine);
        }
        return this._sortLine(packageLines);
    }

    get pageIsDone() {
        for (const line of this.groupedLines) {
            if (this._lineIsNotComplete(line) || this._lineNeedsToBePacked(line) ||
                (line.product_id.tracking != 'none' && !(line.lot_id || line.lot_name))) {
                return false;
            }
        }
        for (const line of this.packageLines) {
            if (this._lineIsNotComplete(line)) {
                return false;
            }
        }
        return Boolean([...this.groupedLines, ...this.packageLines].length);
    }

    /**
     * Returns only the lines (filters out the package lines if relevant).
     * @returns {Array<Object>}
     */
     get pageLines() {
        let lines = super.pageLines;
        // If we show entire package, we don't return lines with package (they
        // will be treated as "package lines").
        if (this.record.picking_type_entire_packs) {
            lines = lines.filter(line => !(line.package_id && line.result_package_id));
        }
        return this._sortLine(lines);
    }

    get previousScannedLinesByPackage() {
        if (this.lastScanned.packageId) {
            return this.currentState.lines.filter(l => l.result_package_id.id === this.lastScanned.packageId);
        }
        return [];
    }

    get printButtons() {
        const buttons = [
            {
                name: _t("Print Picking Operations"),
                class: 'o_print_picking',
                method: 'do_print_picking',
            }, {
                name: _t("Print Delivery Slip"),
                class: 'o_print_delivery_slip',
                method: 'action_print_delivery_slip',
            }, {
                name: _t("Print Barcodes PDF"),
                class: 'o_print_barcodes_pdf',
                method: 'action_print_barcode_pdf',
            },
        ];
        if (this.groups.group_tracking_lot) {
            buttons.push({
                name: _t("Print Packages"),
                class: 'o_print_packages',
                method: 'action_print_packges',
            });
        }
        const picking_type_code = this.record.picking_type_code;
        const picking_state = this.record.state;
        if ( (picking_type_code === 'incoming') && (picking_state === 'done') ||
             (picking_type_code === 'outgoing') && (picking_state !== 'done') ||
             (picking_type_code === 'internal')
           ) {
            buttons.push({
                name: _t("Scrap"),
                class: 'o_scrap',
                method: 'button_scrap',
            });
        }

        return buttons;
    }

    get selectedPackageLine() {
        return this.lastScanned.packageId && this.packageLines.find(pl => pl.result_package_id.id == this.lastScanned.packageId);
    }

    get useExistingLots() {
        return this.record.use_existing_lots;
    }

    async validate() {
        if (this.config.restrict_scan_dest_location == 'mandatory' &&
            !this.lastScanned.destLocation && this.selectedLine) {
            return this.notification.add(_t("Destination location must be scanned"), { type: 'danger' });
        }
        if (this.config.lines_need_to_be_packed &&
            this.currentState.lines.some(line => this._lineNeedsToBePacked(line))) {
            return this.notification.add(_t("All products need to be packed"), { type: 'danger' });
        }
        return await super.validate();
    }

    async displayProductPage() {
        await this._setUser(); // Set current user as picking's responsible.
        super.displayProductPage();
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    async _assignEmptyPackage(line, resultPackage) {
        const fieldsParams = this._convertDataToFieldsParams({ resultPackage });
        const parentLine = this._getParentLine(line);
        if (parentLine) { // Assigns the result package on all sibling lines.
            for (const subline of parentLine.lines) {
                if (subline.qty_done && !subline.result_package_id) {
                    await this.updateLine(subline, fieldsParams);
                }
            }
        } else {
            await this.updateLine(line, fieldsParams);
        }
    }

    _getNewLineDefaultContext() {
        const picking = this.cache.getRecord(this.params.model, this.params.id);
        return {
            default_company_id: picking.company_id,
            default_location_id: this._defaultLocation().id,
            default_location_dest_id: this._defaultDestLocation().id,
            default_picking_id: this.params.id,
            default_qty_done: 1,
        };
    }

    async _cancel() {
        await this.save();
        await this.orm.call(
            this.params.model,
            'action_cancel',
            [[this.params.id]]
        );
        this._cancelNotification();
        this.trigger('history-back');
    }

    _cancelNotification() {
        this.notification.add(_t("The transfer has been cancelled"));
    }

    _checkBarcode(barcodeData) {
        const check = { title: _lt("Not the expected scan") };
        const { location, lot, product, destLocation, packageType } = barcodeData;
        const resultPackage = barcodeData.package;
        const packageWithQuant = (barcodeData.package && barcodeData.package.quant_ids || []).length;

        if (this.config.restrict_scan_source_location && !barcodeData.location) {
            // Special case where the user can not scan a destination but a source was already scanned.
            // That means what is supposed to be a destination is in this case a source.
            if (this.lastScanned.sourceLocation && barcodeData.destLocation &&
                this.config.restrict_scan_dest_location == 'no') {
                barcodeData.location = barcodeData.destLocation;
                delete barcodeData.destLocation;
            }
            // Special case where the source is mandatory and the app's waiting for but none was
            // scanned, get the previous scanned one if possible.
            if (!this.lastScanned.sourceLocation && this._currentLocation) {
                this.lastScanned.sourceLocation = this._currentLocation;
            }
        }

        if (this.config.restrict_scan_source_location && !this._currentLocation && !this.selectedLine) { // Source Location.
            if (location) {
                this.location = location;
            } else {
                check.title = _t("Mandatory Source Location");
                check.message = sprintf(
                    _t("You are supposed to scan %s or another source location"),
                    this.location.display_name,
                );
            }
        } else if (this.config.restrict_scan_product && // Restriction on product.
            !(product || packageWithQuant || this.selectedLine) && // A product/package was scanned.
            !(this.config.restrict_scan_source_location && location && !this.selectedLine) // Maybe the user scanned the wrong location and trying to scan the right one
        ) {
            check.message = lot ?
                _t("Scan a product before scanning a tracking number") :
                _t("You must scan a product");
        } else if (this.config.restrict_put_in_pack == 'mandatory' && !(resultPackage || packageType) &&
                   this.selectedLine && !this.qty_done && !this.selectedLine.result_package_id &&
                   ((product && product.id != this.selectedLine.product_id.id) || location || destLocation)) { // Package.
            check.message = _t("You must scan a package or put in pack");
        } else if (this.config.restrict_scan_dest_location == 'mandatory' && !this.lastScanned.destLocation) { // Destination Location.
            if (destLocation) {
                this.lastScanned.destLocation = destLocation;
            } else if (product && this.selectedLine && this.selectedLine.product_id.id != product.id) {
                // Cannot scan another product before a destination was scanned.
                check.title = _t("Mandatory Destination Location");
                check.message = sprintf(
                    _t("Please scan destination location for %s before scanning other product"),
                    this.selectedLine.product_id.display_name
                );
            }
        }
        check.error = Boolean(check.message);
        return check;
    }

    async _closeValidate(ev) {
        const record = await this.orm.read(this.params.model, [this.record.id], ["state"])
        if (record[0].state === 'done') {
            // If all is OK, displays a notification and goes back to the previous page.
            this.notification.add(this.validateMessage, { type: 'success' });
            this.trigger('history-back');
        }
    }

    _convertDataToFieldsParams(args) {
        const params = {
            lot_name: args.lotName,
            product_id: args.product,
            qty_done: args.quantity,
        };
        if (args.lot) {
            params.lot_id = args.lot;
        }
        if (args.package) {
            params.package_id = args.package;
        }
        if (args.resultPackage) {
            params.result_package_id = args.resultPackage;
        }
        if (args.owner) {
            params.owner_id = args.owner;
        }
        if (args.destLocation) {
            params.location_dest_id = args.destLocation.id;
        }
        return params;
    }

    _createCommandVals(line) {
        const values = {
            dummy_id: line.virtual_id,
            location_id: line.location_id,
            location_dest_id: line.location_dest_id,
            lot_name: line.lot_name,
            lot_id: line.lot_id,
            package_id: line.package_id,
            picking_id: line.picking_id,
            product_id: line.product_id,
            product_uom_id: line.product_uom_id,
            owner_id: line.owner_id,
            qty_done: line.qty_done,
            result_package_id: line.result_package_id,
            state: 'assigned',
        };
        for (const [key, value] of Object.entries(values)) {
            values[key] = this._fieldToValue(value);
        }
        return values;
    }

    _createLinesState() {
        const lines = [];
        const picking = this.cache.getRecord(this.params.model, this.params.id);
        for (const id of picking.move_line_ids) {
            const smlData = this.cache.getRecord('stock.move.line', id);
            // Checks if this line is already in the picking's state to get back
            // its `virtual_id` (and so, avoid to set a new `virtual_id`).
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            smlData.virtual_id = Number(smlData.dummy_id) || previousVirtualId || this._uniqueVirtualId;
            smlData.product_id = this.cache.getRecord('product.product', smlData.product_id);
            smlData.product_uom_id = this.cache.getRecord('uom.uom', smlData.product_uom_id);
            smlData.location_id = this.cache.getRecord('stock.location', smlData.location_id);
            smlData.location_dest_id = this.cache.getRecord('stock.location', smlData.location_dest_id);
            smlData.lot_id = smlData.lot_id && this.cache.getRecord('stock.lot', smlData.lot_id);
            smlData.owner_id = smlData.owner_id && this.cache.getRecord('res.partner', smlData.owner_id);
            smlData.package_id = smlData.package_id && this.cache.getRecord('stock.quant.package', smlData.package_id);
            smlData.product_packaging_id = smlData.product_packaging_id && this.cache.getRecord('product.packaging', smlData.product_packaging_id);
            const resultPackage = smlData.result_package_id && this.cache.getRecord('stock.quant.package', smlData.result_package_id);
            if (resultPackage) { // Fetch the package type if needed.
                smlData.result_package_id = resultPackage;
                const packageType = resultPackage && resultPackage.package_type_id;
                resultPackage.package_type_id = packageType && this.cache.getRecord('stock.package.type', packageType);
            }
            lines.push(smlData);
        }
        return lines;
    }

    _defaultLocation() {
        return this.cache.getRecord('stock.location', this.record.location_id);
    }

    _defaultDestLocation() {
        return this.cache.getRecord('stock.location', this.record.location_dest_id);
    }

    _getCommands() {
        return Object.assign(super._getCommands(), {
            'O-BTN.pack': this._putInPack.bind(this),
            'O-CMD.cancel': this._cancel.bind(this),
        });
    }

    _getDefaultMessageType() {
        if (this.displaySourceLocation && !this.lastScanned.sourceLocation) {
            return 'scan_src';
        }
        return 'scan_product';
    }

    _getLocationMessage() {
        if (this.groups.group_stock_multi_locations) {
            if (this.record.picking_type_code === 'outgoing') {
                return 'scan_product_or_src';
            } else if (this.config.restrict_scan_dest_location != 'no') {
                return 'scan_product_or_dest';
            }
        }
        return 'scan_product';
    }

    _getModelRecord() {
        const record = this.cache.getRecord(this.params.model, this.params.id);
        if (record.picking_type_id && record.state !== "cancel") {
            record.picking_type_id = this.cache.getRecord('stock.picking.type', record.picking_type_id);
        }
        return record;
    }

    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        return Object.assign(defaultValues, {
            location_dest_id: this._defaultDestLocation(),
            reserved_uom_qty: false,
            qty_done: 0,
            picking_id: this.params.id,
        });
    }

    _getFieldToWrite() {
        return [
            'location_id',
            'location_dest_id',
            'lot_id',
            'lot_name',
            'package_id',
            'owner_id',
            'qty_done',
            'result_package_id',
        ];
    }

    _getSaveCommand() {
        const commands = this._getSaveLineCommand();
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.params.model,
                    res_id: this.params.id,
                    write_field: 'move_line_ids',
                    write_vals: commands,
                },
            };
        }
        return {};
    }

    _getScanPackageMessage() {
        return _t("Scan a package or put in pack");
    }

    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        return Object.assign(super._groupSublines(...arguments), {
            reserved_uom_qty: qtyDemand,
            qty_done: qtyDone,
        });
    }

    _incrementTrackedLine() {
        return !(this.record.use_create_lots || this.record.use_existing_lots);
    }

    _lineIsComplete(line) {
        let isComplete = line.reserved_uom_qty && line.qty_done >= line.reserved_uom_qty;
        if (line.isPackageLine && !line.reserved_uom_qty && line.qty_done) {
            return true; // For package line, considers an unreserved package as a completed line.
        }
        if (isComplete && line.lines) { // Grouped lines/package lines have multiple sublines.
            for (const subline of line.lines) {
                // For tracked product, a line with `qty_done` but no tracking number is considered as not complete.
                if (subline.product_id.tracking != 'none') {
                    if (subline.qty_done && !(subline.lot_id || subline.lot_name)) {
                        return false;
                    }
                } else if (subline.reserved_uom_qty && subline.qty_done < subline.reserved_uom_qty) {
                    return false;
                }
            }
        }
        return isComplete;
    }

    _lineIsNotComplete(line) {
        const isNotComplete = line.reserved_uom_qty && line.qty_done < line.reserved_uom_qty;
        if (!isNotComplete && line.lines) { // Grouped lines/package lines have multiple sublines.
            for (const subline of line.lines) {
                // For tracked product, a line with `qty_done` but no tracking number is considered as not complete.
                if (subline.product_id.tracking != 'none') {
                    if (subline.qty_done && !(subline.lot_id || subline.lot_name)) {
                        return true;
                    }
                } else if (subline.reserved_uom_qty && subline.qty_done < subline.reserved_uom_qty) {
                    return true;
                }
            }
        }
        return isNotComplete;
    }

    _lineNeedsToBePacked(line) {
        return Boolean(
            this.config.lines_need_to_be_packed && line.qty_done && !line.result_package_id);
    }

    _moveEntirePackage() {
        return this.record.picking_type_entire_packs;
    }

    async _processLocation(barcodeData) {
        super._processLocation(...arguments);
        if (barcodeData.destLocation) {
            this._processLocationDestination(barcodeData);
            this.trigger('update');
        }
    }

    _processLocationDestination(barcodeData) {
        const selectedLine = this.selectedLine || this.selectedPackageLine;
        if (this.config.restrict_scan_dest_location == 'no' || !selectedLine) {
            return;
        }
        this.changeDestinationLocation(barcodeData.destLocation.id, selectedLine);
        this.trigger('update');
        barcodeData.stopped = true;
    }

    async _processPackage(barcodeData) {
        const { packageName } = barcodeData;
        const recPackage = barcodeData.package;
        this.lastScanned.packageId = false;
        if (barcodeData.packageType && !recPackage) {
            // Scanned a package type and no existing package: make a put in pack (forced package type).
            barcodeData.stopped = true;
            return await this._processPackageType(barcodeData);
        } else if (packageName && !recPackage) {
            // Scanned a non-existing package: make a put in pack.
            barcodeData.stopped = true;
            return await this._putInPack({ default_name: packageName });
        } else if (!recPackage || (
            recPackage.location_id && recPackage.location_id != this.location.id
        )) {
            return; // No package, package's type or package's name => Nothing to do.
        }
        // If move entire package, checks if the scanned package matches a package line.
        if (this._moveEntirePackage()) {
            for (const packageLine of this.packageLines) {
                if (packageLine.package_id.name !== (packageName || recPackage.name)) {
                    continue;
                }
                barcodeData.stopped = true;
                if (packageLine.qty_done) {
                    this.lastScanned.packageId = packageLine.package_id.id;
                    const message = _t("This package is already scanned.");
                    this.notification.add(message, { type: 'danger' });
                    return this.trigger('update');
                }
                for (const line of packageLine.lines) {
                    await this._updateLineQty(line, { qty_done: line.reserved_uom_qty });
                    this._markLineAsDirty(line);
                }
                return this.trigger('update');
            }
        }
        // Scanned a package: fetches package's quant and creates a line for
        // each of them, except if the package is already scanned.
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
            if (currentLine && !currentLine.result_package_id) {
                await this._assignEmptyPackage(currentLine, recPackage);
                barcodeData.stopped = true;
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
                await this._createNewLine({ fieldsParams });
            }
        }
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = recPackage.id;
        this.trigger('update');
    }

    async _processPackageType(barcodeData) {
        const { packageType } = barcodeData;
        const line = this.selectedLine;
        if (!line || !line.qty_done) {
            barcodeData.stopped = true;
            const message = _t("You can't apply a package type. First, scan product or select a line");
            return this.notification.add(message, { type: 'warning' });
        }
        const resultPackage = line.result_package_id;
        if (!resultPackage) { // No package on the line => Do a put in pack.
            const additionalContext = { default_package_type_id: packageType.id };
            if (barcodeData.packageName) {
                additionalContext.default_name = barcodeData.packageName;
            }
            await this._putInPack(additionalContext);
        } else if (resultPackage.package_type_id.id !== packageType.id) {
            // Changes the package type for the scanned one.
            await this.save();
            await this.orm.write('stock.quant.package', [resultPackage.id], {
                package_type_id: packageType.id,
            });
            const message = sprintf(
                _t("Package type %s was correctly applied to the package %s"),
                packageType.name, resultPackage.name
            );
            this.notification.add(message, { type: 'success' });
            this.trigger('refresh');
        }
    }

    async _putInPack(additionalContext = {}) {
        const context = Object.assign({ barcode_view: true }, additionalContext);
        if (!this.groups.group_tracking_lot) {
            return this.notification.add(
                _t("To use packages, enable 'Packages' in the settings"),
                { type: 'danger'}
            );
        }
        await this.save();
        const result = await this.orm.call(
            this.params.model,
            'action_put_in_pack',
            [[this.params.id]],
            { context }
        );
        if (typeof result === 'object') {
            this.trigger('process-action', result);
        } else {
            this.trigger('refresh');
        }
    }

    /**
     * Set the pickings's responsible if not assigned to active user.
     */
    async _setUser() {
        if (this.record.user_id != session.uid) {
            this.record.user_id = session.uid;
            await this.orm.write(this.params.model, [this.record.id], { user_id: session.uid });
        }
    }

    _setLocationFromBarcode(result, location) {
        if (this.record.picking_type_code === 'outgoing') {
            result.location = location;
        } else if (this.record.picking_type_code === 'incoming') {
            result.destLocation = location;
        } else if (this.previousScannedLines.length || this.previousScannedLinesByPackage.length) {
            if (this.config.restrict_scan_source_location && this.config.restrict_scan_dest_location === 'no') {
                result.location = location;
            } else {
                result.destLocation = location;
            }
        } else {
            result.location = location;
        }
        return result;
    }

    _sortingMethod(l1, l2) {
        const l1IsCompleted = this._lineIsComplete(l1);
        const l2IsCompleted = this._lineIsComplete(l2);
        // Complete lines always on the bottom.
        if (!l1IsCompleted && l2IsCompleted) {
            return -1;
        } else if (l1IsCompleted && !l2IsCompleted) {
            return 1;
        }
        return super._sortingMethod(...arguments);
    }

    _updateLineQty(line, args) {
        if (line.product_id.tracking === 'serial' && line.qty_done > 0 && (this.record.use_create_lots || this.record.use_existing_lots)) {
            return;
        }
        if (args.qty_done) {
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const lineUOM = line.product_uom_id;
                if (args.uom.category_id !== lineUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the line's one (%s)."),
                        args.uom.name, lineUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'danger' });
                } else if (args.uom.id !== lineUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.qty_done = (args.qty_done / args.uom.factor) * lineUOM.factor;
                    args.uom = lineUOM;
                }
            }
            line.qty_done += args.qty_done;
            this._setUser();
        }
    }

    _updateLotName(line, lotName) {
        line.lot_name = lotName;
    }

    async _processGs1Data(data) {
        const result = await super._processGs1Data(...arguments);
        const { rule } = data;
        if (result.location && (rule.type === 'location_dest' || this.messageType === 'scan_product_or_dest')) {
            result.destLocation = result.location;
            result.location = undefined;
        }
        return result;
    }
}

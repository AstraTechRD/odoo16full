/** @odoo-module */

import helper from 'stock_barcode.tourHelper';
import tour from 'web_tour.tour';

tour.register('test_internal_picking_from_scratch', {test: true}, [
    /* Move 2 product1 from WH/Stock/Section 1 to WH/Stock/Section 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=qty_done] input",
        run: 'text 2',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product1',
    },

    {
        trigger: ".ui-menu-item > a:contains('product1')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Section 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line .o_line_destination_location:contains("Section 2")',
        run: function() {
            helper.assertLinesCount(1);
        },
    },

    /* Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 3.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text WH/Stock/Section 3',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 3')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line .o_line_destination_location:contains("Section 3")',
        run: function() {
            helper.assertLinesCount(2);
            const $lineProduct1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted($lineProduct1, false);
            const $lineProduct2 = helper.getLine({barcode: 'product2'});
            helper.assertLineIsHighlighted($lineProduct2, true);
        },
    },

    // Edits the first line to check the transaction doesn't crash and the form view is correctly filled.
    { trigger: '.o_barcode_line:first-child .o_edit' },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormLocationSrc("WH/Stock/Section 1");
            helper.assertFormLocationDest("WH/Stock/Section 2");
            helper.assertFormQuantity("2");
        },
    },

    {
        trigger: '.o_save',
    },

    /* Move 1 product2 from WH/Stock/Section 1 to WH/Stock/Section 2.
     */
    {
        trigger: '.o_add_line',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: ".o_field_widget[name=location_id] input",
        run: 'text Section 1',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 1')",
    },

    {
        trigger: ".o_field_widget[name=location_dest_id] input",
        run: 'text Section 2',
    },

    {
        trigger: ".ui-menu-item > a:contains('Section 2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line.o_selected .o_line_source_location:contains("Section 1")',
        extra_trigger: '.o_barcode_line.o_selected .o_line_destination_location:contains("Section 2")',
        run: function() {
            helper.assertLinesCount(3);
        },
    },
    // Scans the destination (Section 2) for the current line...
    { trigger: '.o_barcode_line:nth-child(2).o_selected', run: 'scan LOC-01-02-00' },
    // ...then scans the source (Section 1) for the next line.
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },
    // On this page, scans product1 which will create a new line and then opens its edit form view.

    {
        trigger: '.o_line_source_location .fw-bold:contains("Section 1")',
        run: 'scan product1'
    },

    { // First call to write.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected .o_edit',
    },

    {
        trigger :'.o_save',
        extra_trigger: '.o_field_widget[name="product_id"]:contains("product1")',
    },
    { // Scans the line's destination before to validate the picking.
        trigger: '.o_barcode_line[data-barcode="product1"].o_selected',
        run: 'scan shelf3',
    },

    {
        extra_trigger: '.o_barcode_line:last-child() .o_line_destination_location:contains("Section 3")',
        trigger: '.o_validate_page',
    },
    { trigger: '.o_notification.border-success' } // Second call to write (change the dest. location).
]);

tour.register('test_internal_picking_reserved_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const [line1, line2, line3] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineLocations(line1, '.../Section 1', '.../Section 2');
            helper.assertLineIsHighlighted($(line2), false);
            helper.assertLineLocations(line2, '.../Section 1', '.../Section 2');
            helper.assertLineIsHighlighted($(line3), false);
            helper.assertLineLocations(line3, '.../Section 3', '.../Section 4');
        }
    },

    /* We first move a product1 from shef3 to shelf2.
     */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan shelf3'
    },

    {
        trigger: '.o_barcode_line .o_line_source_location .fw-bold:contains("Section 3")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            const locationInBold = document.querySelector('.o_line_source_location .fw-bold');
            const lineInSection3 = locationInBold.closest('.o_barcode_line');
            helper.assertLineLocations(lineInSection3, '.../Section 3', '.../Section 4');
        }
    },

    { // Scanning product1 after scanned shelf3 will select the existing line but change its source.
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const lineproduct1 = document.querySelector('.o_barcode_line.o_selected');
            helper.assertLineIsHighlighted($(lineproduct1), true);
            helper.assertLineLocations(lineproduct1, '.../Section 3', '.../Section 2');
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00'
    },

    {
        trigger: '.o_barcode_line:not(.o_selected):first-child .o_line_destination_location:contains(".../Section 2")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            var $lineproduct1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted($lineproduct1, false);
            helper.assertLineLocations($lineproduct1[0], '.../Section 3', '.../Section 2');
        }
    },

    // Scans Section 1 as source location.
    { 'trigger': '.o_barcode_client_action', run: 'scan LOC-01-01-00' },

    {
        trigger: '.o_line_source_location .fw-bold:contains("Section 1")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            const [line1, line2, line3] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineIsHighlighted($(line2), false);
            helper.assertLineIsHighlighted($(line3), false);
        }
    },

    // Process the reservation for product1 (create a new line as the previous one was overrided).
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line:nth-child(4).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_product_or_dest');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const [line1, line2, line3, line4] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineIsHighlighted($(line2), false);
            helper.assertLineIsHighlighted($(line3), false);
            helper.assertLineIsHighlighted($(line4), true);
            helper.assertLineLocations(line4, '.../Section 1', 'WH/Stock');
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 1 to Section 2).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan LOC-01-01-00' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            const [line1, line2, line3, line4] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineIsHighlighted($(line2), true);
            helper.assertLineIsHighlighted($(line3), false);
            helper.assertLineIsHighlighted($(line4), false);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    // Process the reservation for product2 (Section 3 to Section 4).
    { trigger: '.o_scan_message.o_scan_src', run: 'scan shelf3' },
    { trigger: '.o_scan_message.o_scan_product', run: 'scan product2' },
    {
        trigger: '.o_barcode_line:nth-child(3).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_dest');
            helper.assertValidateIsHighlighted(false);
            const [line1, line2, line3, line4] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineIsHighlighted($(line2), false);
            helper.assertLineIsHighlighted($(line3), true);
            helper.assertLineIsHighlighted($(line4), false);
        }
    },
    { trigger: '.o_scan_message.o_scan_dest', run: 'scan shelf4' },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);

            const [line1, line2, line3, line4] = document.querySelectorAll('.o_barcode_line');

            helper.assertLineIsHighlighted($(line1), false);
            helper.assertLineQuantityOnReservedQty(0, '1 / 1');
            helper.assertLineLocations(line1, '.../Section 3', '.../Section 2');

            helper.assertLineIsHighlighted($(line2), false);
            helper.assertLineQuantityOnReservedQty(1, '1 / 1');
            helper.assertLineLocations(line2, '.../Section 1', '.../Section 2');

            helper.assertLineIsHighlighted($(line3), false);
            helper.assertLineQuantityOnReservedQty(2, '1 / 1');
            helper.assertLineLocations(line3, '.../Section 3', '.../Section 4');

            helper.assertLineIsHighlighted($(line4), false);
            helper.assertLineQuantityOnReservedQty(3, '1');
            helper.assertLineLocations(line4, '.../Section 1', '.../Section 2');
        }
    },
]);

tour.register('test_receipt_reserved_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertValidateIsHighlighted(false);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("4")',
        run: function() {
            helper.assertValidateIsHighlighted(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_add_line',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormLocationDest('WH/Stock');
        },
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_receipt_product_not_consecutively', {test: true}, [
    // Scan two products (product1 - product2 - product1)
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line',
        run: 'scan product2',
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line:contains("product2")',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("2")',
        run: 'scan O-BTN.validate',
    },
    {
        trigger: '.o_notification.border-success'
    },
]);

tour.register('test_delivery_lot_with_package', {test: true}, [
    // Unfold grouped lines.
    { trigger: '.o_line_button.o_toggle_sublines' },
    {
        trigger: '.o_barcode_client_action:contains("sn2")',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(2);
            helper.assertScanMessage('scan_serial');
            const $line1 = helper.getSubline(':eq(0)');
            const $line2 = helper.getSubline(':eq(1)');
            helper.assert($line1.find('.o_line_lot_name').text(), 'sn1');
            helper.assert($line1.find('.fa-archive').parent().text().includes("pack_sn_1"), true);
            helper.assert($line2.find('.o_line_lot_name').text(), 'sn2');
            helper.assert($line2.find('.fa-archive').parent().text().includes("pack_sn_1"), true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4'
    },

    {
        trigger: '.o_barcode_client_action:contains("sn4")',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertSublinesCount(4);
            helper.assertScanMessage('scan_validate');
            const [line1, line2, line3, line4] = document.querySelectorAll('.o_sublines .o_barcode_line');
            helper.assert(line1.querySelector('.o_line_lot_name').innerText, "sn1");
            helper.assert(line1.querySelector('.o_line_owner'), null);
            helper.assert(line1.querySelector('.result-package').innerText, "pack_sn_1");
            helper.assert(line1.querySelector('.package').innerText, "pack_sn_1");
            helper.assert(line2.querySelector('.o_line_lot_name').innerText, "sn3");
            helper.assert(line2.querySelector('.o_line_owner'), null);
            helper.assert(line2.querySelector('.package').innerText, "pack_sn_2");
            helper.assert(line3.querySelector('.o_line_lot_name').innerText, "sn4");
            helper.assert(line3.querySelector('.o_line_owner').innerText, "Particulier");
            helper.assert(line3.querySelector('.package').innerText, "pack_sn_2");
            helper.assert(line4.querySelector('.o_line_lot_name').innerText, "sn2");
            helper.assert(line4.querySelector('.o_line_owner'), null);
            helper.assert(line4.querySelector('.result-package').innerText, "pack_sn_1");
            helper.assert(line4.querySelector('.package').innerText, "pack_sn_1");
        }
    },

    // Open the form view to trigger a save
    {
        trigger: '.o_sublines .o_barcode_line:nth-child(3) .fa-pencil',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function() {
            helper.assertFormQuantity("1");
            helper.assert($('div[name="package_id"] input').val(), "pack_sn_2");
            helper.assert($('div[name="result_package_id"] input').val(), "");
            helper.assert($('div[name="owner_id"] input').val(), "Particulier");
            helper.assert($('div[name="lot_id"] input').val(), "sn4");
        },
    },
    {
        trigger: '.o_discard',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_delivery_reserved_1', {test: true}, [
    // test that picking note properly pops up + close it
    { trigger: '.alert:contains("A Test Note")' },
    { trigger: '.close' },
    // Opens and close the line's form view to be sure the note is still hidden.
    { trigger: '.o_add_line' },
    { trigger: '.o_discard' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            const note = document.querySelector('.alert.alert-warning');
            helper.assert(Boolean(note), false, "Note must not be present");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },

    // Display the picking's information to trigger a save.
    { trigger: '.o_show_information' },
    { trigger: '.o_barcode_control .btn.o_discard' },
    { trigger: '.o_barcode_line' },
]);

tour.register('test_delivery_reserved_2', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2'
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),

    {
        trigger: '.o_barcode_line.o_selected:contains("product2")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line:not(.o_line_completed)',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line.o_line_completed',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            var $lines = helper.getLine({barcode: 'product1'});
            for (var i = 0; i < $lines.length; i++) {
                helper.assertLineQty($($lines[i]), "2");
            }

        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line:nth-child(4)',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
        }
    },
]);

tour.register('test_delivery_reserved_3', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan this_is_not_a_barcode_dude' },
    {
        trigger: '.o_barcode_line.o_highlight',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            var $line = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted($line, true);
            helper.assertLineQty($line, "1");
        }
    },
]);

tour.register('test_delivery_using_buttons', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            helper.assert(
                $('.o_line_button[name=incrementButton]').length, 3,
                "3 buttons must be present in the view (one by line)"
            );
            helper.assertLineQuantityOnReservedQty(0, '0 / 2');
            helper.assertLineQuantityOnReservedQty(1, '0 / 3');
            helper.assertLineQuantityOnReservedQty(2, '0 / 4');
            helper.assertButtonIsVisible($('.o_barcode_line').eq(0), 'add_quantity');
            helper.assertButtonIsVisible($('.o_barcode_line').eq(1), 'add_quantity');
            helper.assertButtonIsVisible($('.o_barcode_line').eq(2), 'add_quantity');
        }
    },

    // On the first line, goes on the form view and press digipad +1 button.
    { trigger: '.o_barcode_line:first-child .o_edit' },
    { trigger: '.o_digipad_button.o_increase' },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            const $line = $('.o_barcode_line:first-child');
            helper.assert($line.find('.o_add_quantity').length, 1);
            helper.assertLineQuantityOnReservedQty(0, '1 / 2');
            helper.assertLineIsHighlighted($('.o_barcode_line:first-child'), true);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(2)'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:last-child'), false);
        }
    },
    // Press +1 button again, now its buttons must be hidden.
    {
        trigger: '.o_barcode_line:first-child .o_add_quantity'
    },
    {
        trigger: '.o_barcode_line:first-child.o_selected.o_line_completed',
        run: function() {
            helper.assert($('.o_barcode_line:eq(0) .o_add_quantity').length, 0);
            helper.assertLineQuantityOnReservedQty(0, '2 / 2');
            helper.assert($('.o_barcode_line:eq(1) .o_add_quantity').length, 1);
            helper.assertLineQuantityOnReservedQty(1, '0 / 3');
        }
    },
    // Press the add remaining quantity button.
    { trigger: '.o_barcode_line:nth-child(2) .o_add_quantity' },
    // Product2 is now done, its button must be hidden.
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected.o_line_completed',
        run: function() {
            helper.assertLineButtonsAreVisible(1, false, '[name=incrementButton]');
            helper.assertLineQuantityOnReservedQty(1, '3 / 3');
            helper.assertLineIsHighlighted($('.o_barcode_line:first-child'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(2)'), true);
            helper.assertLineIsHighlighted($('.o_barcode_line:last-child'), false);
        }
    },

    // Last line at beginning (product3) now at top of list
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertButtonIsVisible($('.o_barcode_line').eq(2), 'add_quantity');
            helper.assertLineQuantityOnReservedQty(2, '0 / 4');
        }
    },
    // Scan product3 one time, then checks the quantities.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    {
        trigger: '.o_barcode_line:last-child.o_selected .qty-done:contains("1")',
        run: function() {
            helper.assertButtonIsVisible($('.o_barcode_line').eq(2), 'add_quantity');
            helper.assertLineQuantityOnReservedQty(2, '1 / 4');
            helper.assertLineIsHighlighted($('.o_barcode_line:first-child'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(2)'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(3)'), true); // Can't use 'last-child' because the tip is place at the same DOM level just behind this line...
        }
    },
    // Goes on the form view and press digipad +1 button.
    { trigger: '.o_barcode_line:last-child .o_edit' },
    { trigger: '.o_digipad_button.o_increase' },
    { trigger: '.o_save' },
    {
        trigger: '.o_barcode_lines',
        run: function() {
            helper.assertButtonIsVisible($('.o_barcode_line').eq(0), 'add_quantity');
            helper.assertLineQuantityOnReservedQty(0, '2 / 4');
        }
    },
    // Press the add remaining quantity button, then the button must be hidden.
    { trigger: '.o_barcode_line:first-child .o_add_quantity' },
    {
        trigger: '.o_barcode_line:first-child .qty-done:contains("4")',
        run: function() {
            helper.assertLineButtonsAreVisible(0, false, '[name=incrementButton]');
            helper.assertLineQuantityOnReservedQty(0, '4 / 4');
            helper.assertValidateIsHighlighted(true);
        }
    },

    // Now, scan one more time the product3 to create a new line (its +1 button must be visible).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    // The new line is created at the second position (directly below the previous selected line).
    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function() {
            helper.assertLinesCount(4);
            helper.assertLineIsHighlighted($('.o_barcode_line:first-child'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(2)'), true);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(3)'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:last-child'), false);
            const $line = $('.o_barcode_line:nth-child(2)');
            helper.assertLineQty($line, '1');
            // +1 button must be present on new line.
            helper.assertButtonIsVisible($line, 'add_quantity');
        }
    },
    // Press +1 button of the new line.
    {
        trigger: '.o_barcode_line:nth-child(2) .o_add_quantity'
    },
    {
        trigger: '.o_barcode_line:nth-child(2) .qty-done:contains("2")',
        run: function() {
            helper.assertLineIsHighlighted($('.o_barcode_line:first-child'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(2)'), true);
            helper.assertLineIsHighlighted($('.o_barcode_line:nth-child(3)'), false);
            helper.assertLineIsHighlighted($('.o_barcode_line:last-child'), false);
            const $line = $('.o_barcode_line:nth-child(2)');
            helper.assertLineQty($line, '2');
            // +1 button must still be present.
            helper.assertButtonIsVisible($line, 'add_quantity');
        }
    },

    // Validate the delivery.
    {
        trigger: '.o_validate_page'
    },
    {
        trigger: '.o_notification.border-success',
    },
]);

tour.register('test_receipt_from_scratch_with_lots_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('You are expected to scan one or more products.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1'
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_line_lot_name:contains("lot1")',
        run: 'scan LOC-01-00-00'
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan productserial1'
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan lot2',
    },

    {
        trigger: '.o_line_lot_name:contains("lot2")',
        run: 'scan LOC-01-01-00'
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_from_scratch_with_lots_2', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_line_lot_name:contains(lot1)',
        run: 'scan lot1',
    },

    {
        trigger: '.qty-done:contains(2)',
        run: 'scan lot2',
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_from_scratch_with_lots_3', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_barcode_line',
        run: function() {
            helper.assertLinesCount(1);
            const $line = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted($line, true);
            helper.assertLineQty($line, "1");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1'
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: function() {
            helper.assertLinesCount(2);
            const $line1 = helper.getLine({barcode: 'product1'});
            const $line2 = helper.getLine({barcode: 'productlot1'});
            helper.assertLineIsHighlighted($line1, false);
            helper.assertLineQty($line1, "1");
            helper.assertLineIsHighlighted($line2, true);
            helper.assertLineQty($line2, "0");
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.qty-done:contains(2)',
        run: function() {
            helper.assertLinesCount(2);
            const $line1 = helper.getLine({barcode: 'product1'});
            const $line2 = helper.getLine({barcode: 'productlot1'});
            helper.assertLineIsHighlighted($line1, false);
            helper.assertLineQty($line1, "1");
            helper.assertLineIsHighlighted($line2, true);
            helper.assertLineQty($line2, "2");
        }
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_from_scratch_with_lots_4', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },
    {
        trigger: '.o_add_line',
        extra_trigger: '.qty-done:contains("3")',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_delivery_from_scratch_with_lots_1', {test: true}, [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_add_line',
        extra_trigger: '.o_barcode_line:nth-child(2)',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_delivery_from_scratch_with_common_lots_name', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("2")',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line:contains("product2")',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.qty-done:contains("3")',
        run: 'scan SUPERSN',
    },
    { trigger: '.o_barcode_line:contains("productserial1")' },
    // Open the form view to trigger a save
    { trigger: '.o_barcode_line:first-child .o_edit' },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_receipt_with_sn_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_delivery_from_scratch_with_sn_1', {test: true}, [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },

]);

tour.register('test_delivery_reserved_lots_1', {test: true}, [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_delivery_different_products_with_same_lot_name', {test: true}, [

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_delivery_reserved_with_sn_1', {test: true}, [
    /* scan a product tracked by serial number. Then scan 4 a its serial numbers.
    */
    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn3',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn4',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },
    // Open the form view to trigger a save
    {
        trigger: '.o_add_line',
    },

    {
        trigger: '.o_field_widget[name="product_id"]',
    },
    ...tour.stepUtils.discardBarcodeForm(),
]);

tour.register('test_receipt_reserved_lots_multiloc_1', {test: true}, [
    /* Receipt of a product tracked by lots. Open an existing picking with 4
    * units initial demands. Scan 2 units in lot1 in location WH/Stock. Then scan
    * 2 unit in lot2 in location WH/Stock/Section 2
    */

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_line .qty-done:contains("2")',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("Section 2")',
        run: 'scan productlot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot2',
    },

    {
        trigger: '.o_barcode_line.o_selected:contains("lot2") .qty-done:contains("2")',
        run: 'scan LOC-01-01-00',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_duplicate_serial_number', {test: true}, [
    /* Create a receipt. Try to scan twice the same serial in different
    * locations.
    */
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    // reception
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("sn1")',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("../Section 1")',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },
    {
        trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains("../Section 2")',
        run: 'scan O-BTN.validate'
    },
    {
        trigger: '.o_notification.border-success',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]);

tour.register('test_delivery_duplicate_serial_number', {test: true}, [
    /* Create a delivery. Try to scan twice the same serial in different
    * locations.
    */
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },

    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_line:contains("productserial1")',
        run: 'scan sn1',
    },

    {
        trigger: '.o_barcode_line .o_line_lot_name:contains("sn1")',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan productserial1',
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan sn1',
    },

    {
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('The scanned serial number is already used.');
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn2',
    },
    ...tour.stepUtils.validateBarcodeForm(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]);

tour.register('test_bypass_source_scan', {test: true}, [
    /* Scan directly a serial number, a package or a lot in delivery order.
    * It should implicitely trigger the same action than a source location
    * scan with the state location.
    */
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(3);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        }
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan THEPACK',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage("You are expected to scan one or more products or a package available at the picking location");
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan serial1',
    },

    {
        trigger: '.o_barcode_line[data-barcode="productserial1"] .o_edit',
    },

    {
        trigger: '.o_field_many2one[name=lot_id]',
        extra_trigger: '.o_field_widget[name="qty_done"]',
        position: "bottom",
        run: function (actions) {
            actions.text("", this.$anchor.find("input"));
        },
    },

    {
        trigger: '.o_field_widget[name=qty_done] input',
        run: 'text 0',
    },

    {
        trigger: '.o_save'
    },

    {
        trigger: '.o_barcode_line',
        run: 'scan lot1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot1',
    },

    {
        trigger: '.o_scan_message.o_scan_product_or_src',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan THEPACK',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan productserial1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan serial1',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_picking_type_mandatory_scan_settings_pick_int_1', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Edit button is always enabled if the product has no barcode (it can't be scanned')");
            helper.assert(
                Boolean(lineProductNoBarcode.querySelector('.btn.o_add_quantity')), true,
                "Add quantity button is always displayed if the product has no barcode");
        }
    },
    // Scans the source location, it should display an error.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You must scan a product");
        },
    },
    // Scans product1, its buttons should be displayed/enabled.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function() {
            const lineProduct1 = document.querySelector('.o_barcode_line[data-barcode="product1"]');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), true,
                "product1 was scanned, the add quantity button should be visible");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Uses buttons to complete the lines.
    { trigger: '.o_barcode_line.o_selected .btn.o_add_quantity' },
    { trigger: '.o_barcode_line .btn.o_add_quantity' },
    // Lines are completed, the message should ask to validate the operation and that's what we do.
    {
        trigger: '.btn.o_validate_page.btn-success',
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_settings_pick_int_2', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_quantity').disabled, true,
                "All lines' buttons are disabled until a source location was scanned");
        }
    },
    // Scans a product, it should display an error.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scans the source location, the buttons for the product without barcode should be enabled.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: function () {
            const [ lineProductNoBarcode, lineProduct1 ] = document.querySelectorAll('.o_barcode_line');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, true,
                "Edit button should be disabled until the product was scanned");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), false,
                "No button to automatically add the quantity if the product scan is mandatory");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_edit').disabled, false,
                "Since the source of this line was scanned and it has no barcode, its buttons should be enabled");
            helper.assert(
                lineProductNoBarcode.querySelector('.btn.o_add_quantity').disabled, false,
                "Since the source of this line was scanned and it has no barcode, its buttons should be enabled");
        }
    },
    // Scans another location, it replaces the previous scanned source as no product was scanned yet.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },

    // Scans product1.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: function() {
            const lineProduct1 = document.querySelector('.o_barcode_line[data-barcode="product1"]');
            helper.assert(
                lineProduct1.querySelector('.btn.o_edit').disabled, false,
                "product1 was scanned, the edit button should now be enabled");
            helper.assert(
                Boolean(lineProduct1.querySelector('.btn.o_add_quantity')), true,
                "product1 was scanned, the add quantity button should be visible");
            helper.assertValidateIsHighlighted(false);
            // Since the only product with a barcode was scanned, the validate button is enabled.
            helper.assertValidateEnabled(true);
        }
    },
    // Scans another product: it should raise an error as the destination should be scanned between each product.
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "Please scan destination location for product1 before scanning other product");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Uses button to complete the line, then scan the destination.
    { trigger: '.o_barcode_line.o_selected .btn.o_add_quantity' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-00-00',
    },
    // Scans again product1: should raise an error as it expects the source (should be scanned after each product).
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assert(
                document.querySelector('.o_notification_content').innerText,
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scans the source and updates the remaining product qty with its button (because no barcode).
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },
    {
        trigger: '.o_barcode_line .btn.o_add_quantity',
        extra_trigger: '.o_scan_message.o_scan_product',
    },
    // Tries to validate without scanning the destination: display a warning.
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan O-BTN.validate',
    },
    { trigger: '.o_notification.border-danger .o_notification_close.btn' },

    // Scans the destination location than validate the operation.
    {
        trigger: 'div[name="barcode_messages"] .fa-sign-in', // "Scan dest. loc." message's icon.
        run: 'scan LOC-01-00-00',
    },
    {
        trigger: '.btn.o_validate_page.btn-success',
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_complete_flux_receipt', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
        }
    },
    // Scans product1 two times to complete the lines.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            helper.assertScanMessage('scan_product_or_dest');
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true); // Can't validate until product with barcode was scanned.
        }
    },
    // Process product2 and product with no barcode with the button.
    { trigger: '.o_barcode_line[data-barcode="product2"] .btn.o_add_quantity' },
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
        extra_trigger: '.o_barcode_line[data-barcode="product2"].o_line_completed',
    },
    // Before to scan remaining product, scans a first time the destination.
    {
        trigger: '.o_barcode_line:not([data-barcode]).o_line_completed',
        run: 'scan WH-INPUT'
    },
    // The message should ask to scan a product, so scans product tracked by lots.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productlot1'
    },
    // Scans lot-001 x2, lot-002 x2 and lot-003 x2.
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected.o_line_completed',
        run: function() {
            helper.assertScanMessage('scan_product_or_dest');
        }
    },
    // Scans the product tracked by serial numbers and scans three serials.
    {
        trigger: '.o_scan_message.o_scan_product_or_dest',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-003'
    },
    // It should ask to scan the destination, so scans it.
    {
        trigger: 'div[name="barcode_messages"] .o_scan_product_or_dest',
        run: 'scan WH-INPUT',
    },
    // Now the destination was scanned, it should say the operation can be validate.
    {
        extra_trigger: 'div[name="barcode_messages"] .o_scan_validate',
        trigger: '.o_validate_page.btn-success',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_complete_flux_internal', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(false); // Can't validate until product with barcode was scanned.
        }
    },
    // Scans one product1 to move in Section 1, but scans another product between.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_line.o_selected', run: 'scan product2' }, // Should raise an error.
    {
        trigger: '.o_notification.border-danger',
        run: function() {
            helper.assertErrorMessage(
                "Please scan destination location for product1 before scanning other product");
        },
    },
    { trigger: '.btn.o_notification_close' },

    { // Scans the destination (Section 1).
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-01-00'
    },

    // Scans product1 again and move it to Section 3.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan shelf3'
    },

    // Scans product2 and moves it into Section 2.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product2'
    },
    {
        trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-02-00'
    },

    // Process quantities for the product with no barcode and move it to Section 1.
    {
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
        extra_trigger: '.o_scan_message.o_scan_product',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan LOC-01-01-00'
    },

    // The message should ask to scan a product, so scans product tracked by lots.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productlot1'
    },
    // Scans lot-001 x2, lot-002 x2 and moves them in Section 3.
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-001'
    },
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected',
        run: 'scan lot-001'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected.o_line_completed',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan lot-002'
    },
    {
        trigger: '.o_sublines .o_barcode_line.o_selected.o_line_completed',
        run: 'scan shelf3'
    },

    // Scans lot-003 x2 and moves them in Section 4.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan lot-003'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productlot1"].o_selected',
        run: 'scan shelf4'
    },

    // Scans the product tracked by serial numbers and scans three serials.
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan productserial1'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-001'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-002'
    },
    {
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected',
        run: 'scan sn-003'
    },
    { // Moves it to Section 4.
        trigger: '.o_barcode_line[data-barcode="productserial1"].o_selected.o_line_completed',
        run: 'scan shelf4'
    },
    // It should say the operation can be validate.
    {
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
        trigger: '.o_validate_page.btn-success',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_complete_flux_pick', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(6);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateEnabled(false);
            const lineButtons = document.querySelectorAll('.btn.o_edit,.btn.o_add_quantity');
            helper.assert(lineButtons.length, 8, "Should have 1 edit & 1 add qty. buttons on 4 lines");
            for (const button of lineButtons) {
                helper.assert(button.disabled, true,
                    "All lines' buttons are disabled until a source location was scanned");
            }
        }
    },
    // Scans product1 -> raise an error because it expects the source location.
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan product1'
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage(
                "You are supposed to scan WH/Stock or another source location");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scan another location (Section 2 for the instance).
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-02-00'
    },
    {
        trigger: '.o_line_source_location:contains(".../Section 2") .fw-bold',
        run: function() {
            helper.assertLinesCount(6);
            helper.assertScanMessage('scan_product');
            const lineProduct2 = document.querySelector('.o_barcode_line');
            helper.assert(
                lineProduct2.querySelector('.btn.o_edit').disabled, false,
                "Since the source location was scanned, its buttons should be enabled");
            helper.assert(
                lineProduct2.querySelector('.btn.o_add_quantity').disabled, false,
                "Since the source location was scanned, its buttons should be enabled");
        }
    },
    // Scans product2 then scans another source location (Section 3) => Should raise a warning.
    { trigger: '.o_barcode_client_action', run: 'scan product2' },
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan shelf3' },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("You must scan a package or put in pack");
        },
    },
    { trigger: '.btn.o_notification_close' },

    // Scans a pack then scans again Section 3.
    { trigger: '.o_barcode_line.o_line_completed', run: 'scan cluster-pack-01' },
    { trigger: '.o_barcode_line.o_selected .result-package', run: 'scan shelf3' },
    {
        trigger: '.o_line_source_location:contains(".../Section 3") .fw-bold',
        run: function() {
            helper.assertLinesCount(6);
            helper.assertScanMessage('scan_product');
        }
    },
    // Scans product1 (x2), pack it then scans lot-001 and lot-002.
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    { trigger: '.o_barcode_client_action', run: 'scan product1' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan productlot1'
    },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("You must scan a package or put in pack");
        },
    },
    { trigger: '.btn.o_notification_close' },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01' },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan productlot1'
    },
    // Checks we can't edit a line for a tracked product until the tracking number was scan.
    { trigger: '.o_barcode_line.o_selected .btn.o_toggle_sublines .fa-caret-down' },
    {
        trigger: '.o_barcode_line.o_selected .o_sublines',
        run: function() {
            const [ lot001Line, lot002Line ] = document.querySelectorAll('.o_sublines .o_barcode_line');
            helper.assert(lot001Line.querySelector('.btn.o_add_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-001',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: function() {
            const [ lot001Line, lot002Line ] = document.querySelectorAll('.o_sublines .o_barcode_line');
            helper.assert(lot001Line.querySelector('.btn.o_add_quantity').disabled, false,
                "lot-001 was scanned, its line's buttons should be enable");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true,
                "Lot number not scanned yet, so line's buttons are disabled.");
        }
    },
    {
        trigger: '.o_barcode_line.o_selected:not(.o_line_completed)',
        run: 'scan lot-001',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            const lot001Line = document.querySelector('.o_sublines .o_barcode_line.o_line_completed');
            const lot002Line = document.querySelector('.o_sublines .o_barcode_line:not(.o_line_completed)');
            helper.assert(Boolean(lot001Line.querySelector('.btn.o_add_quantity')), false,
                "The two lot-001 were scanned, the button to add the quantity should be hidden.");
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, true);
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-002',
    },
    {
        trigger: '.o_barcode_line.o_selected .qty-done:contains(1)',
        run: function() {
            const lot002Line = document.querySelector('.o_sublines .o_barcode_line.o_selected:not(.o_line_completed)');
            helper.assert(lot002Line.querySelector('.btn.o_add_quantity').disabled, false,
                "lot-002 was scanned, the button to add quantity should be enabled.");
        }
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot-002',
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: function() {
            const lot002Line = document.querySelector('.o_sublines .o_barcode_line.o_selected.o_line_completed');
            helper.assert(Boolean(lot002Line.querySelector('.btn.o_add_quantity')), false,
                "Demand quantity was scanned, the button shouldn't be visible.");
        }
    },
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-02' },

    // Scans Section 1 (source) and processes the remaining products.
    { trigger: '.o_barcode_line.o_selected.o_line_completed .result-package', run: 'scan LOC-01-01-00' },
    {
        extra_trigger: '.o_line_source_location:contains(".../Section 1") .fw-bold',
        trigger: '.o_barcode_line:not([data-barcode]) .btn.o_add_quantity',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed:not([data-barcode])',
        run: 'scan cluster-pack-01'
    },

    // Scans Section 4 (source).
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed .result-package',
        run: 'scan shelf4'
    },
    // Scans the remaining lot and the serial numbers.
    {
        trigger: '.o_line_source_location:contains(".../Section 4") .fw-bold',
        extra_trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-001',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-003',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan sn-002',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        extra_trigger: '.o_scan_message.o_scan_package',
        run: 'scan cluster-pack-02'
    },
    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan lot-003',
    },
    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan cluster-pack-02'
    },
    // It should say the operation can be validate.
    {
        extra_trigger: 'div[name="barcode_messages"] .fa-check-square', // "Press validate" message icon.
        trigger: '.o_validate_page.btn-success',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_complete_flux_pack', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(5);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateEnabled(true);
            helper.assertValidateIsHighlighted(false);
        }
    },
    // Scans first cluster pack.
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-01'},
    // Scans second cluster pack.
    { trigger: '.o_barcode_client_action', run: 'scan cluster-pack-02'},
    // Tries to validate: it should ask to put in pack.
    { trigger: '.o_validate_page.btn-success' },
    {
        trigger: '.o_notification',
        run: function() {
            helper.assertErrorMessage("All products need to be packed");
        },
    },
    { trigger: '.btn.o_notification_close' },
    // Puts in pack.
    { trigger: '.o_barcode_client_action', run: 'scan O-BTN.pack'},
    // Validates the operation.
    {
        extra_trigger: '.o_scan_message.o_scan_validate',
        trigger: '.o_validate_page.btn-success',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_picking_type_mandatory_scan_complete_flux_delivery', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
        }
    },
    // Scans the pack, then validate.
    {
        trigger: '.o_barcode_line:contains("PACK0000001")',
        run: 'scan PACK0000001'
    },
    // It should say the operation can be validate.
    {
        extra_trigger: '.o_scan_message.o_scan_validate', // "Press validate" message icon.
        trigger: '.o_barcode_line.o_line_completed',
        run: 'scan O-BTN.validate',
    },
    { trigger: '.o_notification.border-success' },
]);

tour.register('test_pack_multiple_scan', {test: true}, [

    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    // Receipt
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan O-BTN.pack',
    },
    ...tour.stepUtils.validateBarcodeForm(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
    // Delivery transfer to check the error message
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0001000',
    },

    {
        trigger: '.o_barcode_line:nth-child(2)',
        run: 'scan PACK0001000',
    },

    {
        trigger: '.o_notification.border-danger'
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertErrorMessage('This package is already scanned.');
            var $line1 = helper.getLine({barcode: 'product1'});
            helper.assertLineIsHighlighted($line1, true);
            var $line2 = helper.getLine({barcode: 'product2'});
            helper.assertLineIsHighlighted($line2, true);
        },
    },
    ...tour.stepUtils.validateBarcodeForm(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]);

tour.register('test_pack_common_content_scan', {test: true}, [
    /* Scan 2 packages PACK1 and PACK2 that contains both product1 and
     * product 2. It also scan a single product1 before scanning both pacakges.
     * the purpose is to check that lines with a same product are not merged
     * together. For product 1, we should have 3 lines. One with PACK 1, one
     * with PACK2 and the last without package.
     */
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },

    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK2',
    },

    {
        trigger: '.o_barcode_client_action:contains("PACK2")',
        run: function () {
            helper.assertLinesCount(5);
        },
    },
    ...tour.stepUtils.validateBarcodeForm(),

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]);

tour.register('test_pack_multiple_location', {test: true}, [

    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },

    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-INTERNAL',
    },

    {
        trigger: '.o_barcode_client_action .o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK0000666',
    },

    {
        trigger: '.o_package_content',
        run: function() {
            const $line = $('.o_barcode_lines .o_barcode_line');
            helper.assertLineQty($line, '1');
        },
    },

    { // Scan a second time the same package => Should raise a warning.
        trigger: '.o_barcode_client_action',
        run: 'scan PACK0000666',
    },
    { // A notification is shown and the package's qty. should be unchanged.
        trigger: '.o_notification.border-danger',
        run: function() {
            const $line = $('.o_barcode_lines .o_barcode_line');
            helper.assertLineQty($line, '1');
        },
    },

    { trigger: '.o_package_content' },
    {
        trigger: '.o_kanban_view:contains("product1")',
        run: function () {
            helper.assertKanbanRecordsCount(2);
        },
    },
    { trigger: '.o_close' },

    {
        trigger: '.o_scan_message.o_scan_dest',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan O-BTN.validate',
    },

    {
        trigger: '.o_notification.border-success'
    },

    {
        trigger: '.o_stock_barcode_main_menu',
        run: function () {
            helper.assertErrorMessage('The transfer has been validated');
        },
    },
]);

tour.register('test_pack_multiple_location_02', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan PACK0002020',
    },

    {
        trigger: '.o_barcode_client_action',
        extra_trigger: '.o_barcode_line.o_selected',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_line .o_line_destination_location:contains("WH/Stock/Section 2")',
        run: 'scan O-BTN.validate',
    },

    {
        trigger: '.o_notification.border-success'
    },
]);

tour.register('test_put_in_pack_from_multiple_pages', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_src');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: function () {
            helper.assertLinesCount(4);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line:nth-child(2).o_line_completed',
        run: 'scan LOC-01-02-00',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.pack',
    },

    {
        trigger: '.o_barcode_line:contains("PACK")',
        run: 'scan O-BTN.validate',
    },

    {
        trigger: '.o_notification.border-success'
    },

]);

tour.register('test_reload_flow', {test: true}, [
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-RECEIPTS'
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1'
    },

    {
        trigger: '.o_edit',
    },

    {
        extra_trigger: '.o_field_widget[name="product_id"]',
        trigger: '.o_field_widget[name=qty_done] input',
        run: 'text 2',
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_add_line',
    },

    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text product2',
    },

    {
        trigger: ".ui-menu-item > a:contains('product2')",
    },

    {
        trigger: '.o_save',
    },

    {
        trigger: '.o_barcode_line:nth-child(2).o_selected',
        run: function () {
            helper.assertScanMessage('scan_product_or_dest');
        },
    },

    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-01-00' },
    // Select first line and scans Section 1 to move it to this location.
    {
        extra_trigger: '.o_barcode_line:nth-child(2) .o_line_destination_location:contains(".../Section 1")',
        trigger: '.o_barcode_line:first-child()',
    },
    {
        trigger: '.o_barcode_line:first-child().o_selected',
        run: 'scan LOC-01-01-00'
    },
    {
        trigger: '.o_barcode_line:nth-child(1) .o_line_destination_location:contains(".../Section 1")',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_highlight_packs', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            var $line = $('.o_barcode_line');
            helper.assertLineIsHighlighted($line, false);

        },
    },

    {
        trigger: '.o_barcode_client_action',
        run: 'scan PACK002',
    },

    {
        trigger: '.o_barcode_client_action:contains("PACK002")',
    },

    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(2);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            var $line = $('.o_barcode_line[data-package="PACK002"]');
            helper.assertLineIsHighlighted($line, true);
        },
    },

]);

tour.register('test_put_in_pack_from_different_location', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },

    {
        trigger: '.o_barcode_line.o_selected.o_line_completed',
        run: 'scan product2',
    },

    {
        trigger: '.o_validate_page.btn-success',
        run: 'scan O-BTN.pack',
    },

    {
        trigger: '.o_barcode_line:contains("PACK")',
        run: function() {
            const $line = helper.getLine({barcode: 'product2'});
            helper.assert($line.find('.fa-archive').length, 1, "Expected a 'fa-archive' icon for assigned pack");
        },
    },
    // Scans dest. location.
    {
        trigger: '.o_scan_message.o_scan_product_or_dest',
        run: 'scan LOC-01-02-00',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_put_in_pack_before_dest', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-01-00',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains(".../Section 1") .fw-bold',
        run: 'scan product1',
    },
    { trigger: '.o_barcode_client_action', run: 'scan LOC-01-02-00' },

    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan shelf3',
    },

    {
        trigger: '.o_barcode_line .o_line_source_location:contains(".../Section 3") .fw-bold',
        run: 'scan product2',
    },

    {
        trigger: '.o_barcode_line .qty-done:contains("1")',
        run: 'scan shelf4',
    },

    {
        trigger: '.o_scan_message.o_scan_validate',
        run: 'scan O-BTN.pack'
    },

    {
        trigger: '.modal-title:contains("Choose destination location")',
    },

    {
        trigger: '.o_field_widget[name="location_dest_id"] input',
        run: 'text Section 2',
    },

    {
        trigger: '.ui-menu-item > a:contains("Section 2")',
        auto: true,
        in_modal: false,
    },

    {
        trigger: '.o_field_widget[name="location_dest_id"]',
        run: function () {
            helper.assert(
                $('.o_field_widget[name="location_dest_id"] input').val(),
                'WH/Stock/Section 2'
            );
        },
    },

    {
        trigger: '.btn-primary',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_put_in_pack_scan_package', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: function() {
            helper.assertLinesCount(3);
        }
    },
    {
        trigger: '.o_scan_message.o_scan_src',
        run: 'scan LOC-01-01-00'
    },

    {
        trigger: '.o_scan_message.o_scan_product',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("1")',
        run: 'scan O-BTN.pack',
    },
    {
        trigger: '.o_barcode_line:contains("product1"):contains("PACK0000001")',
        run: function() {
            const $line1 = $('.o_barcode_line:contains("product1")');
            const product1_package = $line1.find('div[name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
        }
    },

    // Scans product2 then scans the package.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    {
        trigger: '.o_barcode_line.o_highlight:contains("product2")',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line:contains("product2"):contains("PACK0000001")',
        run: function() {
            const $line1 = $('.o_barcode_line:contains("product1")');
            const $line2 = $('.o_barcode_line:contains("product2")');
            const product1_package = $line1.find('div[name="package"]').text().trim();
            const product2_package = $line2.find('div[name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
            helper.assert(product2_package, 'PACK0000001');
        }
    },

    // Scans next location then scans again product1 and PACK0000001.
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOC-01-02-00',
    },
    {
        trigger: '.o_barcode_line .o_line_source_location .fw-bold:contains("Section 2")',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_line[data-barcode="product1"] .qty-done:contains("1")',
        run: 'scan PACK0000001',
    },
    {
        trigger: '.o_barcode_line:contains("product1"):contains("PACK0000001")',
        run: function() {
            const $line1 = $('.o_barcode_line:contains("product1")');
            const product1_package = $line1.find('div[name="package"]').text().trim();
            helper.assert(product1_package, 'PACK0000001');
        }
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_picking_owner_scan_package', {test: true}, [
    {
        trigger: '.o_stock_barcode_main_menu:contains("Barcode Scanning")',
    },
    {
        trigger: '.o_stock_barcode_main_menu',
        run: 'scan WH-DELIVERY',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan P00001',
    },
    {
        trigger: '.o_barcode_client_action:contains("P00001")',
    },
    {
        trigger: '.o_barcode_client_action:contains("Azure Interior")',
    },
    ...tour.stepUtils.validateBarcodeForm(),
]);

tour.register('test_receipt_delete_button', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product1',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product2',
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),
    // ensure receipt's extra product CAN be deleted
    {
        trigger: '.o_barcode_line[data-barcode="product2"] .o_edit',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert($('.o_delete').length, 1);
        },
    },
    {
        trigger: '.o_discard',
    },
    // ensure receipt's original move CANNOT be deleted
    {
        trigger: '.o_barcode_line:nth-child(2) .o_edit',
    },
    {
        trigger: '.o_field_widget[name="product_id"]',
        run: function () {
            helper.assert($('.o_delete').length, 0);
        },
    },
    {
        trigger: '.o_discard',
    },
    // add extra product not in original move + delete it
    {
        trigger: '.o_barcode_client_action',
        run: 'scan product3',
    },
    tour.stepUtils.confirmAddingUnreservedProduct(),
    {
        trigger: '.o_barcode_line[data-barcode="product3"] .o_edit',
    },
    {
        trigger: '.o_delete',
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan O-BTN.validate',
    }, {
        content: "wait to be back on the barcode lines",
        trigger: '.o_add_line',
        auto: true,
        run() {},
    },
]);

tour.register('test_show_entire_package', {test: true}, [
    { trigger: 'button.button_operations' },
    { trigger: '.o_kanban_record:contains(Delivery Orders)' },

    // Opens picking with the package level.
    { trigger: '.o_kanban_record:contains(Delivery with Package Level)' },
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product_or_package');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const $line = $('.o_barcode_line');
            helper.assertLineIsHighlighted($line, false);
            helper.assert(
                $line.find('.o_line_button.o_package_content').length, 1,
                "Line for package level => the button to inspect package content should be visible"
            );
            helper.assert($line.find('.o_barcode_line_details > div:contains(package)').text(), "package001package001");
            helper.assert($line.find('div[name=quantity]').text(), '0/ 1');
        },
    },
    { trigger: '.o_line_button.o_package_content' },
    {
        trigger: '.o_kanban_view .o_kanban_record',
        run: function () {
            helper.assertKanbanRecordsCount(1);
        },
    },
    { trigger: 'button.o_close' },
    // Scans package001 to be sure no moves will be created but the package line will be done.
    { trigger: '.o_barcode_lines', run: 'scan package001' },
    {
        trigger: '.o_barcode_line:contains("1/ 1")',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_validate');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(true);
            helper.assertValidateEnabled(true);
            const $line = $('.o_barcode_line');
            helper.assertLineIsHighlighted($line, false);
            helper.assert(
                $line.find('.o_line_button.o_package_content').length, 1,
                "Line for package level => the button to inspect package content should be visible"
            );
            helper.assert($line.find('.o_barcode_line_details > div:contains(package)').text(), "package001package001");
            helper.assert($line.find('div[name=quantity]').text(), '1/ 1');
        },
    },
    { trigger: 'button.o_exit' },

    // Opens picking with the move.
    { trigger: '.o_kanban_record:contains(Delivery with Stock Move)' },
    {
        trigger: '.o_barcode_client_action',
        run: function () {
            helper.assertLinesCount(1);
            helper.assertScanMessage('scan_product');
            helper.assertValidateVisible(true);
            helper.assertValidateIsHighlighted(false);
            helper.assertValidateEnabled(true);
            const $line = $('.o_barcode_line');
            helper.assertLineIsHighlighted($line, false);
            helper.assert(
                $line.find('.o_line_button.o_package_content').length, 0,
                "Line for move with package => should have no button to inspect package content"
            );
            helper.assert($line.find('.o_barcode_line_details > div:contains(package)').text(), "package002");
            helper.assertLineQuantityOnReservedQty(0, '0 / 2');
        },
    },
]);

tour.register('test_define_the_destination_package', {test: true}, [
    {
        trigger: '.o_line_button.o_add_quantity',
    },
    {
        trigger: '.o_barcode_line .qty-done:contains("1")',
        run: 'scan PACK02',
    },
    {
        extra_trigger: '.o_barcode_line:contains("PACK02")',
        trigger: '.btn.o_validate_page',
    },
    {
        trigger: '.o_notification.border-success',
    },
]);

tour.register('test_avoid_useless_line_creation', {test: true}, [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan LOT01',
    },
    {
        trigger: '.o_barcode_line',
        run: 'scan LOREM',
    },
    {
        trigger: '.o_notification.border-danger',
        run: function () {
            helper.assertErrorMessage('You are expected to scan one or more products.');
        },
    },
    // Open the form view to trigger a save
    { trigger: '.o_barcode_line:first-child .o_edit' },
    ...tour.stepUtils.discardBarcodeForm(),
]);

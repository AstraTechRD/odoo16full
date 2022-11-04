odoo.define('stock_barcode.tourHelper', function (require) {
'use strict';

var tour = require('web_tour.tour');

function fail (errorMessage) {
    tour._consume_tour(tour.running_tour, errorMessage);
}

function getLine (description) {
    var $res;
    $('.o_barcode_lines > .o_barcode_line').each(function () {
        var $line = $(this);
        const barcode = $line[0].dataset.barcode.trim();
        if (description.barcode === barcode) {
            if ($res) {
                $res = $res.add($line);
            } else {
                $res = $line;
            }
        }
    });
    if (! $res) {
        fail('cannot get the line with the barcode ' + description.barcode);
    }
    return $res;
}

function getSubline(selector) {
    const $subline = $('.o_sublines .o_barcode_line' + selector);
    if ($subline.length === 0) {
        fail(`No subline was found for the selector "${selector}"`);
    } else if($subline.length > 1) {
        fail(`Multiple sublines were found for the selector "${selector}"`);
    }
    return $subline;
}

function triggerKeydown(eventKey, shiftkey=false) {
    document.querySelector('.o_barcode_client_action')
        .dispatchEvent(new window.KeyboardEvent('keydown', { bubbles: true, key: eventKey, shiftKey: shiftkey}));
}

function assert (current, expected, info) {
    if (current !== expected) {
        fail(info + ': "' + current + '" instead of "' + expected + '".');
    }
}

/**
 * Checks if a button on the given line is visible.
 *
 * @param {jQuerryElement} $line the line where we test the button visibility.
 * @param {string} buttonName could be 'add_quantity' or 'remove_unit'.
 * @param {boolean} [isVisible=true]
 */
function assertButtonIsVisible($line, buttonName, isVisible=true) {
    const $button = $line.find(`.o_${buttonName}`);
    assert($button.length, isVisible ? 1 : 0,
        isVisible ? `Buttons should be in the DOM` : "Button shouldn't be in the DOM");
}

/**
 * Checks if a button on the given line is invisible.
 *
 * @param {jQuerryElement} $line the line where we test the button visibility.
 * @param {string} buttonName could be 'add_quantity' or 'remove_unit'.
 */
function assertButtonIsNotVisible ($line, buttonName) {
    assertButtonIsVisible($line, buttonName, false);
}

/**
 * Checks if both "Add unit" and "Add reserved remaining quantity" buttons are
 * displayed or not on the given line.
 *
 * @param {integer} lineIndex
 * @param {boolean} isVisible
 */
function assertLineButtonsAreVisible(lineIndex, isVisible, cssSelector='.o_line_button') {
    const $buttonAddQty = $(`.o_barcode_line:eq(${lineIndex}) ${cssSelector}`);
    const message = `Buttons must be ${(isVisible ? 'visible' : 'hidden')}`;
    assert($buttonAddQty.length > 0, isVisible, message);
}

function assertValidateVisible (expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page');
    assert(Boolean(validateButton), expected, 'Validate visible');
}

function assertValidateEnabled (expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    assert(validateButton && !validateButton.hasAttribute('disabled'), expected, 'Validate enabled');
}

function assertValidateIsHighlighted (expected) {
    const validateButton = document.querySelector('.o_validate_page,.o_apply_page') || false;
    const isHighlighted = validateButton && validateButton.classList.contains('btn-success');
    assert(isHighlighted, expected, 'Validate button is highlighted');
}

function assertLinesCount(expected) {
    const current = document.querySelectorAll('.o_barcode_lines > .o_barcode_line').length;
    assert(current, expected, `Should have ${expected} line(s)`);
}

function assertScanMessage (expected) {
    const instruction = document.querySelector(`.o_scan_message`);
    const cssClass = instruction.classList[1];
    assert(cssClass, `o_${expected}`, "Not the right message displayed");
}

function assertSublinesCount(expected) {
    const current = document.querySelectorAll('.o_sublines > .o_barcode_line').length;
    assert(current, expected, `Should have ${expected} subline(s), found ${current}`);
}

function assertLineDestinationIsNotVisible(line) {
    const destinationElement = line.querySelector('.o_line_destination_location');
    if (destinationElement) {
        const product = line.querySelector('.product-label').innerText;
        fail(`The destination for line of the product ${product} should not be visible, "${destinationElement.innerText}" instead`);
    }
}

/**
 * Checks if the given line is going in the given location. Implies the destination is visible.
 * @param {Element} line
 * @param {string} location
 */
function assertLineDestinationLocation(line, location) {
    const destinationElement = line.querySelector('.o_line_destination_location');
    const product = line.querySelector('.product-label').innerText;
    if (!destinationElement) {
        fail(`The destination (${location}) for line of the product ${product} is not visible`);
    }
    assert(
        destinationElement.innerText, location,
        `The destination for line of product ${product} isn't in the right location`);
}

function assertLineIsHighlighted ($line, expected) {
    assert($line.hasClass('o_highlight'), expected, 'line should be highlighted');
}

function assertLineQty($line, expectedQuantity) {
    const lineNode = $line[0];
    if (!lineNode) {
        fail("Can't check the quantity: no line was given.");
    } else if (!lineNode.classList.contains('o_barcode_line')) {
        fail("Can't check the quantity: given element isn't a barcode line.");
    }
    const lineQuantity = lineNode.querySelector('.qty-done,.inventory_quantity').innerText;
    expectedQuantity = String(expectedQuantity);
    assert(lineQuantity, expectedQuantity, `Line's quantity is wrong`);
}

function assertLineLocations(line, source=false, destination=false) {
    if (source) {
        assertLineSourceLocation(line, source);
    } else {
        assertLineSourceIsNotVisible(line);
    }
    if (destination) {
        assertLineDestinationLocation(line, destination);
    } else {
        assertLineDestinationIsNotVisible(line);
    }
}

function assertLineProduct(line, productName) {
    const lineProduct = line.querySelector('.product-label').innerText;
    assert(lineProduct, productName, "No the expected product");
}

/**
 * Checks the done quantity on the reserved quantity is what is expected.
 *
 * @param {integer} lineIndex
 * @param {string} textQty quantity on the line, formatted as "n / N"
 */
function assertLineQuantityOnReservedQty (lineIndex, textQty) {
    const $line = $('.o_barcode_line').eq(lineIndex);
    const qty = $line.find('.qty-done').text();
    const reserved = $line.find('.qty-done').next().text();
    const qtyText = reserved ? qty + ' ' + reserved : qty;
    assert(qtyText, textQty, 'Something wrong with the quantities');
}

function assertLineSourceIsNotVisible(line) {
    const sourceElement = line.querySelector('.o_line_source_location');
    if (sourceElement) {
        const product = line.querySelector('.product-label').innerText;
        fail(`The location for line of the product ${product} should not be visible, "${sourceElement.innerText}" instead`);
    }
}

/**
 * Checks if the given line is in the given location. Implies the location is visible.
 * @param {Element} line
 * @param {string} location
 */
function assertLineSourceLocation(line, location) {
    const sourceElement = line.querySelector('.o_line_source_location');
    const product = line.querySelector('.product-label').innerText;
    if (!sourceElement) {
        fail(`The source (${location}) for line of the product ${product} is not visible`);
    }
    assert(
        sourceElement.innerText, location,
        `The source for line of product ${product} isn't in the right location`);
}

function assertFormLocationSrc(expected) {
    var $location = $('.o_field_widget[name="location_id"] input');
    assert($location.val(), expected, 'Wrong source location');
}

function assertFormLocationDest(expected) {
    var $location = $('.o_field_widget[name="location_dest_id"] input');
    assert($location.val(), expected, 'Wrong destination location');
}

function assertFormQuantity(expected) {
    const quantityField = document.querySelector(
        '.o_field_widget[name="inventory_quantity"] input, .o_field_widget[name="qty_done"] input');
    assert(quantityField.value, expected, 'Wrong quantity');
}

function assertErrorMessage(expected) {
    var $errorMessage = $('.o_notification_content').eq(-1);
    assert($errorMessage[0].innerText, expected, 'wrong or absent error message');
}

function assertKanbanRecordsCount(expected) {
    const kanbanRecords = document.querySelectorAll(
        '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');
    assert(kanbanRecords.length, expected, 'Wrong number of cards');
}

function pressShift() {
    document.querySelector('.o_barcode_client_action').dispatchEvent(
        new window.KeyboardEvent(
            'keydown', { bubbles: true, key: 'Shift' },
        )
    );
}

function releaseShift() {
    document.querySelector('.o_barcode_client_action').dispatchEvent(
        new window.KeyboardEvent(
            'keyup', { bubbles: true, key: 'Shift' },
        )
    );
}

return {
    assert: assert,
    assertButtonIsVisible: assertButtonIsVisible,
    assertButtonIsNotVisible: assertButtonIsNotVisible,
    assertLineButtonsAreVisible: assertLineButtonsAreVisible,
    assertLineDestinationIsNotVisible,
    assertLineDestinationLocation,
    assertLineLocations,
    assertLineSourceIsNotVisible,
    assertLineSourceLocation,
    assertErrorMessage: assertErrorMessage,
    assertFormLocationDest: assertFormLocationDest,
    assertFormLocationSrc: assertFormLocationSrc,
    assertFormQuantity,
    assertLinesCount: assertLinesCount,
    assertLineIsHighlighted: assertLineIsHighlighted,
    assertLineProduct,
    assertLineQty: assertLineQty,
    assertLineQuantityOnReservedQty: assertLineQuantityOnReservedQty,
    assertKanbanRecordsCount,
    assertScanMessage: assertScanMessage,
    assertSublinesCount,
    assertValidateEnabled: assertValidateEnabled,
    assertValidateIsHighlighted: assertValidateIsHighlighted,
    assertValidateVisible: assertValidateVisible,
    fail: fail,
    getLine: getLine,
    getSubline,
    pressShift: pressShift,
    releaseShift: releaseShift,
    triggerKeydown: triggerKeydown,
};

});

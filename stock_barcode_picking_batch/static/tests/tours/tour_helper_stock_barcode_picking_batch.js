odoo.define('stock_barcode_picking_batch.tourHelper', function (require) {
'use strict';

const helper = require('stock_barcode.tourHelper');

/**
 * Finds and returns barcode product lines.
 * When options is provided, can fail if can't get what is asked.
 *
 * @param {Object} options used to filter what lines are wanted
 * @param {string} [options.barcode] to get only lines who match this barcode
 * @param {integer[]} [options.index] a list of integer to get only specified lines
 * @param {integer} [options.from] default to 0
 * @param {integer} [options.to] default to length of the matched lines list
 * @returns {jQueryElement[]}
 */
function getLines (options) {
    let selector = '.o_barcode_line';
    const barcode = options && options.barcode;
    let index = options && options.index;
    const from = options && options.from;
    const to = options && options.to;

    if (barcode) {
        selector += '[data-barcode="'+ barcode +'"';
    }
    let $lines = $(selector);
    if (!$lines && barcode) {
        helper.fail('cannot get the line with the barcode ' + barcode);
    }

    if (index) {
        if (!index.length) {
            index = [index];
        }
        let filters = '';
        for (const i of index) {
            if (filters) {
                filters += ', ';
            }
            filters += `:nth-child(${i})`;
        }
        $lines = $lines.filter(filters);
        if ($lines.length !== index.length) {
            helper.fail(`try to select ${index.length} line(s), found ${$lines.length} line(s) instead`);
        }
    }

    if (from || to) {
        let filters = '';
        const startingIndex = from || 1;
        const endingIndex = to || $lines.length;
        for (let i = startingIndex; i <= endingIndex; i++) {
            if (filters) {
                filters += ', ';
            }
            filters += `:nth-child(${i})`;
        }
        $lines = $lines.filter(filters);
    }

    return $lines;
}

/**
 * Checks the line is linked to the given picking.
 *
 * @param {jQueryElement} $line
 * @param {string} pickingName
 */
function assertLineBelongTo($line, pickingName) {
    const $pickingLabel = $line.find('.o_picking_label');
    helper.assert($pickingLabel[0].innerText, pickingName, 'Wrong picking');
}

/**
 * Checks all lines are linked to the given picking.
 *
 * @param {jQueryElement[]} $lines
 * @param {string} pickingName
 */
function assertLinesBelongTo($lines, pickingName) {
    for (const line of $lines) {
        assertLineBelongTo($(line), pickingName);
    }
}

/**
 * Checks the line is highlighted.
 *
 * @param {jQueryElement} $line
 * @param {boolean} expected define if the line must be highlighted or not
 * @param {Object} options
 * @param {string} [options.class] class to add to the CSS selector
 * @param {string} [options.message] to override the fail's message
 */
function assertLineIsHighlighted ($line, expected, options) {
    let CSSClass = 'o_highlight';
    CSSClass += (options && options.class) || '';
    const message = (options && options.message) || 'line should be highlighted';
    helper.assert($line.hasClass(CSSClass), expected, message);
}

/**
 * Checks the line is highlighted in green.
 *
 * @param {jQueryElement} $line
 * @param {boolean} expected define if the line must be highlighted or not
 */
function assertLineIsHighlightedGreen ($line, expected) {
    helper.assertLineIsHighlighted($line, expected, {
        class: '_green',
        message: 'line should be highlighted in green',
    });
}

/**
 * Checks the line is highlighted in red.
 *
 * @param {jQueryElement} $line
 * @param {boolean} expected define if the line must be highlighted or not
 */
function assertLineIsHighlightedRed ($line, expected) {
    assertLineIsHighlighted($line, expected, {
        class: '_red',
        message: 'line should be highlighted in red',
    });
}

function assertLocationHighlight (expected) {
    var $locationElem = $('.o_barcode_summary_location_src');
    // helper.assert($locationElem.hasClass('o_strong'), expected, 'Location source is not bold');
    helper.assert(
        $locationElem.hasClass('o_barcode_summary_location_highlight'),
        expected,
        'Location source is not highlighted'
    );
}

return Object.assign({}, helper, {
    assertLineBelongTo: assertLineBelongTo,
    assertLinesBelongTo: assertLinesBelongTo,
    assertLineIsHighlighted: assertLineIsHighlighted,
    assertLineIsHighlightedGreen: assertLineIsHighlightedGreen,
    assertLineIsHighlightedRed: assertLineIsHighlightedRed,
    assertLocationHighlight: assertLocationHighlight,
    getLines: getLines,
});

});

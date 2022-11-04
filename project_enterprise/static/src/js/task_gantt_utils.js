/** @odoo-module **/


// -----------------------------------------------------------------------------
// Public
// -----------------------------------------------------------------------------

/**
 * Returns the moment format to use in order to compute the correct slot key for the provided interval.
 * @param scale
 * @return {string}
 */
export function getDateFormatForScale(scale) {
    if (scale.interval === 'hour') {
        return 'DD-MM-YYYY HH';
    } else if (scale.interval === 'day') {
        return 'DD-MM-YYYY';
    } else if (scale.interval === 'month') {
        return 'MM-YYYY';
    }
    throw Error("Invalid SCALE interval !");
}

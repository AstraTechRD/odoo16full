/** @odoo-module **/

import { _t } from 'web.core';
import { sprintf } from '@web/core/utils/strings';
import time from 'web.time';
import { RentingMixin } from '@website_sale_renting/js/renting_mixin';

const oldGetInvalidMessage = RentingMixin._getInvalidMessage;
/**
 * Override to take the stock renting availabilities into account.
 *
 * @override
 */
RentingMixin._getInvalidMessage = function (startDate, endDate, productId) {
    let message = oldGetInvalidMessage.apply(this, arguments);
    if (message || !startDate || !endDate || !this.rentingAvailabilities || !this.preparationTime) {
        return message;
    }
    if (this._isDurationWithHours() && startDate.isBefore(moment().add({hours: this.preparationTime}))) {
        return _t("Your rental product cannot be prepared as fast, please rent later.");
    }
    if (!this.rentingAvailabilities[productId]) {
        return message;
    }
    const format = time.getLangDatetimeFormat();
    for (const interval of this.rentingAvailabilities[productId]) {
        if (interval.start <= endDate) {
            if (interval.end > startDate) {
                if (interval.quantity_available <= 0) {
                    if (!message) {
                        message = _t("The product is not available for all the selected time period:\n");
                    }
                    message += " " + sprintf(
                        _t("- From %s to %s.\n"),
                        interval.start.format(format), interval.end.format(format)
                    );
                }
            }
        } else {
            break;
        }
    }
    return message;
};

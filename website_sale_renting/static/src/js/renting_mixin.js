/** @odoo-module **/

import { _t, _lt } from 'web.core';
import { sprintf } from "@web/core/utils/strings";

export const msecPerUnit = {
    hour: 3600 * 1000,
    day: 3600 * 1000 * 24,
    week: 3600 * 1000 * 24 * 7,
    month: 3600 * 1000 * 24 * 30,
};
export const unitMessages = {
    hour: _lt("(%s hours)."),
    day: _lt("(%s days)."),
    week: _lt("(%s weeks)."),
    month: _lt("(%s months)."),
};

export const RentingMixin = {

    /**
     * Get the message to display if the renting has invalid dates.
     *
     * @param {moment} startDate
     * @param {moment} endDate
     * @private
     */
    _getInvalidMessage(startDate, endDate, productId=false) {
        let message;
        if (!this.rentingUnavailabilityDays || !this.rentingMinimalTime) {
            return message;
        }
        if (startDate && endDate) {
            if (this.rentingUnavailabilityDays[startDate.isoWeekday() % 7]) {
                message = _t("You cannot pick up your rental on that day of the week.");
            } else if (this.rentingUnavailabilityDays[endDate.isoWeekday() % 7]) {
                message = _t("You cannot return your rental on that day of the week.");
            } else {
                const rentingDuration = endDate - startDate;
                if (rentingDuration < 0) {
                    message = _t("The return date should be after the pickup date.");
                } else if (startDate.isBefore(moment(), 'day')) {
                    message = _t("The pickup date cannot be in the past.");
                } else if (['hour', 'day', 'week', 'month'].includes(this.rentingMinimalTime.unit)) {
                    const unit = this.rentingMinimalTime.unit;
                    if (rentingDuration / msecPerUnit[unit] < this.rentingMinimalTime.duration) {
                        message = sprintf(
                            _t("The rental lasts less than the minimal rental duration %s"),
                            sprintf(unitMessages[unit], this.rentingMinimalTime.duration)
                        );
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }
        return message;
    },

    _isDurationWithHours() {
        if (this.rentingMinimalTime &&
            this.rentingMinimalTime.duration > 0 && this.rentingMinimalTime.unit !== "hour") {
            return false;
        }
        const unitInput = this.el.querySelector('input[name=rental_duration_unit]');
        return unitInput && unitInput.value === 'hour';
    },

    /**
     * Get the date from the daterange input or the default
     *
     * @private
     */
    _getDateFromInputOrDefault(picker, fieldName, inputName) {
        let date = picker && picker[fieldName];
        if (!date || !date._isValid) {
            const $defaultDate = this.el.querySelector('input[name="default_' + inputName + '"]');
            date = $defaultDate && $defaultDate.value;
        } else {
            date = date.toISOString();
        }
        return date;
    },

    /**
     * Get the renting pickup and return dates from the website sale renting daterange picker object.
     *
     * @param {$.Element} $product
     */
    _getRentingDates($product) {
        const rentingDates = ($product || this.$el).find('input[name=renting_dates]');
        if (rentingDates.length) {
            const picker = rentingDates.data('daterangepicker');
            return {
                start_date: this._getDateFromInputOrDefault(picker, 'startDate', 'start_date'),
                end_date: this._getDateFromInputOrDefault(picker, 'endDate', 'end_date'),
            };
        }
        return {};
    },

};

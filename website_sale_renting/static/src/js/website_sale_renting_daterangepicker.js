/** @odoo-module **/

import { _t } from 'web.core';
import time from 'web.time';
import publicWidget from 'web.public.widget';
import { msecPerUnit, RentingMixin } from '@website_sale_renting/js/renting_mixin';

publicWidget.registry.WebsiteSaleDaterangePicker = publicWidget.Widget.extend(RentingMixin, {
    selector: '.o_website_sale_daterange_picker',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click [data-toggle=daterange]': '_onClickToggleDaterange',
    }),
    jsLibs: (publicWidget.Widget.prototype.jsLibs || []).concat([
        '/web/static/lib/daterangepicker/daterangepicker.js',
        '/web/static/src/legacy/js/libs/daterangepicker.js',
    ]),

    /**
     * During start, load the renting constraints to validate renting pickup and return dates.
     *
     * @override
     */
    willStart() {
        return this._super.apply(this, arguments).then(() => {
            return this._loadRentingConstraints();
        });
    },

    /**
     * Start the website_sale daterange picker and save in the instance the value of the default
     * renting pickup and return dates, which could be undefined.
     *
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.startDate = this._getDefaultRentingDate('start_date');
        this.endDate = this._getDefaultRentingDate('end_date');
        this.el.querySelectorAll('input.daterange-input').forEach(daterangeInput => {
            this._initSaleRentingDateRangePicker(daterangeInput);
        });
        this._verifyValidPeriod();
    },

    /**
     * Load renting constraints.
     *
     * The constraints are the days where no pickup nor return can be processed and the minimal
     * duration of a renting.
     *
     * @private
     */
    async _loadRentingConstraints() {
        return this._rpc({
            route: "/rental/product/constraints",
        }).then((constraints) => {
            this.rentingUnavailabilityDays = constraints.renting_unavailabity_days;
            this.rentingMinimalTime = constraints.renting_minimal_time;
            $('.oe_website_sale').trigger('renting_constraints_changed', {
                rentingUnavailabilityDays: this.rentingUnavailabilityDays,
                rentingMinimalTime: this.rentingMinimalTime,
            });
        });
    },

    /**
     * Initialize renting date input and attach to it a daterange picker object.
     *
     * A method is attached to the daterange picker in order to handle the changes.
     *
     * @param {HTMLElement} dateInput
     * @private
     */
    _initSaleRentingDateRangePicker(dateInput) {
        const $dateInput = this.$(dateInput);
        $dateInput.daterangepicker({
            // dates
            minDate: moment.min(moment(), this.startDate),
            maxDate: moment.max(moment().add(3, 'y'), this.endDate),
            startDate: this.startDate,
            endDate: this.endDate,
            isInvalidDate: this._isInvalidDate.bind(this),
            isCustomDate: this._isCustomDate.bind(this),
            // display
            locale: {
                direction: _t.database.parameters.direction,
                format: this._isDurationWithHours() ?
                    time.getLangDatetimeFormat().replace('YYYY', 'YY').replace(':ss', '') : time.getLangDateFormat(),
                applyLabel: _t('Apply'),
                cancelLabel: _t('Cancel'),
                weekLabel: 'W',
                customRangeLabel: _t('Custom Range'),
                daysOfWeek: moment.weekdaysMin(),
                monthNames: moment.monthsShort(),
                firstDay: moment.localeData().firstDayOfWeek()
            },
            timePicker: this._isDurationWithHours(),
            timePicker24Hour: true,
        }, (start, end, _label) => {
            this.startDate = start;
            this.endDate = this._isDurationWithHours() ? end : end.startOf('day');
            if (this._verifyValidPeriod()) {
                this.$('input[name=renting_dates]').change();
            }
        });
        $dateInput.data('daterangepicker').container.addClass('o_website_sale_renting');
    },

    // ------------------------------------------
    // Handlers
    // ------------------------------------------
    /**
     * Handle the click on daterangepicker input with a calendar icon to open the daterange picker
     * object.
     *
     * @param {Event} event
     */
    _onClickToggleDaterange(event) {
        if (event.currentTarget.dataset['target']) {
            this.$(event.currentTarget.dataset['target'] + " .daterange-input").click();
        }
    },

    // ------------------------------------------
    // Utils
    // ------------------------------------------
    /**
     * Get the default renting date from the hidden input filled server-side.
     *
     * @param {String} inputName - The name of the input tag that contains pickup or return date
     * @private
     */
    _getDefaultRentingDate(inputName) {
        let defaultDate = this._getSearchDefaultRentingDate(inputName);
        if (defaultDate) {
            return moment(defaultDate);
        }
        // that means that the date is not in the url
        const defaultDateEl = this.el.querySelector(`input[name="default_${inputName}"]`);
        if (defaultDateEl) {
            return moment(defaultDateEl.value);
        }
        if (this.startDate) {
            // that means that the start date is already set
            const rentingDurationMs = this.rentingMinimalTime.duration * msecPerUnit[this.rentingMinimalTime.unit];
            const defaultRentingDurationMs = msecPerUnit['day']; // default duration is 1 day
            let endDate = this.startDate.clone().add(Math.max(rentingDurationMs, defaultRentingDurationMs), 'ms');
            return this._getFirstAvailableDate(endDate);
        }
        // that means that the date is not in the url and not in the hidden input
        // get the first available date based on this.rentingUnavailabilityDays
        let date = moment().add(1, 'd');
        return moment(this._getFirstAvailableDate(date));
    },

    /**
     * Get the default renting date for the given input from the search params.
     *
     * @param {String} inputName - The name of the input tag that contains pickup or return date
     * @private
     */
    _getSearchDefaultRentingDate(inputName) {
        return new URLSearchParams(window.location.search).get(inputName);
    },

    /**
     * Check if the date is invalid.
     *
     * This function is used in the daterange picker objects and meant to be easily overriden.
     *
     * @param {moment} date
     * @private
     */
    _isInvalidDate(date) {
        return this.rentingUnavailabilityDays[date.isoWeekday()];
    },

    /**
     * Set Custom CSS to a given daterangepicker cell
     *
     * This function is used in the daterange picker objects and meant to be easily overriden.
     *
     * @param {moment} date
     * @private
     */
    _isCustomDate(date) {
        return [];
    },

    /**
     * Verify that the dates given in the daterange picker are valid and display a message if not.
     *
     * @private
     */
    _verifyValidPeriod() {
        const message = this._getInvalidMessage(this.startDate, this.endDate, this._getProductId());
        if (message) {
            this.el.parentElement.querySelector('span[name=renting_warning_message]').innerText = message;
            this.el.parentElement.querySelector('.o_renting_warning').classList.remove('d-none');
            // only disable when there is a message. Hence, it doesn't override other disabling.
            $('.oe_website_sale').trigger('toggle_disable', [this._getParentElement(), !message]);
        } else {
            this.el.parentElement.querySelector('.o_renting_warning').classList.add('d-none');
        }
        this.el.dispatchEvent(new CustomEvent('toggle_search_btn', { bubbles: true, detail: message }));
        return !message;
    },

    _getProductId() {},

    _getParentElement() {
        return this.el.closest('form');
    },
    /**
     * Get the first available date based on this.rentingUnavailabilityDays.
     * @private
     */
    _getFirstAvailableDate(date) {
        let counter = 0;
        while (this._isInvalidDate(date) && counter < 1000) {
            date = date.add(1, 'd');
            counter++;
        }
        return date;
    }
});

export default publicWidget.registry.WebsiteSaleDaterangePicker;

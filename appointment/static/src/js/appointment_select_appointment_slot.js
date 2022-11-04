odoo.define('appointment.select_appointment_slot', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
var qweb = core.qweb;

publicWidget.registry.appointmentSlotSelect = publicWidget.Widget.extend({
    selector: '.o_appointment',
    events: {
        'change select[name="timezone"]': '_onRefresh',
        'change select[id="selectStaffUser"]': '_onRefresh',
        'click .o_js_calendar_navigate': '_onCalendarNavigate',
        'click .o_slot_button': '_onClickDaySlot',
    },

    /**
     * @override
     */
    start: function () {
        return this._super(...arguments).then(async () => {
            this.initSlots();
            this._removeLoadingSpinner();
            this.$first.click();
        });
    },

    /**
     * Initializes variables and design
     * - $slotsList: the block containing the availabilities
     * - $first: the first day containing a slot
     */
    initSlots: async function () {
        this.$slotsList = this.$('#slotsList');
        this.$first = this.$('.o_slot_button').first();
        await this._updateSlotAvailability();
    },

    /**
     * Finds the first day with an available slot, replaces the currently shown month and
     * click on the first date where a slot is available.
     */
    selectFirstAvailableMonth: function () {
        const $firstMonth = this.$first.closest('.o_appointment_month');
        const $currentMonth = this.$('.o_appointment_month:not(.d-none)');
        $currentMonth.addClass('d-none');
        $currentMonth.find('table').removeClass('d-none');
        $currentMonth.find('.o_appointment_no_slot_month_helper').remove();
        $firstMonth.removeClass('d-none');
        this.$slotsList.empty();
        this.$first.click();
    },

    /**
     * Replaces the content of the calendar month with the no month helper.
     * Renders and appends its template to the element given as argument.
     * - $month: the month div to which we append the helper.
     */
     _renderNoAvailabilityForMonth: function ($month) {
        const firstAvailabilityDate = this.$first.find('.o_day_wrapper').attr('id');
        const staffUserName = this.$("#slots_form select[name='staff_user_id'] :selected").text();
        $month.find('table').addClass('d-none');
        $month.append(qweb.render('Appointment.appointment_info_no_slot_month', {
            firstAvailabilityDate: moment(firstAvailabilityDate).format('dddd D MMMM YYYY'),
            staffUserName: staffUserName,
        }));
        $month.find('#next_available_slot').on('click', () => this.selectFirstAvailableMonth());
    },

    /**
     * Checks whether any slot is available in the calendar.
     * If there isn't, adds an explicative message in the slot list, and hides the appointment details,
     * and make design width adjustment to have the helper message centered to the whole width.
     * If the appointment is missconfigured (missing user or missing availabilities),
     * display an explicative message. The calendar is then not displayed.
     *
     */
     _updateSlotAvailability: function () {
        if (!this.$first.length) { // No slot available
            this.$('#slots_availabilities').empty();
            this.$('.o_appointment_details_column, .o_appointment_timezone_selection').addClass('d-none');
            this.$('.o_appointment_info_main').removeClass('col-lg-8').addClass('col-12');
            const staffUserName = this.$("#slots_form select[name='staff_user_id'] :selected").text();
            const hideSelectDropdown = !!this.$("input[name='hide_select_dropdown']").val();
            this.$('.o_appointment_no_slot_overall_helper').empty().append(qweb.render('Appointment.appointment_info_no_slot', {
                appointmentsCount: this.$slotsList.data('appointmentsCount'),
                staffUserName: hideSelectDropdown ? staffUserName : false,
            }));
        } else {
            this.$('.o_appointment_details_column, .o_appointment_timezone_selection').removeClass('d-none');
            this.$('.o_appointment_info_main').removeClass('col-12').addClass('col-lg-8');
        }
        if (this.$('.o_appointment_missing_configuration').hasClass('d-none')) {
            this.$('.o_appointment_missing_configuration').removeClass('d-none');
        }
    },

    /**
     * Navigate between the months available in the calendar displayed
     */
    _onCalendarNavigate: function (ev) {
        const parent = this.$('.o_appointment_month:not(.d-none)');
        let monthID = parseInt(parent.attr('id').split('-')[1]);
        monthID += ((this.$(ev.currentTarget).attr('id') === 'nextCal') ? 1 : -1);
        parent.find('table').removeClass('d-none');
        parent.find('.o_appointment_no_slot_month_helper').remove();
        parent.addClass('d-none');
        const $month = $(`div#month-${monthID}`).removeClass('d-none');
        this.$('.o_slot_selected').removeClass('o_slot_selected');
        this.$slotsList.empty();

        if (!!this.$first.length) {
            // If there is at least one slot available, check if it is in the current month.
            if (!$month.find('.o_day').length) {
                this._renderNoAvailabilityForMonth($month);
            }
        }
    },

    /**
     * Display the list of slots available for the date selected
     */
    _onClickDaySlot: function (ev) {
        this.$('.o_slot_selected').removeClass('o_slot_selected');
        this.$(ev.currentTarget).addClass('o_slot_selected');

        const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
        const slotDate = this.$(ev.currentTarget).attr('id');
        const slots = JSON.parse(this.$(ev.currentTarget)[0].dataset['availableSlots']);
        let commonUrlParams = new URLSearchParams(window.location.search);
        // If for instance the chosen slot is already taken, then an error is thrown and the
        // user is brought back to the calendar view. In order to keep the selected user, the
        // url will contain the previously selected staff_user_id (-> preselected in the dropdown
        // if there is one). If one changes the staff_user in the dropdown, we do not want the
        // previous one to interfere, hence we delete it. The one linked to the slot is used.
        // The same is true for duration and date_time used in form rendering.
        commonUrlParams.delete('staff_user_id');
        commonUrlParams.delete('duration');
        commonUrlParams.delete('date_time');

        this.$slotsList.empty().append(qweb.render('appointment.slots_list', {
            commonUrlParams: commonUrlParams,
            slotDate: moment(slotDate).format("dddd D MMMM YYYY"),
            slots: slots,
            url: `/appointment/${appointmentTypeID}/info`,
        }));
    },

    /**
     * Refresh the slots info when the user modifies the timezone or the selected user.
     */
    _onRefresh: function (ev) {
        if (this.$("#slots_availabilities")[0]) {
            const self = this;
            const appointmentTypeID = this.$("input[name='appointment_type_id']").val();
            const filterAppointmentTypeIds = this.$("input[name='filter_appointment_type_ids']").val();
            const filterUserIds = this.$("input[name='filter_staff_user_ids']").val();
            const inviteToken = this.$("input[name='invite_token']").val();
            const previousMonthName = this.$('.o_appointment_month:not(.d-none) .o_appointment_month_name').text();
            const staffUserID = this.$("#slots_form select[name='staff_user_id']").val();
            const timezone = this.$("select[name='timezone']").val();
            this.$('.o_appointment_no_slot_overall_helper').empty();
            this.$slotsList.empty();
            this._rpc({
                route: `/appointment/${appointmentTypeID}/update_available_slots`,
                params: {
                    invite_token: inviteToken,
                    filter_appointment_type_ids: filterAppointmentTypeIds,
                    filter_staff_user_ids: filterUserIds,
                    month_before_update: previousMonthName,
                    staff_user_id: staffUserID,
                    timezone: timezone,
                },
            }).then(function (updatedAppointmentCalendarHtml) {
                if (updatedAppointmentCalendarHtml) {
                    self.$("#slots_availabilities").replaceWith(updatedAppointmentCalendarHtml);
                    self.initSlots();
                    // If possible, we keep the current month, and display the helper if it has no availability.
                    const $displayedMonth = self.$('.o_appointment_month:not(.d-none)');
                    if (!!self.$first.length && !$displayedMonth.find('.o_day').length) {
                        self._renderNoAvailabilityForMonth($displayedMonth);
                    }
                    self._removeLoadingSpinner();
                }
            });
        }
    },

    /**
     * Remove the loading spinner when no longer useful
     */
    _removeLoadingSpinner: function () {
        this.$('.o_appointment_slots_loading').remove();
        this.$('#slots_availabilities').removeClass('d-none');
    },
});
});

/* eslint-disable no-undef */
odoo.define('planning.calendar_frontend', function (require) {
"use strict";

const publicWidget = require('web.public.widget');
const time = require('web.time');
const translation = require('web.translation');
const _t = translation._t;

publicWidget.registry.PlanningView = publicWidget.Widget.extend({
    selector: '#calendar_employee',
    jsLibs: [
        '/web/static/lib/fullcalendar/core/main.js',
        '/web/static/lib/fullcalendar/core/locales-all.js',
        '/web/static/lib/fullcalendar/interaction/main.js',
        '/web/static/lib/fullcalendar/moment/main.js',
        '/web/static/lib/fullcalendar/daygrid/main.js',
        '/web/static/lib/fullcalendar/timegrid/main.js',
        '/web/static/lib/fullcalendar/list/main.js'
    ],
    cssLibs: [
        '/web/static/lib/fullcalendar/core/main.css',
        '/web/static/lib/fullcalendar/daygrid/main.css',
        '/web/static/lib/fullcalendar/timegrid/main.css',
        '/web/static/lib/fullcalendar/list/main.css'
    ],

    init: function (parent, options) {
        this._super.apply(this, arguments);
    },
    start: function () {
       if ($('.message_slug').attr('value')) {
           $("#PlanningToast").toast('show');
       }
       this._super.apply(this, arguments);
       this.calendarElement = this.$(".o_calendar_widget")[0];
       const employeeSlotsFcData = JSON.parse($('.employee_slots_fullcalendar_data').attr('value'));
       const openSlotsIds = $('.open_slots_ids').attr('value');
       const locale = $('.locale').attr('value');
       // default date: first event of either assigned slots or open shifts
       const defaultStart = moment($('.default_start').attr('value')).toDate();
       const defaultView = $('.default_view').attr('value');
       const minTime = $('.mintime').attr('value');
       const maxTime = $('.maxtime').attr('value');
       let calendarHeaders = {
           left: 'dayGridMonth,timeGridWeek,listMonth',
           center: 'title',
           right: 'today,prev,next'
       };
       if (employeeSlotsFcData.length === 0) {
           // There are no event to display. This is probably an empty slot sent for assignment
           calendarHeaders = {
                left: false,
                center: 'title',
                right: false,
            };
       }
       let titleFormat = 'MMMM YYYY';
        // The calendar is displayed if there are slots (open or not)
       if (defaultView && (employeeSlotsFcData || openSlotsIds)) {
           this.calendar = new FullCalendar.Calendar($("#calendar_employee")[0], {
                // Settings
                plugins: [
                    'moment',
                    'dayGrid',
                    'timeGrid',
                    'list',
                    'interraction'
                ],
                locale: locale,
                defaultView: defaultView,
                navLinks: true, // can click day/week names to navigate views
                eventLimit: 2, // allow "more" link when more than two events
                titleFormat: titleFormat,
                defaultDate: defaultStart,
                timeFormat: 'LT',
                displayEventEnd: true,
                height: 'auto',
                eventRender: this.eventRenderFunction,
                eventTextColor: 'white',
                eventOverlap: true,
                eventTimeFormat: {
                    hour: 'numeric',
                    minute: '2-digit',
                    meridiem: 'long',
                    omitZeroMinute: true,
                },
                minTime: minTime,
                maxTime: maxTime,
                header: calendarHeaders,
                // Data
                events: employeeSlotsFcData,
                // Event Function is called when clicking on the event
                eventClick: this.eventFunction.bind(this),
                buttonText: { today: "Today",  dayGridMonth: "Month", timeGridWeek: "Week", listMonth: 'List'},
                noEventsMessage: '',
                });
                this.calendar.setOption('locale', locale);
                this.calendar.render();
           }
    },
    eventRenderFunction: function (calRender) {
        const eventContent = calRender.el.querySelectorAll('.fc-time, .fc-title');
        if (calRender.view.type != 'listMonth') {
            calRender.el.classList.add('px-2', 'py-1');
        }
        if (calRender.view.type === 'dayGridMonth') {
            for (let i = 0; i < eventContent.length; i++) {
                eventContent[i].classList.add('d-block', 'text-truncate');
            }
        }
        calRender.el.classList.add('cursor-pointer');
        calRender.el.childNodes[0].classList.add('fw-bold');
    },
    formatDateAsBackend: function (date) {
        const weekday = moment(date).format('ddd.');
        const timeFormat = _t.database.parameters.time_format.replace(':%S', '');
        const dateTimeFormat = `${_t.database.parameters.date_format} ${timeFormat}`;
        const dateTime = moment(date).format(time.strftime_to_moment_format(dateTimeFormat));
        return `${weekday} ${dateTime}`;
    },
    eventFunction: function (calEvent) {
        const planningToken = $('.planning_token').attr('value');
        const employeeToken = $('.employee_token').attr('value');
        $(".modal-title").text(calEvent.event.title);
        $(".modal-header").css("background-color", calEvent.event.backgroundColor);
        $('.o_start_date').text(this.formatDateAsBackend(calEvent.event.start));
        let textValue = this.formatDateAsBackend(calEvent.event.end);
        if (calEvent.event.extendedProps.alloc_hours) {
            textValue += ` (${calEvent.event.extendedProps.alloc_hours})`;
        }
        if (parseFloat(calEvent.event.extendedProps.alloc_perc) < 100) {
            textValue += ` (${calEvent.event.extendedProps.alloc_perc}%)`;
        }
        $('.o_end_date').text(textValue);
        if (calEvent.event.extendedProps.role) {
            $("#role").prev().css("display", "");
            $("#role").text(calEvent.event.extendedProps.role);
            $("#role").css("display", "");
        } else {
            $("#role").prev().css("display", "none");
            $("#role").css("display", "none");
        }
        if (calEvent.event.extendedProps.note) {
            $("#note").prev().css("display", "");
            $("#note").text(calEvent.event.extendedProps.note);
            $("#note").css("display", "");
        } else {
            $("#note").prev().css("display", "none");
            $("#note").css("display", "none");
        }
        $("#allow_self_unassign").text(calEvent.event.extendedProps.allow_self_unassign);
        if (
            calEvent.event.extendedProps.allow_self_unassign
            && !calEvent.event.extendedProps.is_unassign_deadline_passed
            ) {
            document.getElementById("dismiss_shift").style.display = "block";
        } else {
            document.getElementById("dismiss_shift").style.display = "none";
        }
        $("#modal_action_dismiss_shift").attr("action", "/planning/" + planningToken + "/" + employeeToken + "/unassign/" + calEvent.event.extendedProps.slot_id);
        $("#fc-slot-onclick-modal").modal("show");
    },
});

// Add client actions
return publicWidget.registry.PlanningView;
});

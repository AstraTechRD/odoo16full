odoo.define('web_gantt.GanttRow', function (require) {
"use strict";

var core = require('web.core');
var config = require('web.config');
var session = require('web.session');
var Widget = require('web.Widget');
const pyUtils = require('web.py_utils');
let pyUtilsContext = null;
const fieldUtils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var GanttRow = Widget.extend({
    template: 'GanttView.Row',
    events: {
        'mouseleave': '_onMouseLeave',
        'mousemove .o_gantt_cell': '_onMouseMove',
        'mouseenter .o_gantt_pill': '_onPillEntered',
        'click .o_gantt_pill': '_onPillClicked',
        'click': '_onRowSidebarClicked',
        'click .o_gantt_cell_buttons > div > .o_gantt_cell_add': '_onButtonAddClicked',
        'click .o_gantt_cell_buttons > div > .o_gantt_cell_plan': '_onButtonPlanClicked',
    },
    NB_GANTT_RECORD_COLORS: 12,
    LEVEL_LEFT_OFFSET: 16, // 16 px per level
    // This determines the pills height. It needs to be an odd number. If it is not a pill can
    // be dropped between two rows without the droppables drop method being called (see tolerance: 'intersect').
    LEVEL_TOP_OFFSET: 31, // 31 px per level
    POPOVER_DELAY: 260,
    /**
     * @override
     * @param {Object} pillsInfo
     * @param {Object} viewInfo
     * @param {Object} options
     * @param {boolean} options.canCreate
     * @param {boolean} options.canEdit
     * @param {boolean} options.disableDragdrop Disable drag and drop for pills
     * @param {boolean} options.hideSidebar Hide sidebar
     * @param {boolean} options.isGroup If is group, It will display all its
     *                  pills on one row, disable resize, don't allow to create
     *                  new record when clicked on cell
     */
    init: function (parent, pillsInfo, viewInfo, options) {
        this._super.apply(this, arguments);
        var self = this;

        this.name = pillsInfo.groupName;
        this.groupLevel = pillsInfo.groupLevel;
        this.groupedByField = pillsInfo.groupedByField;
        this.pills = _.map(pillsInfo.pills, _.clone);
        this.resId = pillsInfo.resId;
        this.progressBar = pillsInfo.progressBar;

        this.viewInfo = viewInfo;
        this.fieldsInfo = viewInfo.fieldsInfo;
        this.state = viewInfo.state;
        this.colorField = viewInfo.colorField;

        this.options = options;
        this.SCALES = options.scales;
        this.isGroup = options.isGroup;
        this.isOpen = options.isOpen;
        this.rowId = options.rowId;
        this.fromServer = options.fromServer;
        this.pillLabel = options.pillLabel;
        this.isMobile = config.device.isMobile;
        this.unavailabilities = (options.unavailabilities || []).map(u => {
            return {
                startDate: self._convertToUserTime(u.start),
                stopDate: self._convertToUserTime(u.stop)
            };
        });

        this.consolidate = options.consolidate;
        this.consolidationParams = viewInfo.consolidationParams;

        this.dependencyEnabled = parent.dependencyEnabled;

        if(options.thumbnail){
            this.thumbnailUrl = session.url('/web/image', {
                model: options.thumbnail.model,
                id: this.resId,
                field: this.options.thumbnail.field,
            });
        }

        // the total row has some special behaviour
        this.isTotal = this.rowId === '__total_row__';

        this._adaptPills();
        this._snapToGrid(this.pills);
        this._calculateLevel();
        if (this.isGroup && this.pills.length) {
            this._aggregateGroupedPills();
        } else {
            this.progressField = viewInfo.progressField;
            this._evaluateDecoration();
        }
        this._calculateMarginAndWidth();

        if (this.pillLabel) {
            this._generatePillLabels(this.state.scale);
        }
        // Add the 16px odoo window default padding.
        this.leftPadding = (this.groupLevel + 1) * this.LEVEL_LEFT_OFFSET;
        const standardHeight = (this.isMobile ? (this.level > 0 ? this.level : 1) : this.level) * (this.LEVEL_TOP_OFFSET + 3) + (this.level > 0 ? this.level : 0);
        this.cellHeight = this.isMobile && this.level <= 1 ? standardHeight * 2 : standardHeight;

        this.MIN_WIDTHS = { full: 100, half: 50, quarter: 25 };
        this.PARTS = { full: 1, half: 2, quarter: 4 };

        this.cellMinWidth = this.MIN_WIDTHS[this.viewInfo.activeScaleInfo.precision];
        this.cellPart = this.PARTS[this.viewInfo.activeScaleInfo.precision];

        this._prepareSlots();
        this._insertIntoSlot();

        this.childrenRows = [];

        this._onButtonAddClicked = _.debounce(this._onButtonAddClicked, 500, true);
        this._onButtonPlanClicked = _.debounce(this._onButtonPlanClicked, 500, true);
        this._onPillClicked = _.debounce(this._onPillClicked, 500, true);

        if (this.isTotal) {
            const maxCount = Math.max(...this.pills.map(p => p.count));
            const factor = maxCount ? (90 / maxCount) : 0;
            for (let p of this.pills) {
                p.totalHeight = factor * p.count;
            }
        }
        this.isRTL = _t.database.parameters.direction === "rtl";
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$el) {
            const popover = Popover.getInstance(this.$('.o_gantt_pill')[0]);
            if (popover) {
                popover.dispose();
            }
        }
        this._super();
    },
 
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Set the row (if not total row) as droppable for the pills (but the draggables option "containment" prevents
     * them from going above the row headers).
     * See @_setDraggable
     * @param {DOMElement} firstCell
     */
    setDroppable: function (firstCell) {
        if (this.isTotal) {
            return;
        }
        var self = this;
        const resizeSnappingWidth = this._getResizeSnappingWidth(firstCell);
        this.$el.droppable({
            accept: ".o_gantt_pill",
            drop: function (event, ui) {
                var diff = self._getDiff(resizeSnappingWidth, ui.position.left);
                var $pill = ui.draggable;
                const oldRowId = $pill.closest('.o_gantt_row')[0].dataset.rowId;
                if (diff || (self.rowId !== oldRowId)) { // do not perform write if nothing change
                    const action = event.ctrlKey || event.metaKey ? 'copy': 'reschedule';
                    self._saveDragChanges($pill.data('id'), diff, oldRowId, self.rowId, action);
                } else {
                    ui.helper.animate({
                        left: 0,
                        top: 0,
                    });
                }
            },
            tolerance: 'intersect',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * binds the popover of a specific pill
     * @param target
     * @private
     */
    _bindPillPopover: function(target) {
        var self = this;
        var $target = $(target);
        if (!$target.hasClass('o_gantt_pill')) {
            $target = this.$(target.offsetParent);
        }
        $target.popover({
            container: this.$el,
            trigger: 'hover',
            delay: {show: this.POPOVER_DELAY},
            html: true,
            placement: 'auto',
            content: function () {
                return self.viewInfo.popoverQWeb.render('gantt-popover', self._getPopoverContext($(this).data('id')));
            },
        }).popover("show");
    },

    /**
     * Compute minimal levels required to display all pills without overlapping
     *
     * @private
     */
    _calculateLevel: function () {
        if (this.isGroup || !this.pills.length) {
            // We want shadow pills to overlap each other
            this.level = 0;
            this.pills.forEach(function (pill) {
                pill.level = 0;
            });
        } else {
            // Sort pills according to start date
            this.pills = _.sortBy(this.pills, 'startDate');
            this.pills[0].level = 0;
            var levels = [{
                pills: [this.pills[0]],
                maxStopDate: this.pills[0].stopDate,
            }];
            for (var i = 1; i < this.pills.length; i++) {
                var currentPill = this.pills[i];
                for (var l = 0; l < levels.length; l++) {
                    if (currentPill.startDate >= levels[l].maxStopDate) {
                        currentPill.level = l;
                        levels[l].pills.push(currentPill);
                        if (currentPill.stopDate > levels[l].maxStopDate) {
                            levels[l].maxStopDate = currentPill.stopDate;
                        }
                        break;
                    }
                }
                if (!currentPill.level && currentPill.level != 0) {
                    currentPill.level = levels.length;
                    levels.push({
                        pills: [currentPill],
                        maxStopDate: currentPill.stopDate,
                    });
                }
            }
            this.level = levels.length;
        }
    },
    /**
     * Adapt pills to the range of current gantt view
     * Disable resize feature if date is before the start of the gantt scope
     * Disable resize feature for group rows
     *
     * @private
     */
    _adaptPills: function () {
        var self = this;
        var dateStartField = this.state.dateStartField;
        var dateStopField = this.state.dateStopField;
        var ganttStartDate = this.state.startDate;
        var ganttStopDate = this.state.stopDate;
        this.pills.forEach(function (pill) {
            var pillStartDate = self._convertToUserTime(pill[dateStartField]);
            var pillStopDate = self._convertToUserTime(pill[dateStopField]);
            if (pillStartDate < ganttStartDate) {
                pill.startDate = ganttStartDate;
                pill.disableStartResize = true;
            } else {
                pill.startDate = pillStartDate;
            }
            if (pillStopDate > ganttStopDate) {
                pill.stopDate = ganttStopDate;
                pill.disableStopResize = true;
            } else {
                pill.stopDate = pillStopDate;
            }
            // Disable resize feature for groups
            if (self.isGroup) {
                pill.disableStartResize = true;
                pill.disableStopResize = true;
            }
        });
    },
    /**
     * Aggregate overlapping pills in group rows
     *
     * @private
     */
    _aggregateGroupedPills: function () {
        var self = this;
        var sortedPills = _.sortBy(_.map(this.pills, _.clone), 'startDate');
        var firstPill = sortedPills[0];
        firstPill.count = 1;

        var timeToken = this.SCALES[this.state.scale].time;
        var precision = this.viewInfo.activeScaleInfo.precision;
        var cellTime = this.SCALES[this.state.scale].cellPrecisions[precision];
        var intervals = _.reduce(this.viewInfo.slots, function (intervals, slotStart) {
            intervals.push(slotStart);
            if (precision === 'half') {
                intervals.push(slotStart.clone().add(cellTime, timeToken));
            }
            return intervals;
        }, []);

        this.pills = _.reduce(intervals, function (pills, intervalStart) {
            var intervalStop = intervalStart.clone().add(cellTime, timeToken);
            var pillsInThisInterval = _.filter(self.pills, function (pill) {
                return pill.startDate < intervalStop && pill.stopDate > intervalStart;
            });
            if (pillsInThisInterval.length) {
                var previousPill = pills[pills.length - 1];
                var isContinuous = previousPill &&
                    _.intersection(previousPill.aggregatedPills, pillsInThisInterval).length;

                if (isContinuous && previousPill.count === pillsInThisInterval.length) {
                    // Enlarge previous pill so that it spans the current slot
                    previousPill.stopDate = intervalStop;
                    previousPill.aggregatedPills = previousPill.aggregatedPills.concat(pillsInThisInterval);
                } else {
                    var newPill = {
                        id: 0,
                        count: pillsInThisInterval.length,
                        aggregatedPills: pillsInThisInterval,
                        startDate: moment.max(_.min(pillsInThisInterval, 'startDate').startDate, intervalStart),
                        stopDate: moment.min(_.max(pillsInThisInterval, 'stopDate').stopDate, intervalStop),
                    };

                    // Enrich the aggregates with consolidation data
                    if (self.consolidate && self.consolidationParams.field) {
                        newPill.consolidationValue = pillsInThisInterval.reduce(
                            function (sum, pill) {
                                if (!pill[self.consolidationParams.excludeField]) {
                                    return sum + pill[self.consolidationParams.field];
                                }
                                return sum; // Don't sum this pill if it is excluded
                            },
                            0
                        );
                        newPill.consolidationMaxValue = self.consolidationParams.maxValue;
                        newPill.consolidationExceeded = newPill.consolidationValue > newPill.consolidationMaxValue;
                    }

                    pills.push(newPill);
                }
            }
            return pills;
        }, []);

        var maxCount = _.max(this.pills, function (pill) {
            return pill.count;
        }).count;
        var minColor = 215;
        var maxColor = 100;
        this.pills.forEach(function (pill) {
            pill.consolidated = true;
            if (self.consolidate && self.consolidationParams.maxValue) {
                pill.status = pill.consolidationExceeded ? 'danger' : 'success';
                pill.display_name = pill.consolidationValue;
            } else {
                var color = minColor - ((pill.count - 1) / maxCount) * (minColor - maxColor);
                pill.style = _.str.sprintf("background-color: rgba(%s, %s, %s, 0.6)", color, color, color);
                pill.display_name = self._getAggregateGroupedPillsDisplayName(pill);
            }
        });
    },
    /**
     * This function will add a 'label' property to each
     * non-consolidated pill included in the pills list.
     * This new property is a string meant to replace
     * the text displayed on a pill.
     *
     * @private
     * @param {Object} pills
     * @param {string} scale
     */
    _generatePillLabels(scale) {
       // as localized yearless date formats do not exists yet in momentjs,
        // this is an awful surgery adapted from SO: https://stackoverflow.com/a/29641375
        // The following regex chain will:
        //  - remove all 'Y'(ignoring case),
        //  - then remove duplicate consecutives separators,
        //  - and finally remove trailing orphaned separators left
        const self = this;
        this.pills.forEach((pill) => {
            const dateFormat = moment.localeData().longDateFormat('l');
            const yearlessDateFormat = dateFormat.replace(/Y/gi, '').replace(/(\W)\1+/g, '$1').replace(/^\W|\W$/, '');

            const localStartDateTime = (pill[self.state.dateStartField] || pill.startDate).clone().local();
            const localEndDateTime = (pill[self.state.dateStopField] || pill.stopDate).clone().local();

            const spanAccrossDays = localStartDateTime.clone().startOf('day')
                .diff(localEndDateTime.clone().startOf('day'), 'days') != 0;

            const spanAccrossWeeks = localStartDateTime.clone().startOf('week')
                .diff(localEndDateTime.clone().startOf('week'), 'weeks') != 0;

            const spanAccrossMonths = localStartDateTime.clone().startOf('month')
                .diff(localEndDateTime.clone().startOf('month'), 'months') != 0;

            const labelElements = [];

            // Start & End Dates
            if (scale === 'year' && !spanAccrossDays) {
                labelElements.push(localStartDateTime.format(yearlessDateFormat));
            } else if (
                (scale === 'day' && spanAccrossDays) ||
                (scale === 'week' && spanAccrossWeeks) ||
                (scale === 'month' && spanAccrossMonths) ||
                (scale === 'year' && spanAccrossDays)
            ) {
                labelElements.push(localStartDateTime.format(yearlessDateFormat));
                labelElements.push(localEndDateTime.format(yearlessDateFormat));
            }

            // Start & End Times
            if (pill.allocated_hours && !spanAccrossDays && ['week', 'month'].includes(scale)) {
                labelElements.push(
                    localStartDateTime.format('LT'),
                    localEndDateTime.format('LT') + ' (' + fieldUtils.format.float_time(pill.allocated_hours, {}, {noLeadingZeroHour: true}).replace(/(:00|:)/g, 'h') + ')'
                );
            }

            // Original Display Name
            if (scale !== 'month' || spanAccrossDays) {
                labelElements.push(pill.display_name);
            }

            pill.label = labelElements.filter(el => !!el).join(' - ');
        });
    },

    /**
     * Returns the count of pill
     *
     * @private
     * @param {Object} pill
     * @returns {integer}
     */
    _getAggregateGroupedPillsDisplayName(pill) {
        return pill.count;
    },
    /**
     * Calculate left margin and width for pills
     *
     * @private
     */
    _calculateMarginAndWidth: function () {
        var self = this;
        var left;
        var diff;
        this.pills.forEach(function (pill) {
            let widthPill;
            let margin;
            switch (self.state.scale) {
                case 'day':
                    left = pill.startDate.diff(pill.startDate.clone().startOf('hour'), 'minutes');
                    pill.leftMargin = (left / 60) * 100;
                    diff = pill.stopDate.diff(pill.startDate, 'minutes');
                    var gapSize = pill.stopDate.diff(pill.startDate, 'hours') - 1; // Eventually compensate border(s) width
                    widthPill = (diff / 60) * 100;
                    margin = pill.aggregatedPills ? 0 : 4;
                    pill.width = gapSize > 0 ? `calc(${widthPill}% + ${gapSize}px - ${margin}px)` : `calc(${widthPill}% - ${margin}px)`;
                    break;
                case 'week':
                case 'month':
                    left = pill.startDate.diff(pill.startDate.clone().startOf('day'), 'hours');
                    pill.leftMargin = (left / 24) * 100;
                    diff = pill.stopDate.diff(pill.startDate, 'hours');
                    var gapSize = pill.stopDate.diff(pill.startDate, 'days') - 1; // Eventually compensate border(s) width
                    widthPill = (diff / 24) * 100;
                    margin = pill.aggregatedPills ? 0 : 4;
                    pill.width = gapSize > 0 ? `calc(${widthPill}% + ${gapSize}px - ${margin}px)` : `calc(${widthPill}% - ${margin}px)`;
                    break;
                case 'year':
                    var startDateMonthStart = pill.startDate.clone().startOf('month');
                    var stopDateMonthEnd = pill.stopDate.clone().endOf('month');
                    left = pill.startDate.diff(startDateMonthStart, 'days');
                    pill.leftMargin = (left / 30) * 100;

                    var monthsDiff = stopDateMonthEnd.diff(startDateMonthStart, 'months', true);
                    margin = pill.aggregatedPills ? 0 : 4;
                    if (monthsDiff < 1) {
                        // A 30th of a month slot is too small to display
                        // 1-day events are displayed as if they were 2-days events
                        diff = Math.max(Math.ceil(pill.stopDate.diff(pill.startDate, 'days', true)), 2);
                        pill.width = `calc(${(diff / pill.startDate.daysInMonth()) * 100}% - ${margin}px)`;
                    } else {
                        // The pill spans more than one month, so counting its
                        // number of days is not enough as some months have more
                        // days than others. We need to compute the proportion
                        // of each month that the pill is actually taking.
                        var startDateMonthEnd = pill.startDate.clone().endOf('month');
                        var diffMonthStart = Math.ceil(startDateMonthEnd.diff(pill.startDate, 'days', true));
                        var widthMonthStart = (diffMonthStart / pill.startDate.daysInMonth());

                        var stopDateMonthStart = pill.stopDate.clone().startOf('month');
                        var diffMonthStop = Math.ceil(pill.stopDate.diff(stopDateMonthStart, 'days', true));
                        var widthMonthStop = (diffMonthStop / pill.stopDate.daysInMonth());

                        var width = Math.max((widthMonthStart + widthMonthStop), (2 / 30)) * 100;
                        if (monthsDiff > 1) { // start and end months are already covered
                            // If the pill spans more than 2 months, we know
                            // that the middle months are fully covered
                            monthsDiff = Math.floor(monthsDiff)
                            width += (monthsDiff - 1) * 100;
                        }
                        // Added months difference in calculation in px as its width reduces inversely as we increases the width of pill
                        pill.width = `calc(${width}% + ${monthsDiff}px - ${margin}px)`;
                    }
                    break;
                default:
                    break;
            }

            // Add 1px top-gap to events sharing the same cell.
            pill.topPadding = pill.level * (self.LEVEL_TOP_OFFSET + 4) + 2;
        });
    },
    /**
    * Convert date to user timezone
    *
    * @private
    * @param {Moment} date
    * @returns {Moment} date in user timezone
    */
    _convertToUserTime: function (date) {
        // we need to change the original timezone (UTC) to take the user
        // timezone
        return date.clone().local();
    },
    /**
     * Evaluate decoration conditions
     *
     * @private
     */
    _evaluateDecoration: function () {
        var self = this;
        this.pills.forEach(function (pill) {
            var pillDecorations = [];
            _.each(self.viewInfo.pillDecorations, function (expr, decoration) {
                if (py.PY_isTrue(py.evaluate(expr, self._getDecorationEvalContext(pill)))) {
                    pillDecorations.push(decoration);
                }
            });
            pill.decorations = pillDecorations;

            if (self.colorField) {
                pill._color = self._getColor(pill[self.colorField]);
            }

            if (self.progressField) {
                pill._progress = pill[self.progressField] || 0;
            }
        });
    },
    /**
     * @param {integer|Array} value
     * @private
     */
    _getColor: function (value) {
        if (_.isNumber(value)) {
            return Math.round(value) % this.NB_GANTT_RECORD_COLORS;
        } else if (_.isArray(value)) {
            return value[0] % this.NB_GANTT_RECORD_COLORS;
        }
        return 0;
    },
    /**
     * Get context to evaluate decoration
     *
     * @private
     * @param {Object} pillData
     * @returns {Object} context contains pill data, current date, user session
     */
    _getDecorationEvalContext: function (pillData) {
        return Object.assign(
            {},
            this._getPyUtilsContext(),
            session.user_context,
            this._getPillEvalContext(pillData),
        );
    },
    /**
     * @private
     * @param {number} gridOffset
     */
    _getDiff: function (resizeSnappingWidth, gridOffset) {
        return Math.round(gridOffset / resizeSnappingWidth) * this.viewInfo.activeScaleInfo.interval;
    },
    /**
     * Evaluate the pill evaluation context.
     *
     * @private
     * @param {Object} pillData
     * @returns {Object} context
     */
    _getPillEvalContext: function (pillData) {
        var pillContext = _.clone(pillData);
        for (var fieldName in pillContext) {
            const field = this.fieldsInfo[fieldName];
            if (field) {
                const pillCurrentField = pillContext[fieldName];
                if (pillCurrentField instanceof moment) {
                    // Replace by ISO formatted string only, without computing it as it is already avalaible in the Moment object interns.
                    pillContext[fieldName] = pillCurrentField._i;
                }
                else if (field.type === 'date' || field.type === 'datetime') {
                    if (pillCurrentField) {
                        pillContext[fieldName] = JSON.parse(JSON.stringify(pillCurrentField));
                    }
                    continue;
                }
            }
        }
        return pillContext;
    },
    /**
     * Get context to display in popover template
     *
     * @private
     * @param {integer} pillID
     * @returns {Object}
     */
    _getPopoverContext: function (pillID) {
        var data = _.clone(_.findWhere(this.pills, {id: pillID}));
        data.userTimezoneStartDate = this._convertToUserTime(data[this.state.dateStartField]);
        data.userTimezoneStopDate = this._convertToUserTime(data[this.state.dateStopField]);
        return data;
    },
    /**
    * Get pyUtils context
    * When in the same tick, the same pyUtils.context in returned.
    *
    * @returns {Object} the pyUtils context
     */
    _getPyUtilsContext() {
        if (!pyUtilsContext) {
            pyUtilsContext = pyUtils.context();
            Promise.resolve().then(() => {
                pyUtilsContext = null;
            });
        }
        return pyUtilsContext;
    },
    /**
     * @private
     * @returns {number}
     */
    _getResizeSnappingWidth: function (firstCell) {
        if (!this.firstCell) {
            this.firstCell = firstCell || $('.o_gantt_view .o_gantt_header_scale .o_gantt_header_cell:first')[0];
        }
        // jQuery (< 3.0) rounds the width value but we need the exact value
        // getBoundingClientRect is costly when there are lots of rows
        return this.firstCell.getBoundingClientRect().width / this.cellPart;
    },
    /**
     * Insert the pills into the gantt row slots according to their start dates
     *
     * @private
     */
    _insertIntoSlot: function () {
        var slotsToFill = this.slots;
        this.pills.forEach(function (currentPill) {
            var skippedSlots = [];
            slotsToFill.some(function (currentSlot) {
                var fitsInThisSlot = currentPill.startDate < currentSlot.stop;
                if (fitsInThisSlot) {
                    currentSlot.pills.push(currentPill);
                } else {
                    skippedSlots.push(currentSlot);
                }
                return fitsInThisSlot;
            });
            // Pills are sorted by start date, so any slot that was skipped
            // for this pill will not be suitable for any of the next pills
            slotsToFill = _.difference(slotsToFill, skippedSlots);
        });
    },
    /**
     * Prepare the gantt row slots
     *
     * @private
     */
    _prepareSlots: function () {
        const { interval, time, cellPrecisions } = this.SCALES[this.state.scale];
        const precision = this.viewInfo.activeScaleInfo.precision;
        const cellTime = cellPrecisions[precision];

        function getSlotStyle(cellPart, subSlotUnavailabilities, isToday) {
            function color(d) {
                if (isToday) {
                    return d ? 'var(--Gant__DayOff-background-color)' : 'var(--Gant__DayOffToday-background-color)';
                }
                return d ?  'var(--Gant__DayOff-background-color)' :  'var(--Gant__Day-background-color)';
            }
            const sum = subSlotUnavailabilities.reduce((acc, d) => acc + d);
            if (!sum) {
                return '';
            }
            if (cellPart === sum) {
                return `background: ${color(1)}`;
            }
            if (cellPart === 2) {
                const [c0, c1] = subSlotUnavailabilities.map(color);
                return `background: linear-gradient(90deg, ${c0} 49%, ${c1} 50%);`
            }
            if (cellPart === 4) {
                const [c0, c1, c2, c3] = subSlotUnavailabilities.map(color);
                return `background: linear-gradient(90deg, ${c0} 24%, ${c1} 25%, ${c1} 49%, ${c2} 50%, ${c2} 74%, ${c3} 75%);`
            }
        }

        this.slots = [];

        // We assume that the 'slots' (dates) are naturally ordered
        // and that unavailabilties have been normalized
        // (i.e. naturally ordered and pairwise disjoint).
        // A subslot is considered unavailable (and greyed) when totally covered by
        // an unavailability.
        let index = 0;
        for (const date of this.viewInfo.slots) {
            const slotStart = date;
            const slotStop = date.clone().add(1, interval);
            const isToday = date.isSame(new Date(), 'day') && this.state.scale !== 'day';

            let slotStyle = '';
            if (!this.isGroup && this.unavailabilities.slice(index).length) {
                let subSlotUnavailabilities = [];
                for (let j = 0; j < this.cellPart; j++) {
                    const subSlotStart = date.clone().add(j * cellTime, time);
                    const subSlotStop = date.clone().add((j + 1) * cellTime, time).subtract(1, 'seconds');
                    let subSlotUnavailable = 0;
                    for (let i = index; i < this.unavailabilities.length; i++) {
                        let u = this.unavailabilities[i];
                        if (subSlotStop > u.stopDate) {
                            index++;
                        } else if (u.startDate <= subSlotStart) {
                            subSlotUnavailable = 1;
                            break;
                        }
                    }
                    subSlotUnavailabilities.push(subSlotUnavailable);
                }
                slotStyle = getSlotStyle(this.cellPart, subSlotUnavailabilities, isToday);
            }

            this.slots.push({
                isToday: isToday,
                style: slotStyle,
                hasButtons: !this.isGroup && !this.isTotal,
                start: slotStart,
                stop: slotStop,
                pills: [],
            });
        }
    },
    /**
     * Save drag changes
     *
     * @private
     * @param {integer} pillID
     * @param {integer} diff
     * @param {string} oldRowId
     * @param {string} newRowId
     * @param {'copy'|'reschedule'} action
     */
    _saveDragChanges: function (pillId, diff, oldRowId, newRowId, action) {
        this.trigger_up('pill_dropped', {
            pillId: pillId,
            diff: diff,
            oldRowId: oldRowId,
            newRowId: newRowId,
            groupLevel: this.groupLevel,
            action: action,
        });
    },
    /**
     * Save resize changes
     *
     * @private
     * @param {integer} pillID
     * @param {integer} resizeDiff
     * @param {string} direction
     */
    _saveResizeChanges: function (pillID, resizeDiff, direction) {
        var pill = _.findWhere(this.pills, {id: pillID});
        var data = { id: pillID };
        if (direction === 'left') {
            data.field = this.state.dateStartField;
            data.date = pill[this.state.dateStartField].clone().subtract(resizeDiff, this.viewInfo.activeScaleInfo.time);
        } else {
            data.field = this.state.dateStopField;
            data.date = pill[this.state.dateStopField].clone().add(resizeDiff, this.viewInfo.activeScaleInfo.time);
        }
        this.trigger_up('pill_resized', data);
    },
    /**
     * Set the draggable jQuery property on a $pill.
     * @private
     * @param {jQuery} $pill
     */
    _setDraggable: function ($pill) {
        if ($pill.hasClass('ui-draggable-dragging')) {
            return;
        }

        var self = this;
        var pill = _.findWhere(this.pills, { id: $pill.data('id') });

        // DRAGGABLE
        if (this.options.canEdit && !pill.disableStartResize && !pill.disableStopResize && !this.isGroup) {

            const resizeSnappingWidth = this._getResizeSnappingWidth();

            if ($pill.draggable( "instance")) {
                return;
            }
            if (!this.$containment) {
                this.$containment = $('#o_gantt_containment');
            }
            $pill.draggable({
                containment: this.$containment,
                start: function (event, ui) {
                    self.trigger_up('updating_pill_started');

                    const pillWidth = $pill[0].getBoundingClientRect().width;
                    ui.helper.css({ width: pillWidth });
                    ui.helper.removeClass('position-relative');

                    // The following trigger up will sometimes add the class o_hidden on the $pill.
                    // This is why the pill's width is computed above.
                    self.trigger_up('start_dragging', {
                        $draggedPill: $pill,
                        $draggedPillClone: ui.helper,
                    });

                    self.$el.addClass('o_gantt_dragging');
                    $pill.popover('hide');
                    self.$('.o_gantt_pill').popover('disable');
                },
                drag: function (event, ui) {
                    if ($(event.target).hasClass('o_gantt_pill_editing')) {
                        // Kill draggable if pill opened its dialog
                        return false;
                    }
                    var diff = self._getDiff(resizeSnappingWidth, ui.position.left);
                    self._updateResizeBadge(ui.helper, diff, ui);

                    const pointObject = { x: event.pageX, y: event.pageY };
                    const options = { container: document.body };
                    const $el = $.nearest(pointObject, '.o_gantt_hoverable', options).first();
                    if ($el.length) {
                        // remove ui-drag-hover class from other rows
                        $('.o_gantt_hoverable').removeClass('ui-drag-hover');
                        $el.addClass('ui-drag-hover');
                    }
                },
                stop: function () {
                    self.trigger_up('updating_pill_stopped');
                    self.trigger_up('stop_dragging');

                    self.$('.ui-drag-hover').removeClass('ui-drag-hover');
                    self.$el.removeClass('o_gantt_dragging');
                    self.$('.o_gantt_pill').popover('enable').popover('dispose');
                },
                helper: 'clone',
            });
        } else {
            if ($pill.draggable( "instance")) {
                return;
            }
            if (!this.$lockIndicator) {
                this.$lockIndicator = $('<div class="fa fa-lock"/>').css({
                    'z-index': 20,
                    position: 'absolute',
                    top: '4px',
                    right: '4px',
                });
            }
            $pill.draggable({
                // prevents the pill from moving but allows to send feedback
                grid: [0, 0],
                start: function () {
                    self.trigger_up('updating_pill_started');
                    self.trigger_up('start_no_dragging');
                    $pill.popover('hide');
                    self.$('.o_gantt_pill').popover('disable');
                    self.$lockIndicator.appendTo($pill);
                },
                drag: function (ev) {
                    if ($(ev.target).hasClass('o_gantt_pill_editing')) {
                        // Kill draggable if pill opened its dialog
                        return false;
                    }
                },
                stop: function () {
                    self.trigger_up('updating_pill_stopped');
                    self.trigger_up('stop_no_dragging');
                    self.$('.o_gantt_pill').popover('enable').popover('dispose');
                    self.$lockIndicator.detach();
                },
            });
            $pill.addClass('o_fake_draggable');
        }
    },
    /**
     * Set the resizable jQuery property on a $pill.
     * @private
     * @param {jQuery} $pill
     */
    _setResizable: function ($pill) {
        if ($pill.hasClass('ui-resizable')) {
            return;
        }
        var self = this;
        var pillHeight = this.$('.o_gantt_pill:first').height();

        var pill = _.findWhere(self.pills, { id: $pill.data('id') });

        const resizeSnappingWidth = this._getResizeSnappingWidth();

        // RESIZABLE
        var handles = [];
        if (!pill.disableStartResize) {
            handles.push('w');
        }
        if (!pill.disableStopResize) {
            handles.push('e');
        }
        if (handles.length && !self.isGroup && self.options.canEdit) {
            $pill.resizable({
                handles: handles.join(', '),
                odoo_isRTL: this.isRTL,
                // DAM: I wanted to use a containment but there is a bug with them
                // when elements are both draggable and resizable. In that case, is is no more possible
                // to resize on the left side of the pill (I mean starting from left, go to left)
                grid: [resizeSnappingWidth, pillHeight],
                start: function () {
                    $pill.popover('hide');
                    self.$('.o_gantt_pill').popover('disable');
                    self.trigger_up('updating_pill_started');
                    self.$el.addClass('o_gantt_dragging');
                },
                resize: function (event, ui) {
                    var diff = Math.round((ui.size.width - ui.originalSize.width) / resizeSnappingWidth * self.viewInfo.activeScaleInfo.interval);
                    self._updateResizeBadge($pill, diff, ui);
                },
                stop: function (event, ui) {
                    // 'stop' is triggered by the mouseup event. Right after, the click is event is
                    // triggered. As we also listen to this event (to open a dialog to edit the pill),
                    // we have to delay a bit the moment where we mark the pill as no longer being
                    // updated, to prevent the dialog from opening when the user ends its resize
                    setTimeout(() => {
                        if (!self.isDestroyed()) {
                            self.trigger_up('updating_pill_stopped');
                            self.$el.removeClass('o_gantt_dragging');
                            self.$('.o_gantt_pill').popover('enable').popover('dispose');
                        }
                    });
                    var diff = Math.round((ui.size.width - ui.originalSize.width) / resizeSnappingWidth * self.viewInfo.activeScaleInfo.interval);
                    // Sometimes the difference (diff) can be falsely rounded (see planning/work entries), 
                    // leading to changes in the start/end_dates. With the code below the difference 
                    // will always be one of the cell precisions or 0 making the computation more robust. 
                    var precisions = self.SCALES[self.state.scale].cellPrecisions;
                    var smallest_precision = Math.min(...Object.entries(precisions).map(([key, value]) => value));
                    if (diff % smallest_precision != 0) {
                        diff = Math.floor(diff/smallest_precision) * smallest_precision;
                    }
                    var direction = ui.position.left ? 'left' : 'right';
                    if (diff) { // do not perform write if nothing change
                        self._saveResizeChanges(pill.id, diff, direction);
                    }
                },
            });
        }
    },
    /**
     * Snap timespans start and stop dates on grid described by scale precision
     * @params Array<Object> timeSpans objects representing timespans. They need
     *      to have a startDate and a stopDate properties.
     *
     * @private
     */
    _snapToGrid: function (timeSpans) {
        var self = this;
        var interval = this.viewInfo.activeScaleInfo.interval;
        switch (this.state.scale) {
            case 'day':
                timeSpans.forEach(function (span) {
                    var snappedStartDate = self._snapMinutes(span.startDate, interval);
                    var snappedStopDate = self._snapMinutes(span.stopDate, interval);
                    // Set min width
                    var minuteDiff = snappedStartDate.diff(snappedStopDate, 'minute');
                    if (minuteDiff === 0) {
                        if (snappedStartDate > span.startDate) {
                            span.startDate = snappedStartDate.subtract(interval, 'minute');
                            span.stopDate = snappedStopDate;
                        } else {
                            span.startDate = snappedStartDate;
                            span.stopDate = snappedStopDate.add(interval, 'minute');
                        }
                    } else {
                        span.startDate = snappedStartDate;
                        span.stopDate = snappedStopDate;
                    }
                });
                break;
            case 'week':
            case 'month':
                timeSpans.forEach(function (span) {
                    var snappedStartDate = self._snapHours(span.startDate, interval);
                    var snappedStopDate = self._snapHours(span.stopDate, interval);
                    // Set min width
                    var hourDiff = snappedStartDate.diff(snappedStopDate, 'hour');
                    if (hourDiff === 0) {
                        if (snappedStartDate.diff(span.startDate, 'hours') > 2 && span.stopDate.diff(snappedStopDate, 'hours') > 2) {
                            span.startDate = snappedStartDate.subtract(interval, 'hour');
                            span.stopDate = snappedStopDate.add(interval, 'hour');
                        } else if (snappedStartDate > span.startDate) {
                            span.startDate = snappedStartDate.subtract(interval, 'hour');
                            span.stopDate = snappedStopDate;
                        } else {
                            span.startDate = snappedStartDate;
                            span.stopDate = snappedStopDate.add(interval, 'hour');
                        }
                    } else {
                        if (snappedStartDate.diff(span.startDate, 'hours') > 2) {
                            snappedStartDate = snappedStartDate.subtract(interval, 'hour');
                        }
                        if (span.stopDate.diff(snappedStopDate, 'hours') > 2) {
                            snappedStopDate = snappedStopDate.add(interval, 'hour');
                        }
                        span.startDate = snappedStartDate;
                        span.stopDate = snappedStopDate;
                    }
                });
                break;
            case 'year':
                timeSpans.forEach(function (span) {
                    span.startDate = span.startDate.clone().startOf('month');
                    span.stopDate = span.stopDate.clone().endOf('month');
                });
                break;
            default:
                break;
        }
    },
    /**
     * Snap a day to given interval
     *
     * @private
     * @param {Moment} date
     * @param {integer} interval
     * @returns {Moment} snapped date
     */
    _snapHours: function (date, interval) {
        var snappedHours = Math.round(date.clone().hour() / interval) * interval;
        return date.clone().hour(snappedHours).minute(0).second(0);
    },
    /**
     * Snap a hour to given interval
     *
     * @private
     * @param {Moment} date
     * @param {integer} interval
     * @returns {Moment} snapped hour date
     */
    _snapMinutes: function (date, interval) {
        var snappedMinutes = Math.round(date.clone().minute() / interval) * interval;
        return date.clone().minute(snappedMinutes).second(0);
    },
    /**
     * @private
     * @param {jQuert} $pill
     * @param {integer} diff
     * @param {Object} ui
     */
    _updateResizeBadge: function ($pill, diff, ui) {
        $pill.find('.o_gantt_pill_resize_badge').remove();
        if (diff) {
            var direction = ui.position.left ? 'left' : 'right';
            $( QWeb.render('GanttView.ResizeBadge', {
                diff: diff,
                direction: direction,
                time: this.viewInfo.activeScaleInfo.time,
            } ), { css: { 'z-index': 2 } } )
            .appendTo($pill);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When click on cell open dialog to create new record with prefilled fields
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonAddClicked: function (ev) {
        var date = moment($(ev.currentTarget).closest('.o_gantt_cell').data('date'));
        this.trigger_up('add_button_clicked', {
            date: date,
            rowId: this.rowId,
        });
    },
    /**
     * When click on cell open dialog to create new record with prefilled fields
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonPlanClicked: function (ev) {
        var date = moment($(ev.currentTarget).closest('.o_gantt_cell').data('date'));
        this.trigger_up('plan_button_clicked', {
            date: date,
            rowId: this.rowId,
        });
    },
    /**
     * When entering a cell, it displays some buttons (but not when resizing
     * another pill, we thus can't use css rules).
     *
     * Note that we cannot do that on the cell mouseenter because we don't enter
     * the cell we moving the mouse on a pill that spans on multiple cells.
     *
     * Also note that we try to *avoid using jQuery* here to reduce the time
     * spent in this function so the whole view doesn't feel sluggish when there
     * are a lot of records.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseMove: function (ev) {
        if ((this.options.canCreate || this.options.canEdit) &&
            !this.$el[0].classList.contains('o_gantt_dragging')) {
            // Pills are part of the cell in which they start. If a pill is
            // longer than one cell, and the user is hovering on the right
            // side of the pill, the browser will say that the left cell is
            // hovered, since the hover event will bubble up from the pill to
            // the cell which contains it, hence, the left one. The only way we
            // found to target the real cell on which the user is currently
            // hovering is calling the costly elementsFromPoint function.
            // Besides, this function will not work in the test environment.
            var elementsFromPoint = function (x, y) {
                if (document.elementsFromPoint)
                    return document.elementsFromPoint(x, y);
                if (document.msElementsFromPoint) {
                    return Array.prototype.slice.call(document.msElementsFromPoint(x, y));
                }
            };

            var hoveredCell;
            if (ev.target.classList.contains('o_gantt_pill') || ev.target.parentNode.classList.contains('o_gantt_pill')) {
                elementsFromPoint(ev.pageX, ev.pageY).some(function (element) {
                    return element.classList.contains('o_gantt_cell') ? ((hoveredCell = element), true) : false;
                });
            } else {
                hoveredCell = ev.currentTarget;
            }

            if (hoveredCell && hoveredCell != this.lastHoveredCell) {
                if (this.lastHoveredCell) {
                    this.lastHoveredCell.classList.remove('o_hovered');
                }
                hoveredCell.classList.add('o_hovered');
                this.lastHoveredCell = hoveredCell;
            }
        }
    },
    /**
     * @private
     */
    _onMouseLeave: function () {
        // User leaves this row to enter another one
        this.$(".o_gantt_cell.o_hovered").removeClass('o_hovered');
        this.lastHoveredCell = undefined;
    },
    /**
     * When click on pill open dialog to view record
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onPillClicked: function (ev) {
        if (!this.isGroup) {
            this.trigger_up('pill_clicked', {
                target: $(ev.currentTarget),
            });
        }
    },
    /**
     * Set the draggable and resizable jQuery properties on a pill when the user
     * enters the pill.
     *
     * This is only done at this time and not in `on_attach_callback` to
     * optimize the rendering (creating jQuery draggable and resizable for
     * potentially thousands of pills is the heaviest task).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onPillEntered: function (ev) {
        var $pill = $(ev.currentTarget);

        this._setResizable($pill);
        if (!this.isTotal && !this.options.disableDragdrop) {
            this._setDraggable($pill);
        }
        if (!this.isGroup && !config.device.isMobile) {
            this._bindPillPopover(ev.target);
        }
    },
    /**
     * Toggle Collapse/Expand rows when user click in gantt row sidebar
     *
     * @private
     */
    _onRowSidebarClicked: function () {
        if (this.isGroup & !this.isTotal) {
            if (this.isOpen) {
                this.trigger_up('collapse_row', {rowId: this.rowId});
            } else {
                this.trigger_up('expand_row', {rowId: this.rowId});
            }
        }
    },
});

return GanttRow;

});

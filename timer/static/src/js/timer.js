odoo.define('timer.timer', function (require) {
"use strict";

// TODO: [XBO] remove this file when the form view in legacy will be no longer used.
var fieldRegistry = require('web.field_registry');
var AbstractField = require('web.AbstractField');
var Timer = require('timer.Timer');

var TimerFieldWidget = AbstractField.extend({

    /**
     * @override
     * @private
     */
    isSet: function () {
        return true;
    },
    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);
        this._startTimeCounter();
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        clearInterval(this.timer);
    },
    /**
     * @private
     */
    _startTimeCounter: async function () {
        if (this.record.data.timer_start) {
            const serverTime = this.record.data.timer_pause || await this._getServerTime();
            this.timeOffset = moment.duration(moment.utc(serverTime).diff(moment()));
            this.time = Timer.createTimer(0, this.record.data.timer_start, serverTime);
            this.$el.text(this.time.toString());
            this.timer = setInterval(() => {
                if (this.record.data.timer_pause) {
                    clearInterval(this.timer);
                } else {
                    this._updateTimer();
                }
            }, 1000);
        } else if (!this.record.data.timer_pause){
            clearInterval(this.timer);
        }
    },
    /**
     * @private
     */
    _updateTimer() {
        const currentTime = moment().add(this.timeOffset);
        const timeElapsed = moment.duration(currentTime.diff(moment.utc(this.record.data.timer_start)));
        this.time.addSeconds(timeElapsed.asSeconds() - this.time.convertToSeconds());
        this.$el.text(this.time.toString());
    },
    _getServerTime: function () {
        return this._rpc({
            model: 'timer.timer',
            method: 'get_server_time',
            args: []
        });
    }
});

fieldRegistry.add('timer_start_field', TimerFieldWidget);

});

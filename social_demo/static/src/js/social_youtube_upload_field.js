odoo.define('social_demo.youtube_upload_field', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;
var YoutubeUploadField = require('social_youtube.youtube_upload_field');

YoutubeUploadField.include({
    /**
     * When the user selects a file, as we are in demo mode, the video will not be uploaded.
     * Display a toaster to the user to inform them cannot upload video in demo mode.
     *
     * @param {Event} e
     * @private
     * @override
     */
    _onFileChanged: async function (e) {
        this.displayNotification({
            type: 'info',
            message: _t('You cannot upload videos in demo mode.'),
            sticky: false,
        });
    }
});

});

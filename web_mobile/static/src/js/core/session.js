odoo.define('web_mobile.Session', function (require) {
"use strict";

const core = require('web.core');
const Session = require('web.Session');

const mobile = require('web_mobile.core');

const DEFAULT_AVATAR_SIZE = 128;

/*
    Android webview not supporting post download and odoo is using post method to download
    so here override get_file of session and passed all data to native mobile downloader
    ISSUE: https://code.google.com/p/android/issues/detail?id=1780
*/

Session.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get_file: function (options) {
        if (mobile.methods.downloadFile) {
            if (core.csrf_token) {
                options.csrf_token = core.csrf_token;
            }
            mobile.methods.downloadFile(options);
            // There is no need to wait downloadFile because we delegate this to
            // Download Manager Service where error handling will be handled correclty.
            // On our side, we do not want to block the UI and consider the request
            // as success.
            if (options.success) { options.success(); }
            if (options.complete) { options.complete(); }
            return true;
        } else {
            return this._super.apply(this, arguments);
        }
    },

    /**
     * Update the user's account details on the mobile app
     *
     * @returns {Promise}
     */
    async updateAccountOnMobileDevice() {
        if (!mobile.methods.updateAccount) {
            return;
        }
        const base64Avatar = await this.fetchAvatar();
        return mobile.methods.updateAccount({
            avatar: base64Avatar.substring(base64Avatar.indexOf(',') + 1),
            name: this.name,
            username: this.username,
        });
    },

    /**
     * Fetch current user's avatar as PNG image
     *
     * @returns {Promise} resolved with the dataURL, or rejected if the file is
     *  empty or if an error occurs.
     */
    fetchAvatar() {
        const url = this.url('/web/image', {
            model: 'res.users',
            field: 'image_medium',
            id: this.uid,
        });
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            canvas.width = DEFAULT_AVATAR_SIZE;
            canvas.height = DEFAULT_AVATAR_SIZE;
            const context = canvas.getContext('2d');
            const image = new Image();
            image.addEventListener('load', () => {
                context.drawImage(image, 0, 0, DEFAULT_AVATAR_SIZE, DEFAULT_AVATAR_SIZE);
                resolve(canvas.toDataURL('image/png'));
            });
            image.addEventListener('error', reject);
            image.src = url;
        });
    },
});

});

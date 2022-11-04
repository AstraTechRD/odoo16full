/** @odoo-module */

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function base64ToUtf8(str) {
    // Going backwards: from bytestream, to percent-encoding, to original string.
    return decodeURIComponent(
        atob(str)
            .split("")
            .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
            .join("")
    );
}

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function utf8ToBase64(str) {
    // first we use encodeURIComponent to get percent-encoded UTF-8,
    // then we convert the percent encodings into raw bytes which
    // can be fed into btoa.
    return btoa(
        encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function toSolidBytes(match, p1) {
            return String.fromCharCode("0x" + p1);
        })
    );
}

/**
 * Encode a json to a base64 string
 * @param {object} json
 */
export function jsonToBase64(json) {
    return utf8ToBase64(JSON.stringify(json));
}

/**
 * Decode a base64 encoded json
 * @param {string} string
 */
export function base64ToJson(string) {
    return JSON.parse(base64ToUtf8(string));
}

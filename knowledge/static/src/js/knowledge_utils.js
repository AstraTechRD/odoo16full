/** @odoo-module **/

/**
 * Set an intersection observer on the given element. This function will ensure
 * that the given callback function will be called at most once when the given
 * element becomes visible on screen. This function can be used to load
 * components lazily (see: 'EmbeddedViewBehavior').
 * @param {HTMLElement} element
 * @param {Function} callback
 * @returns {IntersectionObserver}
 */
export function setIntersectionObserver (element, callback) {
    const options = {
        root: null,
        rootMargin: '0px'
    };
    const observer = new window.IntersectionObserver(entries => {
        const entry = entries[0];
        if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            callback();
        }
    }, options);
    observer.observe(element);
    return observer;
}

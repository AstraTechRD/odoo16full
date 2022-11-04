odoo.define('payment_sepa_direct_debit.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const sepaSignatureForm = require('payment_sepa_direct_debit.signature_form');

    const _t = core._t;

    const sepaDirectDebitMixin = {

        /**
         * Prepare the inline form of SEPA for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the selected payment option's provider
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (code, paymentOptionId, flow) {
            if (code !== 'sepa_direct_debit') {
                return this._super(...arguments);
            }

            if (flow === 'token') {
                return Promise.resolve(); // Don't show the form for tokens
            }
            // Although payments with SEPA are always performed as "online payments by token", we
            // set the flow to 'online' here so that it is not misinterpreted as a payment from an
            // existing mandate. The flow is later communicated to the controller as 'token'.
            this._setPaymentFlow('direct');

            // Configure the form
            this._resetSepaForm();
            return this._rpc({
                route: '/payment/sepa_direct_debit/form_configuration',
                params: {
                    'provider_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                },
            }).then(formConfiguration => {
                // Update the form with the partner information
                if (formConfiguration.partner_name && formConfiguration.partner_email) {
                    document.getElementById(`o_sdd_signature_config_${paymentOptionId}`)
                        .setAttribute('data-name', formConfiguration.partner_name);
                    document.getElementById(`o_sdd_partner_email_${paymentOptionId}`)
                        .innerText = formConfiguration.partner_email;
                }
                // Show the phone number input if enabled on the provider
                if (formConfiguration.sms_verification_required) {
                    this.sdd_sms_verification_required = true;
                    this._setupInputContainer(
                        document.getElementById(`o_sdd_phone_div_${paymentOptionId}`)
                    );
                    this._setupInputContainer(
                        document.getElementById(`o_sdd_verification_code_div_${paymentOptionId}`)
                    );
                    document.getElementById(`o_sdd_sms_button_${paymentOptionId}`).addEventListener(
                        'click', () => {
                            this._sendVerificationSms(paymentOptionId, parseInt(
                                this.txContext.partnerId
                            ));
                        }
                    );
                }
                // Show the signature form if required on the provider
                if (formConfiguration.signature_required) {
                    this.sdd_signature_required = true;
                    this._setupSignatureForm(paymentOptionId);
                }
            });
        },

        /**
         * Create a token and use it as payment option to process the payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the payment option provider
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (code, paymentOptionId, flow) {
            if (code !== 'sepa_direct_debit' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }

            // Retrieve and store inputs
            const ibanInput = document.getElementById(`o_sdd_iban_${paymentOptionId}`);
            const phoneInput = document.getElementById(`o_sdd_phone_${paymentOptionId}`);
            const codeInput = document.getElementById(`o_sdd_verification_code_${paymentOptionId}`);
            const signerInput = document.getElementById(`o_sdd_signature_form_${paymentOptionId}`)
                .querySelector('input[name="signer"]');

            // Check that all required inputs are filled at this step
            if (
                !ibanInput.reportValidity()
                || (this.sdd_sms_verification_required && !phoneInput.reportValidity())
                || (this.sdd_sms_verification_required && !codeInput.reportValidity())
                || (this.sdd_signature_required && signerInput && !signerInput.reportValidity())
            ) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve(); // Let the browser request to fill out required fields
            }

            // Extract the signature from the signature widget if the option is enabled
            let signature = undefined;
            if (this.sdd_signature_required && signerInput) {
                const signValues = this.signatureWidget._getValues();
                if (signValues) {
                    signature = signValues.signature;
                }
            }

            // Create the token to use for the payment
            return this._rpc({
                route: '/payment/sepa_direct_debit/create_token',
                params: {
                    'provider_id': paymentOptionId,
                    'partner_id': parseInt(this.txContext.partnerId),
                    'iban': ibanInput.value,
                    'mandate_id': this.mandate_id,
                    'phone': phoneInput.value,
                    'verification_code': codeInput.value,
                    // If the submit button was hit before that the signature widget was loaded, the
                    // input will be null. Pass undefined to let the server raise an error.
                    'signer': this.sdd_signature_required && signerInput
                        ? signerInput.value : undefined,
                    'signature': signature,
                },
            }).then(tokenId => {
                // Now that the token is created, use it as a payment option in the generic flow
                return this._processPayment(code, tokenId, 'token');
            }).guardedCatch((error) => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to process your payment."),
                    error.message.data.message,
                );
            });
        },

        /**
         * Clear the stored mandate id and removes the signature form.
         *
         * @private
         * @return {undefined}
         */
        _resetSepaForm: function () {
            this.mandate_id = undefined;
            if (this.signatureWidget) {
                this.signatureWidget.destroy();
            }
        },

        /**
         * Send a verification code by SMS to the provider phone number
         *
         * @private
         * @param {number} providerId - The id of the selected payment provider
         * @param {number} partnerId - The id of the partner
         * @return {Promise}
         */
        _sendVerificationSms: function (providerId, partnerId) {
            this._hideError(); // Remove any previous error

            // Retrieve and store inputs
            const ibanInput = document.getElementById(`o_sdd_iban_${providerId}`);
            const phoneInput = document.getElementById(`o_sdd_phone_${providerId}`);
            const codeInput = document.getElementById(`o_sdd_verification_code_${providerId}`);

            // Check that all required inputs are filled at this step
            if (!ibanInput.reportValidity() || !phoneInput.reportValidity()) {
                return Promise.resolve(); // Let the browser request to fill out required fields
            }

            // Disable the button to avoid spamming
            const sendSmsButton = document.getElementById(`o_sdd_sms_button_${providerId}`);
            sendSmsButton.setAttribute('disabled', true);

            // Fetch the mandate to verify. It is needed as it stores the verification code.
            return this._rpc({
                route: '/payment/sepa_direct_debit/get_mandate',
                params: {
                    'provider_id': providerId,
                    'partner_id': partnerId,
                    'iban': ibanInput.value,
                    'phone': phoneInput.value,
                },
            }).then(mandateId => {
                this.mandate_id = mandateId;
                // Send the verification code by SMS
                return this._rpc({
                    route: '/payment/sepa_direct_debit/send_verification_sms',
                    params: {
                        provider_id: providerId,
                        mandate_id: mandateId,
                        phone: phoneInput.value,
                    }
                });
            }).then(() => {
                // Enable the validation code field
                codeInput.removeAttribute('disabled');

                // Update the button to show the SMS has been sent.
                sendSmsButton.innerText = "";
                const sendSmsButtonIcon = document.createElement('i');
                sendSmsButtonIcon.classList.add('fa', 'fa-check', 'pe-1');
                sendSmsButton.appendChild(sendSmsButtonIcon);
                const sendSmsButtonText = document.createTextNode(_t("SMS Sent"));
                sendSmsButton.appendChild(sendSmsButtonText);

                // Show the button again after a few moments to allow sending a new SMS
                setTimeout(() => {
                    sendSmsButton.removeAttribute('disabled');
                    sendSmsButton.innerText = _t("Re-send SMS");
                    sendSmsButtonIcon.remove();
                    sendSmsButtonText.remove();
                }, 15000);
            }).guardedCatch(error => {
                error.event.preventDefault();
                sendSmsButton.removeAttribute('disabled');
                this._displayError(
                    _t("Server Error"),
                    _t("Could not send the verification code."),
                    error.message.data.message
                );
            });
        },

        /**
         * Show the container and make the input required.
         *
         * @private
         * @param {HTMLElement} inputContainer - The element containing the inputs to show.
         * @return {undefined}
         */
        _setupInputContainer: function (inputContainer) {
            inputContainer.querySelector('input').required = true;
            inputContainer.classList.remove('d-none');
        },

        /**
         * Show the signature form and attach the signature widget
         *
         * @private
         * @param {number} providerId - The id of the selected payment provider
         * @return {undefined}
         */
        _setupSignatureForm: function (providerId) {
            const signatureForm = document.getElementById(`o_sdd_signature_form_${providerId}`);
            this._setupInputContainer(signatureForm);
            const signatureConfig = document.getElementById(`o_sdd_signature_config_${providerId}`);
            this.signatureWidget = new sepaSignatureForm(this, {
                mode: 'draw',
                nameAndSignatureOptions: signatureConfig.dataset
            });
            this.signatureWidget.insertAfter(signatureConfig);
        },

    };

    checkoutForm.include(sepaDirectDebitMixin);
    manageForm.include(sepaDirectDebitMixin);
});

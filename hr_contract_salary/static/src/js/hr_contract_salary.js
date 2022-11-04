odoo.define('hr_contract_salary', function (require) {
"use strict";

const concurrency = require('web.concurrency');
const publicWidget = require('web.public.widget');
const utils = require('web.utils');
const {qweb, _t} = require('web.core');

publicWidget.registry.SalaryPackageWidget = publicWidget.Widget.extend({
    selector: '#hr_cs_form',
    events: {
        "change .advantage_input": "onchangeAdvantage",
        "change input.folded": "onchangeFolded",
        "change .personal_info": "onchangePersonalInfo",
        "click #hr_cs_submit": "submitSalaryPackage",
        "click a[name='recompute']": "recompute",
        "click button[name='toggle_personal_information']": "togglePersonalInformation",
        "change input.bg-danger": "checkFormValidity",
        "change div.invalid_radio": "checkFormValidity",
        "change input.document": "onchangeDocument",
        "input input[type='range']": "onchangeSlider",
        "change select[name='country_id']": "onchangeCountry",
        "keydown input[type='number']": "onkeydownInput",
    },

    init(parent, options) {
        this._super(parent);
        this.dp = new concurrency.DropPrevious();
        $('body').attr('id', 'hr_contract_salary');
        $("#hr_contract_salary select").select2();

        $('b[role="presentation"]').hide();
        $('.select2-arrow').append('<i class="fa fa-chevron-down"></i>');
        this.updateGross = _.debounce(this.updateGross, 1000);
        this.initializeUnsetSliders();
        var whitelist = $("input[name='whitelist']").val();
        if (whitelist) {
            var whitelisted_fields = whitelist.split(',');
            $('input')
                .toArray()
                .forEach(input => {
                    if (!whitelisted_fields.includes(input.name)) {
                        $(input).attr("disabled", true);
                    }
                });
            $('select')
                .toArray()
                .forEach(select => {
                    if (!whitelisted_fields.includes(select.name)) {
                        $(select).attr("disabled", true);
                    }
                });
        }
        this.stateElements = $("select[name='state_id']").find('option');
        this.onchangeCountry();

        // When user use back button, unfold previously unfolded items.
        $('#hr_cs_configurator .hr_cs_control input.folded:checked').closest('div').find('.folded_content').removeClass('d-none')
    },

    willStart() {
        return Promise.all([
            this._super(),
            this.updateGross(),
        ]);
    },

    initializeUnsetSliders() {
        $("input[type='range']").toArray().forEach(input => {
            const inputName = input.name.replace('_slider', '');
            const valueInput = $("input[name='" + inputName + "']");
            if (!valueInput.val()) {
                $(input).val(0);
                valueInput.val(0);
            }
        });
    },

    getFileData(documentName) {
        const file = $("input[name='" + documentName + "']");
        return new Promise(async resolve => {
            if (file[0].files[0]) {
                const testString = await utils.getDataURLFromFile(file[0].files[0]);
                const regex = new RegExp(",(.{0,})", "g");
                const img_src = regex.exec(testString)[1];
                resolve(img_src);
            } else {
                resolve(false);
            }
        });
    },

    async getPersonalDocuments() {
        const documentNames = $("input[type='file']").toArray().map(input => ({
            name: input.name,
            appliesOn: $(input).attr('applies-on'),
        }));
        let documentSrcs = {
            'employee': {},
            'address': {},
            'bank_account': {}
        };
        const promises = documentNames.map(async ({name, appliesOn}) => {
            const docSrc = await this.getFileData(name)
            documentSrcs[appliesOn][name] = docSrc;
        });
        await Promise.all(promises);
        return documentSrcs;
    },

    getAdvantages() {
        const advantages = {
            'contract': {},
            'employee': {},
            'address': {},
            'bank_account': {},
        };
        advantages.employee.job_title = $("input[name='job_title']").val();
        advantages.employee.employee_job_id = $("input[name='employee_job_id']").val();
        advantages.employee.department_id = $("input[name='department_id']").val();
        $('input')
            .toArray()
            .filter(input => input.hasAttribute('applies-on'))
            .filter(input => input.type !== 'file')
            .forEach(input => {
                const appliesOn = $(input).attr('applies-on');
                if (input.type === 'checkbox') {
                    advantages[appliesOn][input.name] = input.checked;
                } else if (input.type === 'radio' && input.checked) {
                    advantages[appliesOn][input.name] = $(input).data('value');
                } else if (input.type !== 'hidden' && input.type !== 'radio') {
                    advantages[appliesOn][input.name] = input.value;
                }
            });
        $('textarea')
            .toArray()
            .filter(area => area.hasAttribute('applies-on'))
            .forEach(area => {
                const appliesOn = $(area).attr('applies-on');
                advantages[appliesOn][area.name] = area.value;
            });
        $('select.advantage_input,select.personal_info').toArray().forEach(select => {
            const appliesOn = $(select).attr('applies-on');
            advantages[appliesOn][select.name] = $(select).val();
        });
        return advantages;
    },

    updateGrossToNetModal(data) {
        const resumeSidebar = $(qweb.render('hr_contract_salary.salary_package_resume', {
            'lines': data.resume_lines_mapped,
            'categories': data.resume_categories,
        }));
        this.$("div[name='salary_package_resume']").html(resumeSidebar);
        $("input[name='wage_with_holidays']").val(data['wage_with_holidays']);
        $("div[name='net']").removeClass('d-none').hide().slideDown( "slow" );
        $("input[name='NET']").removeClass('o_outdated');
    },

    onchangeFoldedResetInteger(advantageField) {
        return true;
    },

    onchangeFolded(event) {
        const foldedContent = $(event.target.parentElement.parentElement).find('.folded_content');
        const checked = event.target.checked;
        if (!checked) {
            $(foldedContent).find('input').toArray().forEach(input => {
                if (input.type == 'number' && this.onchangeFoldedResetInteger(input.name)) {
                    $(input).val(0);
                    $(input).trigger('change');
                }
            });
        } else {
            $(foldedContent).find('select').trigger('change');
        }
        checked ? $(foldedContent).removeClass('d-none') : $(foldedContent).addClass('d-none');
    },

    onchangeSlider(event) {
        let advantageField = event.target.name.replace("_slider", "");;
        $("input[name='" + advantageField + "']").val(event.target.value);
    },

    onchangeCountry(event) {
        const stateElement = $("select[name='state_id']");
        let countryID = parseInt($("select[name='country_id'][applies-on='address']").val());
        let enableState = true;
        stateElement.select2('val', '');
        stateElement.find('option').remove();
        stateElement.append(this.stateElements);
        stateElement.find('option').toArray().forEach(option => {
            let $option = $(option);
            let stateCountryID = $option.data('additional-info');
            if (countryID === stateCountryID) {
                enableState = false;
            } else {
                $option.remove();
            }
        });
        stateElement.attr('disabled', enableState);
    },

    onkeydownInput(event) {
        const disallowedKeys = {
            69: "KEY_E",
            109: "KEY_MINUS_KEYPAD",
            110: "KEY_DOT_KEYPAD",
            189: "KEY_MINUS",
            190: "KEY_DOT"
        };
        // Only allow numbers to be written in the input fields with type="number"
        return !(event.keyCode in disallowedKeys);
    },

    _isInvalidInput() {
        let isInvalidInput;
        $('input[data-field-type=integer]').toArray().forEach(input => {
            if (input.value && !Number.isInteger(parseFloat(input.value))) {
                isInvalidInput = true;
                if (!input.classList.contains('border-danger')) {
                    $("<div class='alert alert-danger alert-dismissable fade show'>")
                        .text(_t('Not a valid input in integer field'))
                        .appendTo($("button#hr_cs_submit").parent());
                    input.classList.toggle('border-danger', isInvalidInput);
                    $(".alert").delay(4000).slideUp(200, function () {
                        $(this).alert('close');
                    });
                }
            } else if(input.classList.contains('border-danger')) {
                input.classList.remove('border-danger');
            }
        });
        return isInvalidInput;
    },

    async onchangeAdvantage(event) {
        // Check that https://github.com/odoo/enterprise/commit/e4fdb4df1d0d6aa5e8880ce1b4cc289a075479fd#diff-aa5bcb2caed35c99a7bd3e018a104342 is still valid
        // Will check when the user has entered a floating value in the integer field
        if (this._isInvalidInput()) {
            return false;
        }
        // Prevent negative value for number inputs
        if (event.target.type === 'number' && parseFloat(event.target.value) < 0) {
            $(event.target).val(0);
        }
        let advantageField = event.target.name;
        if (advantageField.includes('_slider')) {
            advantageField = advantageField.replace("_slider", "");
        } else if (advantageField.includes('_manual')) {
            advantageField = advantageField.replace("_manual", "");
        } else if (advantageField.includes('_radio')) {
            advantageField = advantageField.replace("_radio", "");
        } else if (advantageField.includes('select_')) {
            advantageField = advantageField.replace("select_", "");
        }
        const requested_documents = $(event.target).data('requested_documents');
        if (requested_documents) {
            let hide;
            if (event.target.type === 'number') {
                hide = event.target.value === "0" || event.target.value === "";
            } else if (event.target.type === 'checkbox') {
                hide = !event.target.checked;
            } else if (event.target.type === 'radio') {
                hide = $(event.target.parentElement).find('.hr_cs_control_no').length;
            }
            requested_documents.split(',').forEach(requested_document => {
                const document_div = $("div[name='" + requested_document + "']");
                hide ? document_div.addClass('d-none') : document_div.removeClass('d-none');
            });
        }
        let newValue;
        if (event.target.type === 'radio') {
            const target = $("input[name='" + event.target.name + "']").toArray().find(elem => elem.checked);
            const description = $("span[name='description_" + advantageField + "']");
            $(target).hasClass('hide_description') ? description.addClass('d-none') : description.removeClass('d-none');
            newValue = $(target).data('value');
            if (newValue === 'No') {
                newValue = 0;
            }
        } else if (event.target.type === 'checkbox') {
            newValue = event.target.checked;
        } else {
            newValue = event.target.value;
        }
        if (event.target.type !== 'file') {
            const result = await this._rpc({
                route: '/salary_package/onchange_advantage',
                params: {
                    'advantage_field': advantageField,
                    'new_value': newValue,
                    'contract_id': parseInt($("input[name='contract']").val()),
                    'advantages': this.getAdvantages({includeFiles: false}),
                },
            });
            if (event.target.type !== 'select') {
                $("input[name='" + advantageField + "']").val(result.new_value);
            }
            $("span[name='description_" + advantageField + "']").html(result.description);
            if (result.extra_values) {
                _.each(result.extra_values, function(extra_value) {
                    $("input[name='" + extra_value[0] + "']").val(extra_value[1]);
                });
            }
            await this.updateGross();
        }
    },

    async onchangeDocument(input) {
        if (input.target.files) {
            const testString = await utils.getDataURLFromFile(input.target.files[0]);
            const regex = new RegExp(",(.{0,})", "g");
            const img_src = regex.exec(testString)[1];
            if (img_src.startsWith('JVBERi0')) {
                $('iframe#' + input.target.name + '_pdf').attr('src', testString);
                $('img#' + input.target.name + '_img').addClass('d-none');
                $('iframe#' + input.target.name + '_pdf').removeClass('d-none');
            } else {
                $('img#' + input.target.name + '_img').attr('src', testString);
                $('img#' + input.target.name + '_img').removeClass('d-none');
                $('iframe#' + input.target.name + '_pdf').addClass('d-none');
            }
        }
    },

    updateGross() {
        const self = this;
        $("div[name='net']").addClass('d-none');
        $("div[name='compute_net']").removeClass('d-none');
        $("a[name='details']").addClass('d-none');
        $("a[name='recompute']").removeClass('d-none');
        $("input[name='NET']").addClass('o_outdated');

        return this.dp.add(
            self._rpc({
                route: '/salary_package/update_salary',
                params: {
                    'contract_id': parseInt($("input[name='contract']").val()),
                    'advantages': self.getAdvantages({includeFiles: false}),
                },
            }).then(data => {
                $("input[name='wage']").val(data['new_gross']);
                $("a[name='recompute']").addClass('d-none');
                $("a[name='details']").removeClass('d-none');
                self.updateGrossToNetModal(data);
            })
        );
    },

    async onchangePersonalInfo(event) {
        let newValue;
        // YTI TODO: We could factorize the way we retrieve an input value
        if (event.target.type === 'radio') {
            const target = $("input[name='" + event.target.name + "']").toArray().filter(elem => elem.checked);
            newValue = $(target).data('value');
        } else if (event.target.type === 'checkbox') {
            newValue = event.target.checked;
        } else {
            newValue = event.target.value;
        }
        const data = await this._rpc({
            route: '/salary_package/onchange_personal_info',
            params: {
                'field': event.target.name,
                'value': newValue,
            },
        });
        if (!_.isEmpty(data)) {
            const childDiv = $("div[name='personal_info_child_group_" + data.field + "']")
            const childInputs = childDiv.find('input').toArray();
            if (data.hide_children) {
                childDiv.addClass('d-none');
                childInputs.forEach(input => $(input).removeAttr('required'));
            } else {
                childDiv.removeClass('d-none');
                childInputs.forEach(input => $(input).attr('required', ''));
            }
        }
    },

    recompute() {
        $("a[name='details']").removeClass('d-none');
        $("a[name='recompute']").addClass('d-none');
        $("input[name='NET']").removeClass('o_outdated');
    },

    checkFormValidity() {
        const requiredEmptyInput = $("input:required").toArray().find(input => input.value === '' && input.name !== '' && input.type !== 'checkbox');
        const requiredEmptySelect = $("select:required").toArray().find(select => $(select).val() === '');
        const email = $("input[name='email']").val();
        const atpos = email.indexOf("@");
        const dotpos = email.lastIndexOf(".");
        const invalid_email = atpos<1 || dotpos<atpos+2 || dotpos+2>=email.length;
        const isInvalidInput = this._isInvalidInput();
        let elementToScroll;
        let elementToScrollPosition;
        const isEmailEmpty = email === '';

        let requiredEmptyRadio;
        const radios = Array.prototype.slice.call(document.querySelectorAll('input[type=radio]:required'));
        const groups = Object.values(radios.reduce((result, el) => Object.assign(result, {[el.name]: (result[el.name] || []).concat(el)}), {}));
        groups.some((group, index) => {
            const $radio = group[0].parentElement.parentElement;
            if (!group.some(el => el.checked)) {
                requiredEmptyRadio = true;
                const $warning = document.createElement('div');
                $warning.classList = 'alert alert-danger alert-dismissable fade show';
                $warning.textContent = _t('Some required fields are not filled');
                document.querySelector("button#hr_cs_submit").parentElement.append($warning);
                $radio.classList.toggle('invalid_radio', requiredEmptyRadio);
                elementToScroll = $radio;
                elementToScrollPosition = $($radio).offset().top;
            } else if ($radio.classList.contains('invalid_radio')) {
                $radio.classList.toggle('invalid_radio');
            }
        });

        if(requiredEmptyInput || requiredEmptySelect) {
            $("<div class='alert alert-danger alert-dismissable fade show'>")
                .text(_t('Some required fields are not filled'))
                .appendTo($("button#hr_cs_submit").parent());
            $("input:required").toArray().forEach(input => {
                $(input).toggleClass('bg-danger', input.value === '');
                let inputPosition = $(input).offset().top;
                if ((!elementToScroll || inputPosition < elementToScrollPosition) && input.value === '') {
                    elementToScroll = $(input)[0];
                    elementToScrollPosition = $(input).offset().top;
                }
            });
            $("select:required").toArray().forEach(select =>  {
                const selectParent = $(select).parent().find('.select2-choice');
                selectParent.toggleClass('bg-danger', $(select).val() === '');
                let selectPosition = selectParent.offset().top;
                if ((!elementToScroll || selectPosition <= elementToScrollPosition) && $(select).val() === '') {
                    elementToScroll = selectParent[0];
                    elementToScrollPosition = selectParent.offset().top;
                }
            });
        }
        else{
            $("input:required").toArray().forEach(input => {
                $(input).removeClass('bg-danger');
            });
            $("select:required").toArray().forEach(select => {
                const selectParent = $(select).parent().find('.select2-choice');
                if ($(select).val() !== '') {
                    selectParent.removeClass('bg-danger');
                }
            });
        }
        if (invalid_email) {
            $("input[name='email']").addClass('bg-danger');
            if (!isEmailEmpty) {
                $("<div class='alert alert-danger alert-dismissable fade show'>")
                    .text(_t('Not a valid e-mail address'))
                    .appendTo($("button#hr_cs_submit").parent());
            }
            let emailPosition = $("input[name='email']").offset().top;
            if (!elementToScroll || emailPosition <= elementToScrollPosition) {
                elementToScroll = $("input[name='email']")[0];
            }
        }
        $(".alert").delay(4000).slideUp(200, function () {
            $(this).alert('close');
        });
        if (elementToScroll) {
            elementToScroll.scrollIntoView({block: 'center', behavior: 'smooth'});
        }
        return !invalid_email && !requiredEmptyInput && !requiredEmptySelect && !requiredEmptyRadio && !isInvalidInput;
    },

    async getFormInfo() {
        const personalDocuments = await this.getPersonalDocuments();
        let advantages = this.getAdvantages();
        advantages = {
            'employee': Object.assign(advantages.employee, personalDocuments.employee),
            'contract': Object.assign(advantages.contract, personalDocuments.contract),
            'address': Object.assign(advantages.address, personalDocuments.address),
            'bank_account': Object.assign(advantages.bank_account, personalDocuments.bank_account),
        }

        return {
            'contract_id': parseInt($("input[name='contract']").val()),
            'token': $("input[name='token']").val(),
            'advantages': advantages,
            'applicant_id': parseInt($("input[name='applicant_id']").val()) || false,
            'employee_contract_id': parseInt($("input[name='employee_contract_id']").val()) || false,
            'original_link': $("input[name='original_link']").val()
        };
    },

    async submitSalaryPackage(event) {
        if (this.checkFormValidity()) {
            const formInfo = await this.getFormInfo();
            const data = await this._rpc({
                    route: '/salary_package/submit',
                    params: formInfo,
                });
            if (data['error']) {
                $("button#hr_cs_submit").parent().append("<div class='alert alert-danger alert-dismissable fade show'>" + data['error_msg'] + "</div>");
            } else {
                document.location.pathname = '/sign/document/' + data['request_id'] + '/' + data['token'];
            }
        }
    },

    togglePersonalInformation() {
        $("button[name='toggle_personal_information']").toggleClass('d-none');
        $("div[name='personal_info']").toggle(500);
        $("div[name='personal_info_withholding_taxes']").toggle(500);
    },
});

return publicWidget.registry.SalaryPackageWidget;
});

/* jshint -W065 */
define([
    'jquery',
    'underscore',
    'underscore.string',
    'utils/utils',
    'utils/credit_card',
    'utils/key_codes',
    'js-cookie'
],
    function($,
              _,
              _s,
              Utils,
              CreditCardUtils,
              KeyCodes,
              Cookies) {
        'use strict';

        var BasketPage = {
            hideVoucherForm: function() {
                $('#voucher_form_container').hide();
                $('#voucher_form_link').show();
            },

            onFail: function() {
                var message = gettext('Problem occurred during checkout. Please contact support.');
                $('#messages').html(_s.sprintf('<div class="alert alert-error">%s</div>', message));
            },

            onSuccess: function(data) {
                var $form = $('<form>', {
                    class: 'hidden',
                    action: data.payment_page_url,
                    method: 'POST',
                    'accept-method': 'UTF-8'
                });

                _.each(data.payment_form_data, function(value, key) {
                    $('<input>').attr({
                        type: 'hidden',
                        name: key,
                        value: value
                    }).appendTo($form);
                });

                $form.appendTo('body').submit();
            },

            checkoutPayment: function(data) {
                $.ajax({
                    url: '/api/v2/checkout/',
                    method: 'POST',
                    contentType: 'application/json; charset=utf-8',
                    dataType: 'json',
                    headers: {
                        'X-CSRFToken': Cookies.get('ecommerce_csrftoken')
                    },
                    data: JSON.stringify(data),
                    success: BasketPage.onSuccess,
                    error: BasketPage.onFail
                });
            },

            appendCardValidationErrorMsg: function(event, field, msg) {
                event.preventDefault();
                field.find('~.help-block').append('<span>' + msg + '</span>');
                field.focus();
                $('.add-new-card-cont').attr('data-has-error', true);
            },

            appendCardHolderValidationErrorMsg_custom: function(field, msg) {
                field.find('~.help-block').append(
                    '<span>' + msg + '</span>'
                );
            },

            appendCardHolderValidationErrorMsg: function(field, msg) {
                field.parentsUntil('form-item').find('~.help-block').append(
                    '<span>' + msg + '</span>'
                );
            },

            cardHolderInfoValidation: function(event) {
                var requiredFields = [
                        'input[name=full_name]',
                        'input[name=city]',
                        'input[name=organization]',
                        'select[name=country]'
                    ],
                    countriesWithRequiredStateAndPostalCodeValues = ['US', 'CA'],
                    experiments = window.experimentVariables || {};
                // Only require address and state if we are not in the hide location fields variation of this experiment
                // https://openedx.atlassian.net/browse/LEARNER-2355
                if (!(experiments && experiments.hide_location_fields)) {
                    requiredFields.push('input[name=address_line1]');
                    if (countriesWithRequiredStateAndPostalCodeValues.indexOf($('select[name=country]').val()) > -1) {
                        requiredFields.push('select[name=state]');
                        requiredFields.push('input[name=postal_code]');
                    }
                }

                _.each(requiredFields, function(field) {
                    if ($(field).val() === '') {
                        event.preventDefault();
                        BasketPage.appendCardHolderValidationErrorMsg($(field), gettext('This field is required'));
                        $('.payment-form').attr('data-has-error', true);
                    }
                });

                // Focus the first element that has an error message.
                $('.help-block > span')
                .first().parentsUntil('fieldset').last()
                .find('input')
                .focus();
            },

            cardHolderInfoValidation_custom: function(event, form) {
                var requiredFields = null;
                if(form == 'edit-address'){
                requiredFields = [
                    'input[name=edit_fname]',
                    'input[name=edit_address1]',
                    'input[name=edit_city]',
                    'select[name=edit_country]'
                    ];
                    var countriesWithRequiredStateAndPostalCodeValues = ['US', 'CA'];
                    var experiments = window.experimentVariables || {};
                }
                if(form == 'add-address'){
                    requiredFields = [
                        'input[name=fname]',
                        'input[name=address1]',
                        'input[name=city]',
                        'select[name=country]'
                        ];
                        var countriesWithRequiredStateAndPostalCodeValues = ['US', 'CA'];
                        var experiments = window.experimentVariables || {};
                }
 
                // Only require address and state if we are not in the hide location fields variation of this experiment
                // https://openedx.atlassian.net/browse/LEARNER-2355
                if (!(experiments && experiments.hide_location_fields)) {
                    requiredFields.push('input[name=address_line1]');
                    if (countriesWithRequiredStateAndPostalCodeValues.indexOf($('select[name=country]').val()) > -1) {
                        requiredFields.push('select[name=state]');
                        requiredFields.push('input[name=postal_code]');
                    }
                }

                _.each(requiredFields, function(field) {
                    if ($(field).val() === '') {
                        event.preventDefault();
                        BasketPage.appendCardHolderValidationErrorMsg_custom($(field), gettext('This field is required'));
                        $('.add-address-form').attr('data-has-error', true);
                    }
                });

                // Focus the first element that has an error message.
                $('.help-block > span')
                .first().parentsUntil('fieldset').last()
                .find('input')
            },


            isCardTypeSupported: function(cardType) {
                return $.inArray(cardType, ['amex', 'discover', 'mastercard', 'visa']) > -1;
            },

            cardInfoValidation: function(event) {
                var cardType,
                    // We are adding 1 here because month in js style date-time starts with 0
                    // i.e. 0 for JAN, 1 for FEB etc. However, credit card expiry months start with 1
                    // i.e 1 for JAN, 2 for FEB etc.
                    currentMonth = new Date().getMonth() + 1,
                    currentYear = new Date().getFullYear(),
                    $number = $('#cardNumber'),
                    $cvn = $('#cvc'),
                    $expMonth = $('#month_dropdown'),
                    $expYear = $('#year_dropdown'),
                    cardNumber = $number.val(),
                    cvnNumber = $cvn.val(),
                    cardExpiryMonth = $expMonth.val(),
                    cardExpiryYear = $expYear.val()

                    cardType = CreditCardUtils.getCreditCardType(cardNumber);


                // Number.isInteger() is not compatible with IE11, so polyfill is required. Polyfill taken from:
                // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/isInteger
                Number.isInteger = Number.isInteger || function(value) {
                    return typeof value === 'number' &&
                        isFinite(value) &&
                        Math.floor(value) === value;
                };

                if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && !CreditCardUtils.isValidCardNumber(cardNumber)) {
                    BasketPage.appendCardValidationErrorMsg(event, $number, gettext('Invalid card number'));
                } else if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && (_.isUndefined(cardType) || !BasketPage.isCardTypeSupported(cardType.name))) {
                    BasketPage.appendCardValidationErrorMsg(event, $number, gettext('Unsupported card type'));
                } else if (cvnNumber.length !== cardType.cvnLength || !Number.isInteger(Number(cvnNumber))) {
                    BasketPage.appendCardValidationErrorMsg(event, $cvn, gettext('Invalid security number'));
                }

                if (!Number.isInteger(Number(cardExpiryMonth)) ||
                    Number(cardExpiryMonth) > 12 || Number(cardExpiryMonth) < 1) {
                    BasketPage.appendCardValidationErrorMsg(event, $expMonth, gettext('Invalid month'));
                } else if (!Number.isInteger(Number(cardExpiryYear)) || Number(cardExpiryYear) < currentYear) {
                    BasketPage.appendCardValidationErrorMsg(event, $expYear, gettext('Invalid year'));
                } else if (Number(cardExpiryMonth) < currentMonth && Number(cardExpiryYear) === currentYear) {
                    BasketPage.appendCardValidationErrorMsg(event, $expMonth, gettext('Card expired'));
                }
            },

            cardInfoValidation_custom: function(event) {
                var cardType,
                    // We are adding 1 here because month in js style date-time starts with 0
                    // i.e. 0 for JAN, 1 for FEB etc. However, credit card expiry months start with 1
                    // i.e 1 for JAN, 2 for FEB etc.
                    currentMonth = new Date().getMonth() + 1,
                    currentYear = new Date().getFullYear(),
                    $number = $('#cardNumber'),
                    $cvn = $('#cvc'),
                    $expMonth = $('#month_dropdown'),
                    $expYear = $('#year_dropdown'),
                    cardNumber = $number.val(),
                    cvnNumber = $cvn.val(),
                    cardExpiryMonth = $expMonth.val(),
                    cardExpiryYear = $expYear.val();
  
                cardType = CreditCardUtils.getCreditCardType(cardNumber);
  
  
                // Number.isInteger() is not compatible with IE11, so polyfill is required. Polyfill taken from:
                // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/isInteger
                Number.isInteger = Number.isInteger || function(value) {
                    return typeof value === 'number' &&
                        isFinite(value) &&
                        Math.floor(value) === value;
                };
  
                if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && !CreditCardUtils.isValidCardNumber(cardNumber)) {
                    BasketPage.appendCardValidationErrorMsg(event, $number, gettext('Invalid card number'));
                } else if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && (_.isUndefined(cardType) || !BasketPage.isCardTypeSupported(cardType.name))) {
                    BasketPage.appendCardValidationErrorMsg(event, $number, gettext('Unsupported card type'));
                } else if (cvnNumber.length !== cardType.cvnLength || !Number.isInteger(Number(cvnNumber))) {
                    BasketPage.appendCardValidationErrorMsg(event, $cvn, gettext('Invalid security number'));
                }
  
                if (!Number.isInteger(Number(cardExpiryMonth)) ||
                    Number(cardExpiryMonth) > 12 || Number(cardExpiryMonth) < 1) {
                    BasketPage.appendCardValidationErrorMsg(event, $expMonth, gettext('Invalid month'));
                } else if (!Number.isInteger(Number(cardExpiryYear)) || Number(cardExpiryYear) < currentYear) {
                    BasketPage.appendCardValidationErrorMsg(event, $expYear, gettext('Invalid year'));
                } else if (Number(cardExpiryMonth) < currentMonth && Number(cardExpiryYear) === currentYear) {
                    BasketPage.appendCardValidationErrorMsg(event, $expMonth, gettext('Card expired'));
                }
            },

            showErrorState: function(e, msg) {
                e.preventDefault();
                $('#input-quantity-field').addClass('error-state');
                $('div#error-msg').text(gettext(msg));
            },

            validateQuantity: function(e) {
                var inputQuantity = $('#input-quantity-field').val();
                var quantity = isNaN(parseInt(inputQuantity, 10)) ? '' : parseInt(inputQuantity, 10);
                if (quantity === '') {
                    this.showErrorState(e, 'Please enter a quantity from 1 to 100.');
                } else if (quantity > 100) {
                    this.showErrorState(e, 'Quantity must be less than or equal to 100.');
                } else if (quantity < 1) {
                    this.showErrorState(e, 'Quantity must be greater than or equal to 1.');
                }
            },

            detectCreditCard: function() {
                var card,
                    $input = $('#card-number'),
                    cardNumber = $input.val().replace(/\s+/g, ''),
                    iconPath = '/static/images/credit_cards/';

                if (cardNumber.length > 12) {
                    card = CreditCardUtils.getCreditCardType(cardNumber);

                    if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && !CreditCardUtils.isValidCardNumber(cardNumber)) {
                        $('.card-type-icon').attr('src', '').addClass('hidden');
                        return;
                    }

                    if (typeof card !== 'undefined') {
                        $('.card-type-icon').attr(
                            'src',
                            iconPath + card.name + '.png'
                        ).removeClass('hidden');
                        $input.trigger('cardType:detected', {type: card.name});
                    } else {
                        $('.card-type-icon').attr('src', '').addClass('hidden');
                    }
                } else {
                    $('.card-type-icon').attr('src', '').addClass('hidden');
                }
            },
            detectCreditCard_custom: function() {
                var card,
                    $input = $('#cardNumber'),
                    cardNumber = $input.val().replace(/\s+/g, ''),
                    iconPath = '/static/images/credit_cards/';
  
                if (cardNumber.length > 12) {
                    card = CreditCardUtils.getCreditCardType(cardNumber);
  
                    if (!CreditCardUtils.savedCreditCardValidator(cardNumber) && !CreditCardUtils.isValidCardNumber(cardNumber)) {
                        $('.card-type-icon').attr('src', '').addClass('hidden');
                        return;
                    }
  
                    if (typeof card !== 'undefined') {
                        $('.card-type-icon').attr(
                            'src',
                            iconPath + card.name + '.png'
                        ).removeClass('hidden');
                        $input.trigger('cardType:detected', {type: card.name});
                    } else {
                        $('.card-type-icon').attr('src', '').addClass('hidden');
                    }
                } else {
                    $('.card-type-icon').attr('src', '').addClass('hidden');
                }
            },

            showVoucherForm: function() {
                $('#voucher_form_container').show();
                $('#voucher_form_link').hide();
                $('#id_code').focus();
            },

            showCvvTooltip: function() {
                $('#cvvtooltip').show();
                $('#card-cvn-help').attr({
                    'aria-haspopup': 'false',
                    'aria-expanded': 'true'
                });
            },

            hideCvvTooltip: function() {
                $('#cvvtooltip').hide();
                $('#card-cvn-help').attr({
                    'aria-haspopup': 'true',
                    'aria-expanded': 'false'
                });
            },

            toggleCvvTooltip: function() {
                var $cvnHelpButton = $('#card-cvn-help');
                $('#cvvtooltip').toggle();
                $cvnHelpButton.attr({
                    'aria-haspopup': $cvnHelpButton.attr('aria-haspopup') === 'true' ? 'false' : 'true',
                    'aria-expanded': $cvnHelpButton.attr('aria-expanded') === 'true' ? 'false' : 'true'
                });
            },

            isValidLocalCurrencyCookie: function(cookie) {
                return !!cookie && !!cookie.countryCode && !!cookie.symbol && !!cookie.rate && !!cookie.code;
            },

            addPriceDisclaimer: function() {
                var price = $('#basket-total').find('> .price').text(),
                    countryData = Cookies.getJSON('edx-price-l10n'),
                    disclaimerPrefix;

                // when the price value has a USD prefix, replace it with a $
                price = price.replace('USD', '$');
                disclaimerPrefix = '* This total contains an approximate conversion. You will be charged ';

                if (BasketPage.isValidLocalCurrencyCookie(countryData) && countryData.countryCode !== 'USA') {
                    $('<span>').attr('class', 'price-disclaimer')
                        .text(gettext(disclaimerPrefix) + price + ' USD.')
                        .appendTo('div[aria-labelledby="order-details-region"]');
                }
            },

            formatToLocalPrice: function(prefix, priceInUsd) {
                var countryData = Cookies.getJSON('edx-price-l10n'),
                    parsedPriceInUsd;

                // Default to USD when the exchange rate cookie doesn't exist
                if (BasketPage.isValidLocalCurrencyCookie(countryData) && countryData.countryCode !== 'USA') {
                    // assumes all formatted prices have a comma every three places
                    parsedPriceInUsd = parseFloat(priceInUsd.replace(',', ''));
                    return countryData.symbol + Math.round(parsedPriceInUsd * countryData.rate).toLocaleString() + ' '
                        + countryData.code + ' *';
                } else {
                    return prefix + priceInUsd;
                }
            },

            generateLocalPriceText: function(usdPriceText) {
                // Assumes price value is prefixed by $ or USD with optional sign followed by optional string
                var localPriceText = usdPriceText,
                    prefixMatch = localPriceText.match(/(\$|USD)?(([1-9][0-9]{0,2}(,[0-9]{3})*)|[0-9]+)?\.[0-9]{1,2}/),
                    entireMatch,
                    groupMatch,
                    startIndex,
                    priceValue;

                if (prefixMatch) {
                    entireMatch = prefixMatch[0];
                    groupMatch = prefixMatch[1];
                    startIndex = prefixMatch.index;
                    priceValue = localPriceText
                      .substring(startIndex + groupMatch.length, startIndex + entireMatch.length);

                    localPriceText = localPriceText
                        .replace(entireMatch, BasketPage.formatToLocalPrice(groupMatch, priceValue));
                }

                return localPriceText;
            },

            replaceElementText: function(element, text) {
                if (element.text() !== text) {
                    element.text(text);
                }
            },

            translateToLocalPrices: function() {
                var translatedItemPrices = [],
                    translatedVoucherPrices = [],
                    $prices = $('.price'),
                    $vouchers = $('.voucher');

                // Generate all local price text values
                $prices.each(function() {
                    translatedItemPrices.push(BasketPage.generateLocalPriceText($(this).text()));
                });

                $vouchers.each(function() {
                    translatedVoucherPrices.push(BasketPage.generateLocalPriceText($(this).text()));
                });

                // Replace local price text values
                if ($prices.length === translatedItemPrices.length
                    && $vouchers.length === translatedVoucherPrices.length) {
                    // Add price disclaimer after all translated values have been calculated
                    BasketPage.addPriceDisclaimer();

                    $prices.each(function(index, element) {
                        BasketPage.replaceElementText($(element), translatedItemPrices[index]);
                    });

                    $vouchers.each(function(index, element) {
                        BasketPage.replaceElementText($(element), translatedVoucherPrices[index]);
                    });
                }
            },

            onReady: function() {
                var $paymentButtons = $('.payment-buttons'),
                    basketId = $paymentButtons.data('basket-id');

                Utils.toogleMobileMenuClickEvent();

                $(document).keyup(function(e) {
                    switch (e.which) {
                    case KeyCodes.Escape:
                        BasketPage.hideCvvTooltip();
                        break;
                    case KeyCodes.Tab:
                        if ($('#card-cvn-help').is(':focus')) {
                            BasketPage.showCvvTooltip();
                        }
                        break;
                    default:
                        break;
                    }
                });

                $('#card-cvn-help').on('click touchstart', function(event) {
                    event.preventDefault();
                    BasketPage.toggleCvvTooltip();
                });

                $('#card-cvn-help').blur(BasketPage.hideCvvTooltip)
                    .hover(BasketPage.showCvvTooltip, BasketPage.hideCvvTooltip);

                $('#voucher_form_link').on('click', function(event) {
                    event.preventDefault();
                    BasketPage.showVoucherForm();
                });

                $('#voucher_form_cancel').on('click', function(event) {
                    event.preventDefault();
                    BasketPage.hideVoucherForm();
                });

                $('#voucher_form').on('submit', function() {
                    $('#apply-voucher-button').attr('disabled', true);
                    $('#payment-button').attr('disabled', true);
                    $('.payment-button[type=button]').attr('disabled', true);
                });

                $('select[name=country]').on('change', function() {
                    var country = $('select[name=country]').val(),
                        $inputDiv = $('#div_id_state .controls'),
                        states = {
                            US: {
                                Alabama: 'AL',
                                Alaska: 'AK',
                                American: 'AS',
                                Arizona: 'AZ',
                                Arkansas: 'AR',
                                'Armed Forces Americas': 'AA',
                                'Armed Forces Europe': 'AE',
                                'Armed Forces Pacific': 'AP',
                                California: 'CA',
                                Colorado: 'CO',
                                Connecticut: 'CT',
                                Delaware: 'DE',
                                'Dist. of Columbia': 'DC',
                                Florida: 'FL',
                                Georgia: 'GA',
                                Guam: 'GU',
                                Hawaii: 'HI',
                                Idaho: 'ID',
                                Illinois: 'IL',
                                Indiana: 'IN',
                                Iowa: 'IA',
                                Kansas: 'KS',
                                Kentucky: 'KY',
                                Louisiana: 'LA',
                                Maine: 'ME',
                                Maryland: 'MD',
                                'Marshall Islands': 'MH',
                                Massachusetts: 'MA',
                                Michigan: 'MI',
                                Micronesia: 'FM',
                                Minnesota: 'MN',
                                Mississippi: 'MS',
                                Missouri: 'MO',
                                Montana: 'MT',
                                Nebraska: 'NE',
                                Nevada: 'NV',
                                'New Hampshire': 'NH',
                                'New Jersey': 'NJ',
                                'New Mexico': 'NM',
                                'New York': 'NY',
                                'North Carolina': 'NC',
                                'North Dakota': 'ND',
                                'Northern Marianas': 'MP',
                                Ohio: 'OH',
                                Oklahoma: 'OK',
                                Oregon: 'OR',
                                Palau: 'PW',
                                Pennsylvania: 'PA',
                                'Puerto Rico': 'PR',
                                'Rhode Island': 'RI',
                                'South Carolina': 'SC',
                                'South Dakota': 'SD',
                                Tennessee: 'TN',
                                Texas: 'TX',
                                Utah: 'UT',
                                Vermont: 'VT',
                                Virginia: 'VA',
                                'Virgin Islands': 'VI',
                                Washington: 'WA',
                                'West Virginia': 'WV',
                                Wisconsin: 'WI',
                                Wyoming: 'WY'
                            },
                            CA: {
                                Alberta: 'AB',
                                'British Columbia': 'BC',
                                Manitoba: 'MB',
                                'New Brunswick': 'NB',
                                'Newfoundland and Labrador': 'NL',
                                'Northwest Territories': 'NT',
                                'Nova Scotia': 'NS',
                                Nunavut: 'NU',
                                Ontario: 'ON',
                                'Prince Edward Island': 'PE',
                                Quebec: 'QC',
                                Saskatchewan: 'SK',
                                Yukon: 'YT'
                            }
                        },
                        experiments = window.experimentVariables || {},
                        selectorRequired = 'aria-required="true" required',
                        stateSelector = '<select name="state" class="select form-control" id="id_state"';

                    if (country === 'US' || country === 'CA') {
                        $($inputDiv).empty();
                        // Only require state if we are not in the hide location fields variation of this experiment
                        // https://openedx.atlassian.net/browse/LEARNER-2355
                        stateSelector += !(experiments && experiments.hide_location_fields) ? selectorRequired : '';
                        stateSelector += '></select>';
                        $($inputDiv).append(stateSelector);
                        $('#id_state').append($('<option>', { value: '', text: gettext('<Choose state/province>') }));
                        $('#div_id_state').find('label').text(gettext('State/Province (required)'));

                        _.each(states[country], function(value, key) {
                            $('#id_state').append($('<option>', { value: value, text: key }));
                        });
                    } else {
                        $($inputDiv).empty();
                        $('#div_id_state').find('label').text('State/Province');
                        // In order to change the maxlength attribute, the same needs to be changed in the Django form.
                        $($inputDiv).append(
                            '<input class="textinput textInput form-control" id="id_state"' +
                            'maxlength="60" name="state" type="text">'
                        );
                    }
                });

                $('#cardNumber').on('input', function() {
                    BasketPage.detectCreditCard_custom();
                });

                $('#quantity-update').on('click', function(e) {
                    BasketPage.validateQuantity(e);
                });

                // $('#payment-button').click(function(e) {
                //     _.each($('.help-block'), function(errorMsg) {
                //         $(errorMsg).empty();  // Clear existing validation error messages.
                //     });
                //     $('.payment-form').attr('data-has-error', false);
                //     if ($('#card-number').val()) {
                //         BasketPage.detectCreditCard();
                //     }
                //     BasketPage.cardInfoValidation(e);
                //     BasketPage.cardHolderInfoValidation(e);
                // });

                $('#add_address_save_button').click(function(e) {
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                    $('.add-address-form').attr('data-has-error', false);
                    BasketPage.cardHolderInfoValidation_custom(e, 'add-address');
                    if ($('.add-address-form').attr('data-has-error') == 'false') {
                        $("#add_address_save_button").attr("disabled","true");
                        let csrf = $('#csrf-token').val();
                        var data = {
                            "first_name": document.getElementById("fname").value,
                            "address_line1": document.getElementById("address1").value,
                            "address_line2": document.getElementById("address2").value,
                            "address_city": document.getElementById("city").value,
                            "address_state": document.getElementById("state").value,
                            "address_postal_code": document.getElementById("zip").value,
                            "address_country": document.getElementById("country").value,
                            "is_default_for_billing": document.querySelector('input[name="add_radio"]:checked') ? true : false,
                        };

                        $.ajax({
                            url: '/basket/address-add-new/',
                            method: 'POST',
                            contentType: 'application/json; charset=utf-8',
                            dataType: 'json',
                            headers: {
                                'X-CSRFToken': csrf
                            },
                            data: JSON.stringify(data),
                            success: function(response) {
                                window.location.replace(window.location.protocol + "//" + window.location.host + "/basket/");
                            },
                            error: function(data) {
                                alert("Some error has occured");
                            },
                        });
                    }
                });
                $("#btn-save-card").click(function(e) {                    
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                    $('.add-new-card-cont').attr('data-has-error', false);
                    if ($('#cardNumber').val()) {
                        BasketPage.detectCreditCard_custom();
                    }
  
                    BasketPage.cardInfoValidation_custom(e);
                    if ($(".add-new-card-cont").attr('data-has-error') == "false") {
                      $("#btn-save-card").attr("disabled","true");                 
                      
                      let csrf = $('#csrf-token').val();
                  
                      var data_dictionary = {
                  
                          "number": $("#cardNumber").val(),
                  
                          "exp_month": $('#month_dropdown option:selected').text(),
                  
                          "exp_year": $('#year_dropdown option:selected').text(),
                  
                          "cvc": $("#cvc").val(),
                  
                          "is_default": $("#add_card_radio").is(":checked")
                  
                      }
                  
                      $.ajax({
                  
                          url: '/basket/card-add-source/',
                  
                          method: 'POST',
                  
                          contentType: 'application/json; charset=utf-8',
                  
                          dataType: 'json',
                  
                          headers: {
                  
                              'X-CSRFToken': csrf
                  
                          },
                  
                          data: JSON.stringify(data_dictionary),
                  
                          success: function(response) {
                  
                              if (response['status'] == 'Success')
                  
                              {
                  
                                  window.location.replace(window.location.protocol + "//" + window.location.host + "/basket/");
                  
                              } else
                  
                              {
                  
                                  alert('some error has occured')
                  
                              }
                  
                          },
                  
                          error: function(data) {
                  
                              alert('some error has occured')
                  
                          },
                  
                      });
                  
                  }
                  
                  });

                $('#edit_address_save_button').click(function(e) {
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                    $('.add-address-form').attr('data-has-error', false);
                    
                    BasketPage.cardHolderInfoValidation_custom(e, 'edit-address');
                    if ($('.add-address-form').attr('data-has-error') == 'false') {
                        $("#edit_address_save_button").attr("disabled","true");
                        let csrf = $('#csrf-token').val();
                        var data = {
                            "id": document.getElementById("edit_address_id").value,
                            "first_name": document.getElementById("edit_fname").value,
                            "address_line1": document.getElementById("edit_address1").value,
                            "address_line2": document.getElementById("edit_address2").value,
                            "address_city": document.getElementById("edit_city").value,
                            "address_state": document.getElementById("edit_state").value,
                            "address_postal_code": document.getElementById("edit_zip").value,
                            "address_country": document.getElementById("edit_country").value,
                            "is_default_for_billing": document.querySelector('input[name="edit_radio"]:checked') ? true : false,
                        };
                
                        $.ajax({
                            url: '/basket/address-edit/',
                            method: 'POST',
                            contentType: 'application/json; charset=utf-8',
                            dataType: 'json',
                            headers: {
                                'X-CSRFToken': csrf
                            },
                            data: JSON.stringify(data),
                            success: function(response){
                                window.location.replace(window.location.protocol + "//" + window.location.host + "/basket/");
                            },
                            error: function(data){ 
                                alert("Some error has occured");
                            },
                        }); 
                    }  
                });


                $('#add_new_address_button').click(function(e) {
                    $('#add-address-form').trigger("reset");
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                });

                $('.edit-address-btn').click(function(e) {
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                });


                $('#add_new_card_btn').click(function(e) {
                    $('#card-add').trigger("reset");
                    _.each($('.help-block'), function(errorMsg) {
                        $(errorMsg).empty();  // Clear existing validation error messages.
                    });
                });




                // NOTE: We only include buttons that have a data-processor-name attribute because we don't want to
                // go through the standard checkout process for some payment methods (e.g. Apple Pay).
                // $paymentButtons.find('.payment-button[data-processor-name]').click(function(e) {
                //     var $btn = $(e.target),
                //         deferred = new $.Deferred(),
                //         promise = deferred.promise(),
                //         paymentProcessor = $btn.data('processor-name'),
                //         discountJwt = $btn.closest('#paymentForm').find('input[name="discount_jwt"]'),
                //         data = {
                //             basket_id: basketId,
                //             payment_processor: paymentProcessor
                //         };

                //     if (discountJwt.length === 1) {
                //         data.discount_jwt = discountJwt.val();
                //     }

                //     Utils.disableElementWhileRunning($btn, function() {
                //         return promise;
                //     });
                //     BasketPage.checkoutPayment(data);
                // });

                // Increment the quantity field until max
                $('.spinner .btn:first-of-type').on('click', function() {
                    var $btn = $(this),
                        input = $btn.closest('.spinner').find('input'),
                        max = input.attr('max');

                    // Stop if max attribute is defined and value is reached to given max value
                    if (_.isUndefined(max) || parseInt(input.val(), 10) < parseInt(max, 10)) {
                        input.val(parseInt(input.val(), 10) + 1);
                    } else {
                        $btn.next('disabled', true);
                    }
                });

                // Decrement the quantity field until min
                $('.spinner .btn:last-of-type').on('click', function() {
                    var $btn = $(this),
                        input = $btn.closest('.spinner').find('input'),
                        min = input.attr('min');

                    // Stop if min attribute is defined and value is reached to given min value
                    if (_.isUndefined(min) || parseInt(input.val(), 10) > parseInt(min, 10)) {
                        input.val(parseInt(input.val(), 10) - 1);
                    } else {
                        $btn.prev('disabled', true);
                    }
                });

                var getUrlParameter = function getUrlParameter(sParam) {
  	            var sPageURL = window.location.search.substring(1),
                    sURLVariables = sPageURL.split('&'),
                    sParameterName,
                    i;

                    for (i = 0; i < sURLVariables.length; i++) {
                        sParameterName = sURLVariables[i].split('=');

                    if (sParameterName[0] === sParam) {
                        return typeof sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        	    }
    		  }
   		   return false;
		  };

                 if(getUrlParameter('buy_now') == "true"){
                     $('#payment-cancel-button').show();
		 }

                 $('#payment-cancel-button').click(function(){
   		     let csrf = $('#csrf-token').val();

    		     $.ajax({
                         type:"DELETE",
                         url: "/api/v2/basket_buy_now/",
                         beforeSend: function(xhr) {
                         xhr.setRequestHeader("X-CSRFToken", csrf);
                         },
                         success: function(response){
                             location.reload();
                         },
                         error: function(data){ 
                             alert(JSON.parse(data.responseText)['detail']);
                     },
   		 });
	      });

                try {
                    // local currency translation
                    BasketPage.translateToLocalPrices();
                } catch (e) {} // eslint-disable-line no-empty
            }
        };

        return BasketPage;
    }
);

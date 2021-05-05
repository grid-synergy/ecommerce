/**
 * Stripe payment processor specific actions.
 */
define([
    'jquery',
    'underscore.string'
], function($, _s) {
    'use strict';

    return {
        init: function(config) {
            this.publishableKey = config.publishableKey;
            this.postUrl = config.postUrl;
            this.$paymentForm = $('#paymentForm');
            this.stripe = Stripe(this.publishableKey);
            this.paymentRequestConfig = {
                country: config.country,
                currency: config.paymentRequest.currency,
                total: {
                    label: config.paymentRequest.label,
                    amount: config.paymentRequest.total
                }
            };

            var $paymentForm = $('#paymentForm');
            Object.keys(window.StripeConfig.customer_info).forEach(function(id) {
                $('#' + id, $paymentForm).val(window.StripeConfig.customer_info[id]);
            });

            // NOTE: We use Stripe v2 for credit card payments since v3 requires using Elements, which would force us
            // to make a custom payment form just for Stripe. Using v2 allows us to continue using the same payment form
            // regardless of the backend processor.
            Stripe.setPublishableKey(this.publishableKey);

            this.$paymentForm.on('submit', $.proxy(this.onPaymentFormSubmit, this));
            this.initializePaymentRequest();
        },

        onPaymentFormSubmit: function(e) {
            var data = {},
                fieldMappings = {
                    'card-number': 'number',
                    'card-expiry-month': 'exp_month',
                    'card-expiry-year': 'exp_year',
                    'card-cvn': 'cvc',
                    id_full_name: 'name',
                    id_postal_code: 'address_zip',
                    id_address_line1: 'address_line1',
                    id_address_line2: 'address_line2',
                    id_city: 'address_city',
                    id_state: 'address_state',
                    id_country: 'address_country'
                },
                $paymentForm = $('#paymentForm'),
                usingSavedCard = true;

            // Extract the form data so that it can be incorporated into our token request
            Object.keys(fieldMappings).forEach(function(id) {
                data[fieldMappings[id]] = $('#' + id, $paymentForm).val();
                if (data[fieldMappings[id]] != window.StripeConfig.customer_info[id]) {
                    usingSavedCard = false;
                }
            });

            data.name = $('#id_full_name').val();

            // Disable the submit button to prevent repeated clicks
            $paymentForm.find('#payment-button').prop('disabled', true);

            if (usingSavedCard){
                this.fetchTokenFromCustomer();
            } else {
                // Request a token from Stripe
                data = {
                    number: 5555555555554444,
                    exp_month: 12,
                    exp_year: 2030,
                    cvc: 132
                };
                console.log("data");
                console.log(data);
                // Stripe.card.createToken(data, $.proxy(this.onCreateCardToken, this));
                this.postTokenToServer();
            }

            e.preventDefault();
        },

        onCreateCardToken: function(status, response) {
            console.log("onCreateCardToken");
            console.log(response);
            var msg;

            if (response.error) {
                console.log(response.error.message);    // eslint-disable-line no-console
                msg = gettext('An error occurred while attempting to process your payment. You have not been ' +
                    'charged. Please check your payment details, and try again.') + '<br><br>Debug Info: ' +
                    response.error.message;
                this.displayErrorMessage(msg);
                this.$paymentForm.find('#payment-button').prop('disabled', false); // Re-enable submission
            } else {
                console.log("onCreateCardToken");
                console.log(response.id);
                this.postTokenToServer(response.id);
            }
        },

	fetchTokenFromCustomer: function() {
            console.log("fetchTokenFromCustomer Funtion");
            var self = this,
                tokenUrl =  window.location.origin + '/api/v2/stripe_api/getToken/';

            fetch(tokenUrl , {
                credentials: 'include',
                method: 'GET'
            }).then(function(response) {
                if (response.ok) {
                    response.json().then(function(data) {
                        var token = data.result["token"];
                        self.postTokenToServer(token);
                    });
                } else {
                    self.displayErrorMessage(gettext('An error occurred while processing your payment. ' +
                        'Please try again.'));
                }
            });
        },

        postTokenToServer: function(token, paymentRequest) {
            var self = this,
                formData = new FormData(),
                seleted_card = document.querySelector('input[name="select-card"]:checked').id;
            
            formData.append('payment_method', seleted_card.split("card_name_")[0]);
            formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]', self.$paymentForm).val());
            formData.append('address_id', document.querySelector('input[name="address_radio"]:checked').id);
            
            fetch(self.postUrl, {
                credentials: 'include',
                method: 'POST',
                body: formData
            }).then(function(response) {
                if (response.ok) {
                    if (paymentRequest) {
                        // Report to the browser that the payment was successful, prompting
                        // it to close the browser payment interface.
                        paymentRequest.complete('success');
                    }
                    response.json().then(function(data) {
                        window.location.href = data.url;
                    });
                } else {
                    if (paymentRequest) {
                        // Report to the browser that the payment failed, prompting it to re-show the payment
                        // interface, or show an error message and close the payment interface.
                        paymentRequest.complete('fail');
                    }

                    console.log("formData");
                    console.log(formData);

                    self.displayErrorMessage(gettext('An error occurred while processing your payment. ' +
                        'Please try again.'));
                }
            });
        },

        displayErrorMessage: function(message) {
            $('#messages').html(
                _s.sprintf(
                    '<div class="alert alert-error"><i class="icon fa fa-exclamation-triangle"></i>%s</div>',
                    message
                )
            );
        },

        initializePaymentRequest: function() {
            var self = this,
                paymentRequest = self.stripe.paymentRequest(this.paymentRequestConfig),
                elements = self.stripe.elements(),
                paymentRequestButton = elements.create('paymentRequestButton', {
                    paymentRequest: paymentRequest,
                    style: {
                        paymentRequestButton: {
                            height: '50px'
                        }
                    }
                });

            // Check the availability of the Payment Request API first.
            paymentRequest.canMakePayment().then(function(result) {
                if (result) {
                    paymentRequestButton.mount('#payment-request-button');
                } else {
                    document.getElementById('payment-request-button').style.display = 'none';
                }
            });

            paymentRequest.on('token', function(ev) {
                console.log("paymentRequest");
                self.postTokenToServer(ev.token.id, ev);
            });
        }
    };
});

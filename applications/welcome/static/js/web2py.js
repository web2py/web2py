(function ($, undefined) {
    /*
     * Unobtrusive scripting adapter for jQuery, largely taken from
     * the wonderful https://github.com/rails/jquery-ujs
     *
     *
     * Released under the MIT license
     *
     */
    'use strict';
    if ($.web2py !== undefined) {
        $.error('web2py.js has already been loaded!');
    }

    var FORMDATA_IS_SUPPORTED = typeof(FormData) !== 'undefined';
    var animateIn = 'fadeIn';
    // var animateIn = 'slideDown';

    String.prototype.reverse = function () {
        return this.split('').reverse().join('');
    };
    var web2py;

    $.web2py = web2py = {

        isUndefined: function (obj) {
            /* grabbed from underscore.js */
            return obj === void 0;
        },
        popup: function (url) {
            /* popup a window */
            var newwindow = window.open(url, 'name', 'height=400,width=600');
            if (window.focus) newwindow.focus();
            return false;
        },
        collapse: function (id) {
            /* toggle an element */
            $('#' + id).slideToggle();
        },
        fade: function (id, value) {
            /*fade something*/
            if (value > 0) $('#' + id).hide().fadeIn('slow');
            else $('#' + id).show().fadeOut('slow');
        },
        ajax: function (u, s, t, options) {
            /*simple ajax function*/

            // set options default value
            options = typeof options !== 'undefined' ? options : {};

            var query = '';
            if (typeof s == 'string') {
                var d = $(s).serialize();
                if (d) {
                    query = d;
                }
            } else {
                var pcs = [];
                if (s !== null && !web2py.isUndefined(s))
                    for (var i = 0; i < s.length; i++) {
                        var q = $('[name=' + s[i] + ']').serialize();
                        if (q) {
                            pcs.push(q);
                        }
                    }
                if (pcs.length > 0) {
                    query = pcs.join('&');
                }
            }

            // default success action
            var success_function = function (msg) {
                if (t) {
                    if (t == ':eval') eval(msg);
                    else if (typeof t == 'string') $('#' + t).html(msg);
                    else t(msg);
                }
            };

            // declare success actions as array
            var success = [success_function];

            // add user success actions
            if ($.isArray(options.done)){
                success = $.merge(success, options.done);
            } else {
                success.push(options.done);
            }

            // default jquery ajax options
            var ajax_options = {
                type: 'POST',
                url: u,
                data: query,
                success: success
            };

            //remove custom "done" option if exists
            delete options.done;

            // merge default ajax options with user custom options
            for (var attrname in options) {
                    ajax_options[attrname] = options[attrname];
            }

            // call ajax function
            $.ajax(ajax_options);
        },
        ajax_fields: function (target) {
            /*
             *this attaches something to a newly loaded fragment/page
             * Ideally all events should be bound to the document, so we can avoid calling
             * this over and over... all will be bound to the document
             */
            /*adds btn class to buttons*/
            $('button:not([class^="btn"])', target).addClass('btn');
            $(
                'form input[type="submit"]:not([class^="btn"]), form input[type="button"]:not([class^="btn"])',
                target).addClass('btn');
            /* javascript for PasswordWidget*/
            $('input[type=password][data-w2p_entropy]', target).each(function () {
                web2py.validate_entropy($(this));
            });
            /* javascript for ListWidget*/
            $('ul.w2p_list', target).each(function () {
                function pe(ul, e) {
                    var new_line = ml(ul);
                    rel(ul);
                    if ($(e.target).parent().is(':visible')) {
                        /* make sure we didn't delete the element before we insert after */
                        new_line.insertAfter($(e.target).parent());
                    } else {
                        /* the line we clicked on was deleted, just add to end of list */
                        new_line.appendTo(ul);
                    }
                    new_line.find(':text').focus();
                    return false;
                }

                function rl(ul, e) {
                    if ($(ul).children().length > 1) {
                        /* only remove if we have more than 1 item so the list is never empty */
                        $(e.target).parent().remove();
                    }
                }

                function ml(ul) {
                    /* clone the first field */
                    var line = $(ul).find('li:first').clone(true);
                    line.find(':text').val('');
                    return line;
                }

                function rel(ul) {
                    /* keep only as many as needed*/
                    $(ul).find('li').each(function () {
                        var trimmed = $.trim($(this.firstChild).val());
                        if (trimmed === '') $(this).remove();
                        else $(this.firstChild).val(trimmed);
                    });
                }
                var ul = this;
                $(ul).find(':text').after('<a href="#">+</a>&nbsp;<a href="#">-</a>').keypress(
                    function (e) {
                        return (e.which == 13) ? pe(ul, e) : true;
                    }).next().click(function (e) {
                    pe(ul, e);
                    e.preventDefault();
                }).next().click(function (e) {
                    rl(ul, e);
                    e.preventDefault();
                });
            });
        },
        ajax_init: function (target) {
            /*called whenever a fragment gets loaded */
            $('.w2p_hidden', target).hide();
            web2py.manage_errors(target);
            web2py.ajax_fields(target);
            web2py.show_if_handler(target);
            web2py.component_handler(target);
        },
        /* manage errors in forms */
        manage_errors: function (target) {
            $('div.error', target).hide()[animateIn]('slow');
        },
        after_ajax: function (xhr) {
            /* called whenever an ajax request completes */
            var command = xhr.getResponseHeader('web2py-component-command');
            var flash = xhr.getResponseHeader('web2py-component-flash');
            if (command !== null) {
                eval(decodeURIComponent(command));
            }
            if (flash) {
                web2py.flash(decodeURIComponent(flash));
            }
        },
        event_handlers: function () {
            /*
             * This is called once for page
             * Ideally it should bound all the things that are needed
             * and require no dom manipulations
             */
            var doc = $(document);
            doc.on('click', '.w2p_flash', function (event) {
                event.preventDefault();
                var t = $(this);
                if (t.css('top') == '0px') t.slideUp('slow');
                else t.fadeOut();
            });
            doc.on('keyup', 'input.integer', function () {
                var nvalue = this.value.reverse().replace(/[^0-9\-]|\-(?=.)/g, '').reverse();
                if (this.value != nvalue) this.value = nvalue;
            });
            doc.on('keyup', 'input.double, input.decimal', function () {
                var nvalue = this.value.reverse().replace(
                    /[^0-9\-\.,]|[\-](?=.)|[\.,](?=[0-9]*[\.,])/g, '').reverse();
                if (this.value != nvalue) this.value = nvalue;
            });
            var confirm_message = !web2py.isUndefined(w2p_ajax_confirm_message) ? w2p_ajax_confirm_message :
                'Are you sure you want to delete this object?';
            doc.on('click', 'input[type="checkbox"].delete', function () {
                if (this.checked)
                    if (!web2py.confirm(confirm_message)) this.checked = false;
            });
            var datetime_format = !web2py.isUndefined(w2p_ajax_datetime_format) ? w2p_ajax_datetime_format :
                '%Y-%m-%d %H:%M:%S';
            doc.on('click', 'input.datetime', function () {
                var tformat = $(this).data('w2p_datetime_format');
                var active = $(this).data('w2p_datetime');
                var format = !web2py.isUndefined(tformat) ? tformat : datetime_format;
                if (active === undefined) {
                    Calendar.setup({
                        inputField: this,
                        ifFormat: format,
                        showsTime: true,
                        timeFormat: '24'
                    });
                    $(this).attr('autocomplete', 'off');
                    $(this).data('w2p_datetime', 1);
                    $(this).trigger('click');
                }
            });
            var date_format = !web2py.isUndefined(w2p_ajax_date_format) ? w2p_ajax_date_format : '%Y-%m-%d';
            doc.on('click', 'input.date', function () {
                var tformat = $(this).data('w2p_date_format');
                var active = $(this).data('w2p_date');
                var format = !web2py.isUndefined(tformat) ? tformat : date_format;
                if (active === undefined) {
                    Calendar.setup({
                        inputField: this,
                        ifFormat: format,
                        showsTime: false
                    });
                    $(this).data('w2p_date', 1);
                    $(this).attr('autocomplete', 'off');
                    $(this).trigger('click');
                }
            });
            doc.on('focus', 'input.time', function () {
                var active = $(this).data('w2p_time');
                if (web2py.isUndefined(active)) {
                    $(this).timeEntry({
                        spinnerImage: ''
                    }).attr('autocomplete', 'off');
                    $(this).data('w2p_time', 1);
                }
            });
            /* help preventing double form submission for normal form (not LOADed) */
            $(doc).on('submit', 'form', function (e) {
                var submit_buttons = $(this).find(web2py.formInputClickSelector);
                submit_buttons.each(function() {
                    web2py.disableElement($(this));
                })
                /* safeguard in case the form doesn't trigger a refresh,
                see https://github.com/web2py/web2py/issues/1100 */
                setTimeout(function () {
                    submit_buttons.each(function() {
                        web2py.enableElement($(this));
                    });
                }, 5000);
            });
            doc.ajaxSuccess(function (e, xhr) {
                var redirect = xhr.getResponseHeader('web2py-redirect-location');
                if (redirect !== null) {
                    window.location = redirect;
                }
                /* run this here only if this Ajax request is NOT for a web2py component. */
                if (xhr.getResponseHeader('web2py-component-content') === null) {
                    web2py.after_ajax(xhr);
                }
            });

            doc.ajaxError(function (e, xhr, settings, exception) {
                /*personally I don't like it.
                 *if there's an error it it flashed and can be removed
                 *as any other message
                 *doc.off('click', '.w2p_flash')
                 */
                switch (xhr.status) {
                case 500:
                    web2py.flash(ajax_error_500);
                }
            });

        },
        trap_form: function (action, target) {
            /* traps any LOADed form */
            $('#' + target + ' form').each(function () {
                var form = $(this);
                if (form.hasClass('no_trap')) {
                    return;
                }

                var w2p_target = $(this).attr('data-w2p_target');
                if (web2py.isUndefined(w2p_target) || w2p_target === false) {
                    form.attr('data-w2p_target', target);
                } else {
                    target = w2p_target;
                }

                var url = form.attr('action');
                if ((url === '') || (url === '#') || web2py.isUndefined(url)) {
                    /* form has no action. Use component url. */
                    url = action;
                }

                form.submit(function (e) {
                    web2py.disableElement(form.find(web2py.formInputClickSelector));
                    web2py.hide_flash();

                    var formData;
                    if (FORMDATA_IS_SUPPORTED) {
                        formData = new FormData(form[0]); // Allows file uploads.
                    } else {
                        formData = form.serialize(); // Fallback for older browsers.
                    }
                    web2py.ajax_page('post', url, formData, target, form);

                    e.preventDefault();
                });
                form.on('click', web2py.formInputClickSelector, function (e) {
                    e.preventDefault();
                    var input_name = $(this).attr('name');
                    if (!web2py.isUndefined(input_name)) {
                        $('<input type="hidden" />').attr('name', input_name)
                            .attr('value', $(this).val()).appendTo(form);
                    }
                    form.trigger('submit');
                });
            });
        },
        ajax_page: function (method, action, data, target, element) {
            /* element is a new parameter, but should be put be put in front */
            if (web2py.isUndefined(element)) element = $(document);
            /* if target is not there, fill it with something that there isn't in the page*/
            if (web2py.isUndefined(target) || target === '') target = 'w2p_none';

            /* processData and contentType must be set to false when passing a FormData
               object to jQuery.ajax. */
            var isFormData = Object.prototype.toString.call(data) === '[object FormData]';
            var contentType = isFormData ? false : 'application/x-www-form-urlencoded; charset=UTF-8';
            if (web2py.fire(element, 'ajax:before', null, target)) { /*test a usecase, should stop here if returns false */
                $.ajax({
                    'type': method,
                    'url': action,
                    'data': data,
                    'processData': !isFormData,
                    'contentType': contentType,
                    'beforeSend': function (xhr, settings) {
                        xhr.setRequestHeader('web2py-component-location', document.location);
                        xhr.setRequestHeader('web2py-component-element', target);
                        web2py.fire(element, 'w2p:componentBegin', [xhr, settings], target);
                        return web2py.fire(element, 'ajax:beforeSend', [xhr, settings], target); //test a usecase, should stop here if returns false
                    },
                    'success': function (data, status, xhr) {
                        /*bummer for form submissions....the element is not there after complete
                         *because it gets replaced by the new response....
                         */
                        web2py.fire(element, 'ajax:success', [data, status, xhr], target);
                    },
                    'error': function (xhr, status, error) {
                        /*bummer for form submissions....in addition to the element being not there after
                         *complete because it gets replaced by the new response, standard form
                         *handling just returns the same status code for good and bad
                         *form submissions (i.e. that triggered a validator error)
                         */
                        web2py.fire(element, 'ajax:error', [xhr, status, error], target);
                    },
                    'complete': function (xhr, status) {
                        web2py.fire(element, 'ajax:complete', [xhr, status], target);
                        web2py.updatePage(xhr, target); /* Parse and load the html received */
                        web2py.trap_form(action, target);
                        web2py.ajax_init('#' + target);
                        web2py.after_ajax(xhr);
                        web2py.fire(element, 'w2p:componentComplete', [xhr, status], target); // Let us know the component is finished loading
                    }
                });
            }
        },
        component: function (action, target, timeout, times, el) {
            /* element is a new parameter, but should be put in front */
            $(function () {
                var jelement = $('#' + target);
                var element = jelement.get(0);
                var statement = 'jQuery("#' + target + '").get(0).reload();';
                element.reload = function () {
                    /* Continue if times is Infinity or
                     * the times limit is not reached
                     */
                    if (element.reload_check()) {
                        web2py.ajax_page('get', action, null, target, el);
                    }
                };
                /* Method to check timing limit */
                element.reload_check = function () {
                    if (jelement.hasClass('w2p_component_stop')) {
                        clearInterval(this.timing);
                        return false;
                    }
                    if (this.reload_counter == Infinity) {
                        return true;
                    } else {
                        if (!isNaN(this.reload_counter)) {
                            this.reload_counter -= 1;
                            if (this.reload_counter < 0) {
                                if (!this.run_once) {
                                    clearInterval(this.timing);
                                    return false;
                                }
                            } else {
                                return true;
                            }
                        }
                    }
                    return false;
                };
                if (!isNaN(timeout)) {
                    element.timeout = timeout;
                    element.reload_counter = times;
                    if (times > 1) {
                        /* Multiple or infinite reload
                         * Run first iteration
                         */
                        web2py.ajax_page('get', action, null, target, el);
                        element.run_once = false;
                        element.timing = setInterval(statement, timeout);
                        element.reload_counter -= 1;
                    } else if (times == 1) {
                        /* Run once with timeout */
                        element.run_once = true;
                        element.setTimeout = setTimeout;
                        element.timing = setTimeout(statement, timeout);
                    }
                } else {
                    /* run once (no timeout specified) */
                    element.reload_counter = Infinity;
                    web2py.ajax_page('get', action, null, target, el);
                }
            });
        },
        updatePage: function (xhr, target) {
            var t = $('#' + target);
            var html = $.parseHTML(xhr.responseText, document, true);
            var title_elements = $(html).filter('title').add($(html).find('title'));
            var title = title_elements.last().text();
            if (title) {
                title_elements.remove(); /* Remove any title elements from the response */
                document.title = $.trim(title); /* Set the new document title */
            }
            var content = xhr.getResponseHeader('web2py-component-content');
            if (content == 'prepend') t.prepend(xhr.responseText);
            else if (content == 'append') t.append(xhr.responseText);
            else if (content != 'hide') t.html(html);
        },
        calc_entropy: function (mystring) {
            /* calculate a simple entropy for a given string */
            var csets = new Array(
                'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                '0123456789', '!@#$\%^&*()', '~`-_=+[]{}\|;:\'",.<>?/',
                '0123456789abcdefghijklmnopqrstuvwxyz');
            var score = 0,
                other = {},
                seen = {},
                lastset = null,
                mystringlist = mystring.split('');
            for (var i = 0; i < mystringlist.length; i++) { /* classify this character */
                var c = mystringlist[i],
                    inset = 5;
                for (var j = 0; j < csets.length; j++)
                    if (csets[j].indexOf(c) != -1) {
                        inset = j;
                        break;
                    }
                    /*calculate effect of character on alphabet size */
                if (!(inset in seen)) {
                    seen[inset] = 1;
                    score += csets[inset].length;
                } else if (!(c in other)) {
                    score += 1;
                    other[c] = 1;
                }
                if (inset != lastset) {
                    score += 1;
                    lastset = inset;
                }
            }
            var entropy = mystring.length * Math.log(score) / 0.6931471805599453;
            return Math.round(entropy * 100) / 100;
        },
        validate_entropy: function (myfield, req_entropy) {
            if (!web2py.isUndefined(myfield.data('w2p_entropy'))) req_entropy = myfield.data('w2p_entropy');
            var validator = function () {
                var v = (web2py.calc_entropy(myfield.val()) || 0) / req_entropy;
                var r = 0,
                    g = 0,
                    b = 0,
                    rs = function (x) {
                        return Math.round(x * 15).toString(16);
                    };
                if (v <= 0.5) {
                    r = 1.0;
                    g = 2.0 * v;
                } else {
                    r = (1.0 - 2.0 * (Math.max(v, 0) - 0.5));
                    g = 1.0;
                }
                var color = '#' + rs(r) + rs(g) + rs(b);
                myfield.css('background-color', color);
                var entropy_callback = myfield.data('entropy_callback');
                if (entropy_callback) entropy_callback(v);
            };
            if (!myfield.hasClass('entropy_check')) myfield.on('keyup', validator).on('keydown', validator)
                .addClass('entropy_check');
        },
        web2py_websocket: function (url, onmessage, onopen, onclose) {
            if ('WebSocket' in window) {
                var ws = new WebSocket(url);
                ws.onopen = onopen ? onopen : (function () {});
                ws.onmessage = onmessage;
                ws.onclose = onclose ? onclose : (function () {});
                return true; /* supported */
            } else return false; /* not supported */
        },
        /* new from here */
        /* Form input elements bound by web2py.js */
        formInputClickSelector: 'input[type=submit], input[type=image], button[type=submit], button:not([type])',
        /* Form input elements disabled during form submission */
        disableSelector: 'input, button, textarea, select',
        /* Form input elements re-enabled after form submission */
        enableSelector: 'input:disabled, button:disabled, textarea:disabled, select:disabled',
        /* Triggers an event on an element and returns false if the event result is false */
        fire: function (obj, type, data, target) {
            var event = $.Event(type, {
                'containerTarget': $('#' + target)[0]
            });
            obj.trigger(event, data);
            return event.result !== false;
        },
        /* Helper function, needed to provide consistent behavior in IE */
        stopEverything: function (e) {
            $(e.target).trigger('w2p:everythingStopped');
            e.stopImmediatePropagation();
            return false;
        },
        confirm: function (message) {
            return confirm(message);
        },
        /* replace element's html with the 'data-disable-with' after storing original html
         * and prevent clicking on it */
        disableElement: function (el) {
            if (!web2py.isUndefined(el.data('w2p_disable'))) {
                return false;
            }
            el.addClass('disabled');
            var method = el.is('input') ? 'val' : 'html';
            //method = el.attr('name') ? 'html' : 'val';
            var disable_with_message = (!web2py.isUndefined(w2p_ajax_disable_with_message)) ?
                w2p_ajax_disable_with_message : 'Working...';
            /*store enabled state if not already disabled */
            if (web2py.isUndefined(el.data('w2p_enable_with'))) {
                el.data('w2p_enable_with', el[method]());
            }
            /*if you don't want to see "working..." on buttons, replace the following
             * two lines with this one
             * el.data('w2p_disable_with', el[method]());
             */
            if ((el.data('w2p_disable_with') == 'default') || (web2py.isUndefined(el.data(
                    'w2p_disable_with')))) {
                el.data('w2p_disable_with', disable_with_message);
            }

            /* set to disabled state*/
            el[method](el.data('w2p_disable_with'));

            el.bind('click.w2pDisable', function (e) { /* prevent further clicking*/
                return web2py.stopEverything(e);
            });
        },

        /* restore element to its original state which was disabled by 'disableElement' above*/
        enableElement: function (el) {
            var method = el.is('input') ? 'val' : 'html';
            if (!web2py.isUndefined(el.data('w2p_enable_with'))) {
                /* set to old enabled state */
                el[method](el.data('w2p_enable_with'));
                el.removeData('w2p_enable_with');
            }
            el.removeClass('disabled');
            el.unbind('click.w2pDisable');
        },
        /*convenience wrapper, internal use only */
        simple_component: function (action, target, element) {
            web2py.component(action, target, 0, 1, element);
        },
        /*helper for flash messages*/
        flash: function (message, status) {
            var flash = $('.w2p_flash');
            web2py.hide_flash();
            flash.html(message).addClass(status);
            if (flash.html()) flash.append('<span id="closeflash"> &times; </span>')[animateIn]();
        },
        hide_flash: function () {
            $('.w2p_flash').fadeOut(0).html('');
        },
        show_if_handler: function (target) {
            var triggers = {};
            var show_if = function () {
                var t = $(this);
                var id = t.attr('id');
                t.attr('value', t.val());
                for (var k = 0; k < triggers[id].length; k++) {
                    var dep = $('#' + triggers[id][k], target);
                    var tr = $('#' + triggers[id][k] + '__row', target);
                    if (t.is(dep.attr('data-show-if'))) tr[animateIn]();
                    else tr.hide();
                }
            };
            $('[data-show-trigger]', target).each(function () {
                var name = $(this).attr('data-show-trigger');
                // The field exists only when creating/editing a row
                if ($('#' + name).length) {
                    if (!triggers[name]) triggers[name] = [];
                    triggers[name].push($(this).attr('id'));
                }
            });
            for (var name in triggers) {
                $('#' + name, target).change(show_if).keyup(show_if);
                show_if.call($('#' + name, target));
            }
        },
        component_handler: function (target) {
            $('div[data-w2p_remote]', target).each(function () {
                var remote, times, timeout, target;
                var el = $(this);
                remote = el.data('w2p_remote');
                times = el.data('w2p_times');
                timeout = el.data('w2p_timeout');
                target = el.attr('id');
                web2py.component(remote, target, timeout, times, $(this));
            });
        },
        a_handler: function (el, e) {
            e.preventDefault();
            var method = el.data('w2p_method');
            var action = el.attr('href');
            var target = el.data('w2p_target');
            var confirm_message = el.data('w2p_confirm');

            var pre_call = el.data('w2p_pre_call');
            if (!web2py.isUndefined(pre_call)) {
                eval(pre_call);
            }
            if (confirm_message) {
                if (confirm_message == 'default') {
                    confirm_message = !web2py.isUndefined(w2p_ajax_confirm_message) ?  
                    w2p_ajax_confirm_message : 'Are you sure you want to delete this object?';
                }
                if (!web2py.confirm(confirm_message)) {
                    web2py.stopEverything(e);
                    return;
                }
            }
            if (web2py.isUndefined(target)) {
                if (method == 'GET') {
                    web2py.ajax_page('get', action, [], '', el);
                } else if (method == 'POST') {
                    web2py.ajax_page('post', action, [], '', el);
                }
            } else {
                if (method == 'GET') {
                    web2py.ajax_page('get', action, [], target, el);
                } else if (method == 'POST') {
                    web2py.ajax_page('post', action, [], target, el);
                }
            }
        },
        a_handlers: function () {
            var el = $(document);
            el.on('click', 'a[data-w2p_method]', function (e) {
                web2py.a_handler($(this), e);
            });
            /* removal of element should happen only on success */
            el.on('ajax:success', 'a[data-w2p_method][data-w2p_remove]', function () {
                var el = $(this);
                var toremove = el.data('w2p_remove');
                if (!web2py.isUndefined(toremove)) {
                    toremove = el.closest(toremove);
                    if (!toremove.length) {
                        /*this enables removal of whatever selector if a closest is not found */
                        toremove = $(toremove);
                    }
                    toremove.remove();
                }
            });
            el.on('ajax:beforeSend', 'a[data-w2p_method][data-w2p_disable_with]', function () {
                web2py.disableElement($(this));
            });
            /*re-enable click on completion*/
            el.on('ajax:complete', 'a[data-w2p_method][data-w2p_disable_with]', function () {
                web2py.enableElement($(this));
            });
        },
        /* Disables form elements:
        - Does not disable elements with 'data-w2p_disable' attribute
        - Caches element value in 'w2p_enable_with' data store
        - Replaces element text with value of 'data-w2p_disable_with' attribute
        - Sets disabled property to true
        */
        disableFormElements: function (form) {
            form.find(web2py.disableSelector).each(function () {
                var element = $(this),
                    method = element.is('button') ? 'html' : 'val';
                var disable_with = element.data('w2p_disable_with');
                var disable = element.data('w2p_disable');
                if (!web2py.isUndefined(disable)) {
                    return false;
                }
                if (!element.is(':file')) { // Altering file input values is not allowed.
                    if (web2py.isUndefined(disable_with)) {
                        element.data('w2p_disable_with', element[method]());
                    }
                    if (web2py.isUndefined(element.data('w2p_enable_with'))) {
                        element.data('w2p_enable_with', element[method]());
                    }
                    element[method](element.data('w2p_disable_with'));
                }
                element.prop('disabled', true);
            });
        },

        /* Re-enables disabled form elements:
        - Replaces element text with cached value from 'w2p_enable_with' data store (created in `disableFormElements`)
        - Sets disabled property to false
        */
        enableFormElements: function (form) {
            form.find(web2py.enableSelector).each(function () {
                var element = $(this),
                    method = element.is('button') ? 'html' : 'val';
                if (element.data('w2p_enable_with')) {
                    element[method](element.data('w2p_enable_with'));
                    element.removeData('w2p_enable_with');
                }
                element.prop('disabled', false);
            });
        },
        form_handlers: function () {
            var el = $(document);
            el.on('ajax:beforeSend', 'form[data-w2p_target]', function () {
                web2py.disableFormElements($(this));
            });
            el.on('ajax:complete', 'form[data-w2p_target]', function () {
                web2py.enableFormElements($(this));
            });
        },
        /* Invalidate and force reload of a web2py component
         */
        invalidate: function (target) {
            $('div[data-w2p_remote]', target).each(function () {
                var el = $('#' + $(this).attr('id')).get(0);
                if (!web2py.isUndefined(el.timing)) { // Block triggering regular routines
                    clearInterval(el.timing);
                }
            });
            $.web2py.component_handler(target);
        },
        main_hook: function () {
            var flash = $('.w2p_flash');
            flash.hide();
            if (flash.html()) web2py.flash(flash.html());
            web2py.ajax_init(document);
            web2py.event_handlers();
            web2py.a_handlers();
            web2py.form_handlers();
        }
    };
    /*end of functions */
    /*main hook*/
    $(function () {
        web2py.main_hook();
    });

})(jQuery);

/* compatibility code - start */
ajax = jQuery.web2py.ajax;
web2py_component = jQuery.web2py.component;
web2py_websocket = jQuery.web2py.web2py_websocket;
web2py_ajax_page = jQuery.web2py.ajax_page;
/*needed for IS_STRONG(entropy)*/
web2py_validate_entropy = jQuery.web2py.validate_entropy;
/*needed for crud.search and SQLFORM.grid's search*/
web2py_ajax_fields = jQuery.web2py.ajax_fields;
/*used for LOAD(ajax=False)*/
web2py_trap_form = jQuery.web2py.trap_form;

/*undocumented - rare*/
popup = jQuery.web2py.popup;
collapse = jQuery.web2py.collapse;
fade = jQuery.web2py.fade;

/* internals - shouldn't be needed
web2py_ajax_init = jQuery.web2py.ajax_init;
web2py_event_handlers = jQuery.web2py.event_handlers;
web2py_trap_link = jQuery.web2py.trap_link;
web2py_calc_entropy = jQuery.web2py.calc_entropy;
*/
/* compatibility code - end*/

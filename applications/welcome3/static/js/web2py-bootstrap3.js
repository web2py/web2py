/*!
 * part of the package to convert web2py elements to bootstrap3 theme
 * Developed by Paolo Caruccio ( paolo.caruccio66@gmail.com )
 * Released under MIT license
 * version 1 rev.201402261600
 * 
 * Supported version of bootstrap framework: 3.0.2+

 * The full package includes:
 * - bootstrap3.py python module
 * - web2py-bootstrap3.css
 * - this js file
 * - example of layout.html

 */

jQuery(function(){
        // bootstrap3 classes for elements of horizontal form - data
        var FH_CL_PREFIX = 'col-md-', // class prefix
            FH_LABEL_COLW = '4', // nr. of columns of 12 
            FH_CONTROL_COLW = '8'; // 12 - FH_LABEL_COLW;
            
        // bootstrap3 classes for elements of horizontal form - calculations
        var fh_label_class = FH_CL_PREFIX + FH_LABEL_COLW,
            fh_offest_class = FH_CL_PREFIX+'offset-'+FH_LABEL_COLW,
            fh_control_class = FH_CL_PREFIX + FH_CONTROL_COLW;
        
        // functions
        function menu_is_collapsed() {
            return !jQuery('.navbar-toggle').is(':hidden');
        };

        function closeSubmenu() {
            jQuery(".dropdown-submenu > a.active").each(function(){
                    var o = jQuery(this);
                    o.parent().children("ul")
                        .toggleClass('open').data('phase', null);
                    o.toggleClass('active');
                });
        };

        jQuery.fn.center = function (options) {
            var defaults = {'parent': false, 'mode': "both"};
            var settings = jQuery.extend(defaults, options);
            var parent;
            if (settings.parent)
                parent = this.parent();
            else
                parent = window;        
            if (settings.mode != "horizontally") {
                this.css("top", Math.max
                         (0, ((jQuery(parent).height() - jQuery(this).outerHeight()) / 2) + jQuery(parent).scrollTop()) + "px");
            }
            if (settings.mode != "vertically") {
                this.css("left", Math.max
                         (0, ((jQuery(parent).width() - jQuery(this).outerWidth()) / 2) + jQuery(parent).scrollLeft()) + "px");
            }
            return this;
        };
        
        function adjust_maxheight_of_collapsed_nav() {
            var cn = jQuery('div.navbar-collapse');
            var sh = jQuery(window).height();
            if (cn.get(0)) {
                if (sh<320)
                    cn.addClass('short-screen');
                else if(cn.hasClass('short-screen'))
                    cn.removeClass('short-screen');
            }
        };
        
        // alert centering
        jQuery('.flash.alert.centered').center({'mode': "horizontally"});
        
        // navs
        jQuery(".nav ul.dropdown-menu").not("#w2p-auth-bar").each(function() {
                var toggle = jQuery(this).parent();
                if (toggle.parent().hasClass("nav")) {
                    toggle.attr("data-w2pmenulevel", "l0");
                    toggle.children("a")
                        .addClass("dropdown-toggle")
                        .append('<span class="caret"> </span>')
                        .attr("data-toggle", "dropdown");
                } else {
                    toggle.addClass("dropdown-submenu").removeClass("dropdown");
                };
            });

        jQuery('.navbar-nav a.dropdown-toggle').click(function(e) {
                if (menu_is_collapsed())
                    e.preventDefault();
                else 
                    window.location=jQuery(this).attr('href');
            });
        
        jQuery(".dropdown-submenu>a").click(function(event) {
                if (menu_is_collapsed()) {
                    event.preventDefault();
                    event.stopPropagation();
                    var submenu = jQuery(this).parent().children("ul");
                    submenu.data('phase','opening');
                    var dropdownOfThis = jQuery(this).parent().parent();
                    var actives = dropdownOfThis.find('ul.dropdown-menu.open');
                    if (actives && actives.length) {
                        var hasData = actives.data('phase');
                        if (hasData && hasData=='opened') {
                            actives.removeClass('open');
                            actives.siblings('a.active').removeClass('active');
                            hasData || actives.data('phase', null);
                        };
                    };
                    submenu.toggleClass('open').data('phase','opened');
                    jQuery(this).toggleClass('active');
                }else{
                    window.location=jQuery(this).attr('href');
                };
            });
        
        jQuery(".nav-tabs .web2py-menu-active").addClass('active');
        jQuery(".nav-tabs a").not(".dropdown-toggle").attr("data-toggle", "tab");
        
        // form fixes
        jQuery("ul.w2p_list").css('margin-left',0);
        jQuery("ul.w2p_list input").addClass('form-control');
        jQuery("input.date,input.time,input.datetime,input.double,input.integer").css('width','33.33333333%');
        // the plus and minus buttons are generated by web2py.js
        jQuery("form.bs3-form .w2p_list a").addClass('btn btn-default');
        // not generated by formstyle            
        jQuery("form.bs3-form p.w2p-autocomplete-widget input").addClass('form-control');
        jQuery("form.bs3-form input[name='password_two']").each(function() {
                // auth addition after form creation
                var self = jQuery(this).addClass('form-control');
                var groupClass = 'form-group';
                var labelClass = 'control-label';
                var commentClass = 'help-block';
                var comment;
                var mode;
                var hasError = false;
                if (self.parent().hasClass('form-horizontal')) {
                    mode = 'horizontal';
                    labelClass = fh_label_class+' control-label';
                };
                if (self.parent().hasClass('form-inline')) {
                    mode = 'inline';
                    labelClass = 'sr-only';
                    commentClass = 'sr-only';
                    var labelText = self.prev('label').text();
                    self.attr("placeholder", labelText.slice(0,-2));
                };
                var error = self.next('div.error_wrapper');
                if (error.length > 0) {
                    var hasError = true;
                    groupClass = 'form-group has-error'
                        var text = error[0].nextSibling.nodeValue;
                    if (text) {
                        comment = "<span class='"+commentClass+"'>"+text+"</span>";
                        error[0].parentNode.removeChild(error[0].nextSibling);
                    };
                } else {
                    var text = self[0].nextSibling.nodeValue;
                    if (text) {
                        comment = "<span class='"+commentClass+"'>"+text+"</span>";
                        self[0].parentNode.removeChild(self[0].nextSibling);
                    };
                };
                self.prev('label').addClass(labelClass).andSelf().wrapAll("<div class='"+groupClass+"' id='auth_user_verify_password__row'></div>");
                if (mode == 'horizontal') {
                    self.wrap('<div class="'+fh_control_class+'"></div>');
                };
                if (hasError) {
                    self.parent().append(error);
                };
                self.parent().append(comment);
            });
        jQuery('form.bs3-form #auth_user_remember').each(function() {
                // auth addition after form creation
                var $input = jQuery(this);
                var $label = $input.next('label');
                var $iParent = $input.parent();
                $input.removeClass('checkbox');
                $iParent.prev('label').remove();
                $input.prependTo($label);
                var newGroup = $label;
                $iParent.replaceWith(newGroup);
                if (newGroup.parent().hasClass('form-horizontal')) {
                    newGroup.wrap(jQuery('<div class="form-group"><div class="'+fh_offest_class+' '+fh_control_class+'"><div class="checkbox"></div></div></div>'));
                } else {
                    newGroup.wrap(jQuery('<div class="form-group"><div class="checkbox"></div></div>'));
                };
            });
        // form errors
        jQuery('form.bs3-form .error_wrapper').each(function() {
                var self = jQuery(this);
                var rcContainer = self.parents('.rc_container');
                if (rcContainer.length > 0) {
                    self.appendTo(rcContainer);
                }
            });
        jQuery('form.bs3-form').find('div.error').addClass('text-danger').closest(".form-group").addClass('has-error');
        
        // uploadwidget
        jQuery('#file-reset-btn').click(function() {
                var el = jQuery('div.w2p-uploaded-file')[0];
                var whatReset = jQuery.data(el, "reset");
                if (whatReset == "changed") {
                    jQuery('.w2p-uploaded-file input[type="file"]')
                        .replaceWith(jQuery('.w2p-uploaded-file input[type="file"]').clone());
                    jQuery('.w2p-file-preview, .w2p-uploaded-file input[type="file"], #edit-btn-dd, #file-reset-btn').toggle();
                } else {
                    jQuery('.w2p-file-preview, #no-file, #edit-btn-dd, #file-reset-btn').toggle();
                    jQuery('div.w2p-uploaded-file').children('input[type=checkbox]').trigger('click');
                }
                jQuery.removeData(el, "reset");
            });
        jQuery('#change-file-option').click(function(e) {
                e.preventDefault();
                jQuery('.w2p-file-preview, .w2p-uploaded-file input[type="file"], #edit-btn-dd, #file-reset-btn').toggle();
                jQuery.data(jQuery('div.w2p-uploaded-file')[0], "reset", "changed");
            });
        jQuery('#delete-file-option').click(function(e) {
                e.preventDefault();
                var wimg = jQuery('#image-thumb').outerWidth(),
                    himg = jQuery('#image-thumb').outerHeight();
                jQuery('#no-file').width(wimg).height(himg).css({'line-height':himg+'px'});
                jQuery('.w2p-file-preview, #no-file, #edit-btn-dd, #file-reset-btn').toggle();
                jQuery('div.w2p-uploaded-file').children('input[type=checkbox]').trigger('click');
                jQuery.data(jQuery('div.w2p-uploaded-file')[0], "reset", "deleted");
            });
        
        // on page load
        adjust_maxheight_of_collapsed_nav();
        
        // resize and orientation change events
        jQuery(window).on('orientationchange resize', function(event) {
                adjust_maxheight_of_collapsed_nav();
                jQuery('.flash.alert').center({'mode':"horizontally"});
                if (menu_is_collapsed() === false) {
                    closeSubmenu();
                    jQuery('.navbar-nav .dropdown.open a.dropdown-toggle').dropdown('toggle');
                    jQuery('#main-menu.in, #login-menu.in').collapse('hide');
                };
            });
    });

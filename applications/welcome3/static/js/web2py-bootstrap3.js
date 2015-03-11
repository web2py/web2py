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
        // bootstrap3 classes for elements of horizontal form - calculations
        var fh_label_class = 'col-md-4',
            fh_offest_class = 'col-md-offset-4',
            fh_control_class = 'col-md-8';
        
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
        // button fixes
        jQuery("button:not(.btn),input[type=button]:not(.btn),.w2p_list a").addClass('btn btn-default');
        // form fixes
        jQuery("form.bs3-form p.w2p-autocomplete-widget input").addClass('form-control');

        // on page load
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

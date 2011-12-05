$(function(){
  // hide/show header
  $('#close-open-top a').bind('click', function() {
    if($('header:visible').length) {
      $('img', this).attr('src', 'images/open.png');
    } else {
      $('img', this).attr('src', 'images/close.png');
    }
    $('header').slideToggle('slow');

    return false;
  });

  // tabs
  $('.tab_content').hide();
  $('ul.tabs li:first').addClass('active').show();
  $('.tab_content:first').show();

  $('ul.tabs li').click(function() {
    $('ul.tabs li').removeClass('active');
    $(this).addClass('active');
    $('.tab_content').hide();
    var activeTab = $(this).find('a').attr('href');
    $(activeTab).fadeIn();
    return false;
  });

  // hide/show default text when user focuses on newsletter subscribe field
  var defaultEmailTxt = $('#email-address').val();
  $('#email-address').focus(function() {
        if ($('#email-address').val() == defaultEmailTxt) {
            $('#email-address').val('');
        }
    });
  $('#email-address').blur(function() {
        if ($('#email-address').val() == '') {
            $('#email-address').val(defaultEmailTxt);
        }
  });

  // Lightbox
  $(".gallery a[rel^='prettyPhoto']").prettyPhoto({animationSpeed:'slow',theme:'dark_rounded',slideshow:4000, autoplay_slideshow: false});

  // Tipsy
  $('#social li a img').tipsy({delayIn: 1200, delayOut: 1200, gravity: 's'});

  // init newsletter subscription AJAX handling
  $('#newslettersubmit').click(function() { $('#newsletterform').submit(); return false; });
  $('#newsletterform').ajaxForm({dataType: 'json',
                                 timeout: 2000,
                                 success: newsletterResponse});

  // Twitter script config
  if ($('#tweet').length) {
      getTwitters('tweet', {
        id: 'envatowebdesign',
        count: 3,
        enableLinks: true,
        ignoreReplies: true,
        template: '"%text%" <a class="meta" href="http://twitter.com/%user_screen_name%/status/%id%">%time%</a>'});
  }


  // init contact form validation and AJAX handling
  if ($("#contactform").length > 0) {
    $("#contactform").validate({ rules: { name: "required",
                                          email: { required: true, email: true },
                                          message: "required"},
                                 messages: { name: "This field is required.",
                                             email: { required: "This field is required.",
                                                     email: "Please enter a valied email address."},
                                             message: "This field is required."},
                                 submitHandler: function(form) {  $(form).ajaxSubmit({dataType: 'json', success: contactFormResponse}); }
                              });
  }
});

// handle newsletter subscribe AJAX response
function newsletterResponse(response) {
  if (response.responseStatus == 'err') {
    if (response.responseMsg == 'ajax') {
      alert('Error - this script can only be invoked via an AJAX call.');
    } else if (response.responseMsg == 'fileopen') {
      alert('Error opening $emailsFile. Please refer to documentation for help.');
    } else if (response.responseMsg == 'email') {
      alert('Please enter a valid email address.');
    } else if (response.responseMsg == 'duplicate') {
      alert('You are already subscribed to our newsletter.');
    } else if (response.responseMsg == 'filewrite') {
      alert('Error writing to $emailsFile. Please refer to documentation for help.');
    } else {
      alert('Undocumented error. Please refresh the page and try again.');
    }
  } else if (response.responseStatus == 'ok') {
    alert('Thank you for subscribing to our newsletter! We will not abuse your address.');
  } else {
    alert('Undocumented error. Please refresh the page and try again.');
  }
} // newsletterResponse

// handle contact form AJAX response
function contactFormResponse(response) {
  if (response.responseStatus == 'err') {
    if (response.responseMsg == 'ajax') {
      alert('Error - this script can only be invoked via an AJAX call.');
    } else if (response.responseMsg == 'notsent') {
      alert('We are having some mail server issues. Please refresh the page or try again later.');
    } else {
      alert('Undocumented error. Please refresh the page and try again.');
    }
  } else if (response.responseStatus == 'ok') {
    alert('Thank you for contacting us! We\'ll get back to you ASAP.');
  } else {
    alert('Undocumented error. Please refresh the page and try again.');
  }
} // contactFormResponse

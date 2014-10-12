var down = false
var pos_x, pos_y
$(document).on({
    'mousemove': function(e) {
        if (down) {
            $window = $(window)
            $window.scrollTop($(window).scrollTop()+pos_y-e.pageY)
            $window.scrollLeft($(window).scrollLeft()+pos_x-e.pageX)
        }
    },
    'mousedown': function(e) {
        down = true
        pos_x = e.pageX
        pos_y = e.pageY
    },
    'mouseup': function() {
        down = false
    }
})


function highlight(el, callback) {
    var $el = $(el)
    $el.fadeTo('normal', 0, function() {
        $el.css('background-color', 'lime').fadeTo('slow', 1).fadeTo('slow', 0, function() {
            $el.css('background', 'transparent')
            $el.fadeTo('normal', 1)
            if (typeof(callback)!=='undefined') {
                callback()
            }
        })
    })
}


function scroll_to(el, duration, callback) {
    if (typeof(duration)==='undefined') {
        duration = 0
    }
    var $el = $(el)
    $('html, body').animate({
        'scrollTop': $el.offset().top-window.innerHeight/2+$el.height()/2,
        'scrollLeft': $el.offset().left-window.innerWidth/2+$el.width()/2
    }, {
        'duration': duration, 
        'complete': function() {
            if (typeof(callback)!=='undefined') {
                callback()
            }
        }
    })
}

var scroll = true
function scroll_to_hash(duration) {
    if (!scroll) {
        return
    }
    setTimeout(function() {
        var $el = $(window.location.hash)
        if ($el.length!=1) {
            return
        }
        scroll_to($el, duration)
        highlight($el)
    }, 1)
    return false
}

function scroll_and_hash(el, duration) {
    if (typeof(duration)==='undefined') {
        duration = 0
    }
    var top = $(window).scrollTop()
    var left = $(window).scrollLeft()
    scroll = false
    window.location.hash = $(el).attr('id')
    $(window).scrollTop(top)
    $(window).scrollLeft(left)
    setTimeout(function() {
        $(window).scrollTop(top)
        $(window).scrollLeft(left)
        scroll = true
        scroll_to(el, duration)
        highlight(el)
    }, 1)
}

$(function() {
    $('.entity').dblclick(function() {
        scroll_and_hash(this, 400)
    })
    $('.entity[href^="#"]').click(function(e) {
        if (e.preventDefault) {
            e.preventDefault()
        } else {
            e.stop()
        }
        var id = $(this).attr('href')
        scroll_and_hash($(id), 600)
    })


    $(window).load(function() {
        setTimeout(scroll_to_hash, 1)
    })
    $(window).on('hashchange', function() {
        scroll_to_hash()
    })
})
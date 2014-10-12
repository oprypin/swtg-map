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


function highlight(el) {
    var $el = $(el)
    $el.css('background-color', 'cyan').fadeTo('slow', 0).fadeTo('slow', 1, function() {
        $el.css('background', 'none')
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

$(function() {
    $('.room').dblclick(function() {
        window.location.hash = '#'+$(this).attr('id')
    })
    $('.entity[href^="#"]').click(function(e) {
        if (e.preventDefault) {
            e.preventDefault()
        } else {
            e.stop()
        }
        var id = $(this).attr('href')
        scroll_to(id, 100)
        highlight(id)
        scroll = false
        window.location.hash = id
        setTimeout(function() {
            scroll = true
        }, 1)
    })


    $(window).load(function() {
        setTimeout(scroll_to_hash, 1)
    })
    $(window).on('hashchange', function() {
        scroll_to_hash()
    })
})
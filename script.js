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
    $el = $(el)
    var $hl = $('<div class="highlight"/>').appendTo($el)
    var end_sz = ($el.width()+$el.height())/2
    var start_sz = end_sz+500
    var dims = function(sz) {
        return {
            left: $el.width()/2-sz/2,
            top: $el.height()/2-sz/2,
            width: sz,
            height: sz
        }
    }
    $hl.css(dims(end_sz+500))
    $hl.animate(dims(end_sz), {
        duration: 900,
        queue: false,
        complete: function() {
            $hl.animate(dims(end_sz+100), {
                duration: 200,
                queue: false,
                complete: function() {
                    $hl.remove()
                }
            })
        }
    })
    $hl.fadeTo(0, 0).fadeTo(300, 1).fadeTo(600, 0.5).fadeTo(200, 0)
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
        scroll_to($el, duration, function() {
            highlight($el)
        })
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
        scroll_to(el, duration, function() {
            highlight(el)
        })
    }, 1)
}

$(function() {
    $('.entity').dblclick(function() {
        scroll_and_hash(this, 400)
    })
    $('a[href^="#"]').click(function(e) {
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
        var $el = $('#header').clone()
        $el.css({
            position: 'fixed',
            top: 0,
            left: 0
        })
        $('body').append($el)
    })
    $(window).on('hashchange', function() {
        scroll_to_hash()
    })
})
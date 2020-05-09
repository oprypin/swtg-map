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

var $highlight = $('<div/>')
function highlight(el) {
    $el = $(el)
    $parent = $el.parent()
    $highlight.remove()
    $highlight = $('<div class="highlight"/>').appendTo($parent)
    var $hl = $highlight
    var end_sz = ($el.width()+$el.height())/2
    var dims = function(sz) {
        return {
            left: $el.position().left+$el.width()/2-sz/2,
            top: $el.position().top+$el.height()/2-sz/2,
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
                queue: false
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


var current_file = window.location.pathname
current_file = current_file.substring(current_file.lastIndexOf('/')+1)
current_file = current_file.substring(0, current_file.indexOf('.'))
var found_key = 'blaxpirit.swtg.found.'+current_file

function store_gems() {
    var found = []
    $('.entity.gem.found').each(function() {
        found.push($(this).attr('id'))
    })
    localStorage[found_key] = found.join(',')
}
function upd_gems() {
    if (localStorage[found_key]) {
        var found = localStorage[found_key].split(',')
        for (var i = 0; i<found.length; ++i) {
            $(document.getElementById(found[i])).addClass('found')
        }
    }
}

$(function() {
    $('.entity').click(function() {
        history.replaceState({}, '', '#'+this.id)
    })
    $('.entity').dblclick(function() {
        scroll_and_hash(this, 400)
    })
    $('.entity.gem').click(function() {
        $(this).toggleClass('found')
        store_gems()
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

    var $el = $('#header').clone()
    $el.css({
        position: 'fixed',
        top: 0,
        left: 0
    })
    $('body').append($el)

    setTimeout(scroll_to_hash, 1)
    $(window).on('hashchange', function() {
        scroll_to_hash()
    })

    upd_gems()
})

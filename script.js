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

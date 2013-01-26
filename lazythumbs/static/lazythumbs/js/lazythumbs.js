var lazythumbs = {
    FETCH_STEP_MIN: 50
};
(function(lazythumbs){

    function bind_event(eventname, callback) {
        if (window.addEventListener) {
            window.addEventListener(eventname, callback, false);
        } else {
            window.attachEvent('on' + eventname, callback);
        }
    }

    function data(el, name, value) {
        if (!!el.dataset) {
            if (typeof value !== 'undefined') {
                el.dataset[name] = value;
            } else {
                return el.dataset[name]
            }
        } else {
            if (typeof value !== 'undefined') {
                el.setAttribute('data-' + name, value);
            } else {
                return el.getAttribute('data-' + name);
            }
        }
    }
    
    function update_responsive_images(e) {

        var responsive_images = document.querySelectorAll('.lt-responsive-img');
        var img, i, width, height, needs_loaded, url_template, old_ratio, new_ratio, wdelta, hdelta, roundedsize;

        for (i=0; i < responsive_images.length; i++) {
            img = responsive_images[i];
            width = img.clientWidth;
            height = img.clientHeight;
            old_ratio = data(img, 'ltwidth') / data(img, 'ltheight');
            new_ratio = width / height;

            if (width===0 || height===0) {
                // The image is currently hidden
                continue;
            }

            // We want to load the image if this is the page load event
            // or if the image has increased in size.
            if (!data(img, 'ltmaxwidth')) {
                needs_loaded = true;
                data(img, 'ltmaxwidth', img.getAttribute('width'));
                data(img, 'ltmaxheight', img.getAttribute('height'));
            }

            roundedsize = round_size_up({width: width, height: height}, {width: data(img, 'ltmaxwidth'), height: data(img, 'ltmaxheight')});
            width = roundedsize.width;
            height = roundedsize.height;

            if (e.type !== 'load') {
                width = Math.min(width, data(img, 'ltmaxwidth'));
                height = Math.min(height, data(img, 'ltmaxheight'));
                wdelta = width - data(img, 'ltwidth');
                hdelta = height - data(img, 'ltheight');

                // Load new images when increasing by a large enough delta
                if (wdelta > lazythumbs.FETCH_STEP_MIN || hdelta > lazythumbs.FETCH_STEP_MIN) {
                    needs_loaded = true;
                }

                // Load new images when changing ratio
                if (Math.abs(old_ratio - new_ratio) > 0.1 && data(img, 'action') != 'resize') {
                    needs_loaded = true;
                }
            }

            if (needs_loaded) {
                url_template = data(img, 'urltemplate');
                url_template = url_template.replace('{{ action }}', data(img, 'action'));
                if (data(img, 'action') === 'thumbnail') {
                    url_template = url_template.replace('{{ dimensions }}', width);
                } else {
                    url_template = url_template.replace('{{ dimensions }}', width + '/' + height);
                }

                (function(existing_img) {
                    var new_image = new Image();
                    new_image.src = url_template;
                    new_image.onload = function() {
                        existing_img.src = new_image.src;  
                    }
                })(img);

                data(img, 'ltwidth', width);
                data(img, 'ltheight', height);
            }
        }
    };

    bind_event('load', setup_responsive_images, false);
    function setup_responsive_images() {
        if (this.removeEventListener) {
            this.removeEventListener('load', arguments.callee);
        } else if (this.detachEvent) {
            this.detachEvent('onload', arguments.callee);
        }

        var r = update_responsive_images.apply(this, arguments);
        bind_event("resize", update_responsive_images);
        return r;
    }

    function scale_size(size, scale) {
        return {
            width: parseInt(size.width / scale),
            height: parseInt(size.height / scale)
        }
    }

    function scale_from_step(size, step) {
        var d = Math.min(size.width, size.height);
        return (d + step) / d;
    }

    /* round_size_up(size, origsize)
     *
     * size     {width, height} of the requested image size
     * origsize  {width, height} or the original image size
     *
     * Produces a {width, height} result that is at least `size`, and
     * rounded up by the step value so that multiple requests for similar
     * sizes can request the same, cached size.
     */
    function round_size_up(size, origsize) {
        var ratio = size.width / size.height;

        // The largest size we would allow, in the ratio requested
        var candidate = {
            width: size.width<size.height ?
                origsize.width :
                origsize.height * ratio
        ,   height: size.height<size.width ?
                origsize.height :
                origsize.width / ratio
        };
        var scale = scale_from_step(origsize, lazythumbs.FETCH_STEP_MIN);
        var current = candidate;

        while (current.width >= size.width && current.height >= size.height) {
            // The one we're looking at is still larger, so step down
            candidate = current;
            current = scale_size(current, scale);
        }

        // Current is now too small, candidate is the next largest size.
        return candidate;
    }

    lazythumbs.scale_size = scale_size;
    lazythumbs.scale_from_step = scale_from_step;
    lazythumbs.round_size_up = round_size_up;

})(lazythumbs);

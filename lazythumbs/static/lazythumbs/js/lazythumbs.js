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
        var img, i, width, height, needs_loaded, url_template, old_ratio, new_ratio, wdelta, hdelta, roundedsize, matches;

        for (i=0; i < responsive_images.length; i++) {
            img = responsive_images[i];
            width = img.clientWidth;
            height = img.clientHeight;
            allow_undersized = false;

            aspectratio = data(img, 'aspectratio');
            if (aspectratio) {
                matches = /(\d+):(\d+)/.exec(aspectratio);
                old_ratio = matches[1] / matches[2];
                // We're not going to allow the aspect ratio to change.
                new_ratio = old_ratio;
                height = width * (1/old_ratio);
                allow_undersized = true;
            } else if (data(img, 'action') == 'matte') {
                // Since 'matte' will *probably* be requesting an image that's
                // larger than the underlying image (that's what the black
                // matte is for), we should not consult the image's maximum
                // dimensions before requesting a new image.
                allow_undersized = true;
            } else {
                old_ratio = data(img, 'ltwidth') / data(img, 'ltheight');
                new_ratio = width / height;
            }

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

            roundedsize = round_size_up(
                {width: width, height: height},
                {width: data(img, 'ltmaxwidth'), height: data(img, 'ltmaxheight')},
                allow_undersized
            );
            width = roundedsize.width;
            height = roundedsize.height;

            if (e.type !== 'load') {
                // Check if we're using a defined aspect ratio, if we aren't,
                // we need to make sure that we don't request an image that's
                // larger than the image actually is.
                if(! allow_undersized) {
                    width = Math.min(width, data(img, 'ltmaxwidth'));
                    height = Math.min(height, data(img, 'ltmaxheight'));
                }
                wdelta = Math.abs(width - data(img, 'ltwidth'));
                hdelta = Math.abs(height - data(img, 'ltheight'));

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
                    new_image.onload = function() {
                        existing_img.src = new_image.src;
                    }
                    new_image.src = url_template;
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
        bind_event("resize", debounce(update_responsive_images, 500));
        return r;
    }

    /* Prevents execution of a function more than once per `wait` ms.
     *
     * Note:
     *   This is lifted directly from http://davidwalsh.name/function-debounce,
     *   which itself lifted this code from an earlier version of Underscore.js
     *
     * func         The function to debounce.
     * wait         The size of the window (in milliseconds) during which only
     *              the *last* call of `func` will be executed.
     * immediate    Instead of executing only the *last* call of `func` during
     *              the `wait` window, execute the *first* call, and drop all
     *              other executions during the window.
     */
    function debounce(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) {
                    func.apply(context, args);
                }
            }
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) {
                func.apply(context, args);
            }
        };
    };

    function scale_size(size, scale) {
        return {
            width: parseInt(size.width / scale),
            height: parseInt(size.height / scale)
        }
    }

    /* scale_from_step(size, step)
     *
     * size     {width, height} of the image.
     * step     the step size by which the image should grow.
     *
     * Using an image's size, calculate the coefficient that one would
     * need to multiply the existing image's size by in order to grow
     * an image by `step` pixels.
     */
    function scale_from_step(size, step) {
        var d = Math.min(size.width, size.height);
        return (d + step) / d;
    }

    function get_first_candidate(size, origsize, allow_undersized) {
        var height = origsize.height;
        var width = origsize.width;
        var ratio = size.width / size.height;

        // The largest size we would allow, in the ratio requested
        if(allow_undersized) {
            // Continually increase our candidate image's dimensions
            // until the candidate is larger than our requested size.
            // The remainder will be filled with a black background.

            var current = origsize;
            var multiplier = 1;
            var scale = scale_from_step(origsize, lazythumbs.FETCH_STEP_MIN);

            while(
                current.width < size.width || current.height < size.height
            ) {
                // Note: Must use the reciprocal of the actual scale to
                // *increase* the image's size rather than decrease.
                current = scale_size(current, 1/Math.pow(scale, multiplier));
                multiplier++;
            }

            height = current.height
            width = current.width
        }

        return {
            width: (
                size.width < size.height ? width : parseInt(height * ratio)
            ),
            height: (
                size.height < size.width ? height : parseInt(width / ratio)
            )
        };
    }

    function round_size_up(size, origsize, allow_undersized) {
        if (flipper.is_active("D-01463")) {
            return round_size_up_without_multiplier(size, origsize, allow_undersized);
        }
        return round_size_up_with_multiplier(size, origsize, allow_undersized);
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
    function round_size_up_with_multiplier(size, origsize, allow_undersized) {
        var candidate = get_first_candidate(size, origsize, allow_undersized);
        var scale = scale_from_step(origsize, lazythumbs.FETCH_STEP_MIN);
        var current = candidate;
        var final_size = candidate;
        var multiplier = 1;

        // Overview:
        //   Starting from the image's current size, scale down in steps
        //   (using lazythumbs.FETCH_STEP_MIN) until we've found an image that
        //   is just barely *larger* than the size we need.
        while (current.width >= size.width && current.height >= size.height) {
            // We want to keep the size *right* *before* the last size we
            // encounter in this while loop; once the while loop breaks,
            // current will be *too* *small*, so let's save the previous value.
            final_size = current;
            // The one we're looking at is still larger, so step down
            current = scale_size(candidate, Math.pow(scale, multiplier));
            multiplier++;
        }
        return final_size;
    }

    function round_size_up_without_multiplier(size, origsize, allow_undersized) {
        var candidate = get_first_candidate(size, origsize, allow_undersized);
        var scale = scale_from_step(origsize, lazythumbs.FETCH_STEP_MIN);
        var current = candidate;

        while (current.width >= size.width && current.height >= size.height) {
            // with_multiplier's version ends up parseInt'ing the width and height
            // of the final return size (through the call to scale_size),
            // whereas this version ...
            // parseInt's the width and height of the size at each call
            // to scale_size.
            // This version is similar to the one in commit: d8c543 (lazythumbs repo)
            // before the next commit introduced the black matte borders in tease
            // images.
            candidate = current;
            current = scale_size(current, scale);
        }
        return candidate;
    }

    lazythumbs.scale_size = scale_size;
    lazythumbs.scale_from_step = scale_from_step;
    lazythumbs.round_size_up = round_size_up;

})(lazythumbs);

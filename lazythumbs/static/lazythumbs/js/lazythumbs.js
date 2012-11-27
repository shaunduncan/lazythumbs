var lazythumbs = {
    FETCH_STEP_MIN: 50
};
(function(lazythumbs){

    window.addEventListener("resize", update_responsive_images, false);
    function update_responsive_images(e) {

        var responsive_images = document.getElementsByClassName('lt-responsive-img');
        var img, i, width, height, needs_loaded, url_template;

        for (i=0; i < responsive_images.length; i++) {
            img = responsive_images[i];
            width = img.clientWidth;
            height = img.clientHeight;

            // We want to load the image if this is the page load event
            // or if the image has increased in size.
            if (e.type === 'load') {
                needs_loaded = true;
                img.dataset['ltmaxwidth'] = img.getAttribute('width');
                img.dataset['ltmaxheight'] = img.getAttribute('height');
            } else {
                width = Math.min(width, img.dataset['ltmaxwidth']);
                height = Math.min(height, img.dataset['ltmaxheight']);
                var wdelta = width - img.dataset['ltwidth'];
                var hdelta = height - img.dataset['ltheight'];
                if (wdelta > lazythumbs.FETCH_STEP_MIN || hdelta > lazythumbs.FETCH_STEP_MIN) {
                    needs_loaded = true;
                }
            }

            if (needs_loaded) {
                url_template = img.dataset['urltemplate'];
                url_template = url_template.replace('{{ action }}', img.dataset['action']);
                if (img.dataset['action'] === 'thumbnail') {
                    url_template = url_template.replace('{{ dimensions }}', width);
                } else {
                    url_template = url_template.replace('{{ dimensions }}', width + 'x' + height);
                }

                console.log("load", url_template);

                (function(existing_img) {
                    var new_image = new Image();
                    new_image.src = url_template;
                    new_image.onload = function() {
                        existing_img.src = new_image.src;  
                    }
                })(img);

                img.dataset['ltwidth'] = width;
                img.dataset['ltheight'] = height;
            }
        }
    };

    window.addEventListener('load', setup_responsive_images, false);
    function setup_responsive_images() {
        this.removeEventListener('load', arguments.callee);
        return update_responsive_images.apply(this, arguments);
    }

})(lazythumbs);

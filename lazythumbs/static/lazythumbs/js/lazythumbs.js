var lazythumbs = {};
(function(lazythumbs){

    window.addEventListener("resize", update_responsive_images, false);
    function update_responsive_images(e) {

        var responsive_images = document.getElementsByClassName('lt-responsive-img');
        var img, i, width, height, needs_loaded, url_template;

        console.log("Looking for responsive images...");

        for (i=0; i < responsive_images.length; i++) {
            img = responsive_images[i];
            width = img.clientWidth;
            height = img.clientHeight;

            if (e.type === 'load') {
                needs_loaded = true;
            } else {
                if (width > img.dataset['ltwidth'] || height > img.dataset['ltheight']) {
                    needs_loaded = true;
                }
            }

            if (needs_loaded) {
                url_template = img.dataset['urltemplate'];
                url_template = url_template.replace('{{ action }}', 'resize');
                url_template = url_template.replace('{{ width }}', width);
                url_template = url_template.replace('{{ height }}', height);

                console.log("load", url_template);

                (function(existing_img) {
                    var new_image = new Image();
                    new_image.src = url_template;
                    new_image.onload = function() {
                        existing_img.src = new_image.src;  
                    }
                })(img);
            }

            img.dataset['ltwidth'] = width;
            img.dataset['ltheight'] = height;
        }
    }

    window.addEventListener('load', setup_responsive_images, false);
    function setup_responsive_images() {
        this.removeEventListener('load', arguments.callee);
        return update_responsive_images.apply(this, arguments);
    }

})(lazythumbs);

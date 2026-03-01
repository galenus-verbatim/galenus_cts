/**
 * Do something with bâle chartier data
 */
const image = document.getElementById('image');
const div = document.getElementById('viewcont');
if (div) {
    // viewer override of resize
    Viewer.prototype.resize = function() {
        var _this3 = this;

        if (!this.isShown || this.hiding) {
            return;
        }

        if (this.fulled) {
            this.close();
            this.initBody();
            this.open();
        }

        this.initContainer();
        this.initViewer();
        this.renderViewer();
        this.renderList();

        if (this.viewed) {
            // do not resize image
            /*
            this.initImage(function() {
                _this3.renderImage();
            });
            _this3.options.viewed();
            */
        }

        if (this.played) {
            if (this.options.fullscreen && this.fulled && !(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement)) {
                this.stop();
                return;
            }

            forEach(this.player.getElementsByTagName('img'), function(image) {
                addListener(image, EVENT_LOAD, _this3.loadImage.bind(_this3), {
                    once: true
                });
                dispatchEvent(image, EVENT_LOAD);
            });
        }
    };

    /*
    var onViewed = function onViewed() {
        var imageData = _this2.imageData;
        var render = Array.isArray(options.title) ? options.title[1] : options.title;
        // EDIT 2022-04, keep html in titles
        title.innerHTML = isFunction(render) ? render.call(_this2, image, imageData) : "".concat(alt, " (").concat(imageData.naturalWidth, " \xD7 ").concat(imageData.naturalHeight, ")");
    };
    */

    Viewer.prototype.wheel = function(event) {
        var _this4 = this;
        if (!this.viewed) {
            return;
        }

        event.preventDefault(); // Limit wheel speed to prevent zoom too fast

        if (this.wheeling) {
            return;
        }

        this.wheeling = true;
        setTimeout(function() {
            _this4.wheeling = false;
        }, 50);
        var ratio = Number(this.options.zoomRatio) || 0.1;
        var delta = 1;

        if (event.deltaY) {
            delta = event.deltaY;
        } else if (event.wheelDelta) {
            delta = -event.wheelDelta;
        } else if (event.detail) {
            delta = event.detail;
        }
        this.move(0, -delta);
    };

    var pageViewer = new Viewer(div, {
        title: function(image) {
            // title sould not be html
            return image.alt;
        },
        title: false,
        transition: false,
        inline: true,
        navbar: 0,
        zIndex: 4,
        // minWidth: '100%', 
        toolbar: {
            width: function() {
                let cwidth = div.offsetWidth;
                let iwidth = pageViewer.imageData.naturalWidth;
                let zoom = cwidth / iwidth;
                pageViewer.zoomTo(zoom);
                pageViewer.moveTo(0, pageViewer.imageData.y);
            },
            zoomIn: true,
            zoomOut: true,
            oneToOne: true,
            reset: true,
        },
        viewed() {
            // default zoom on load, image width
            let cwidth = div.offsetWidth;
            let iwidth = pageViewer.imageData.naturalWidth;
            let zoom = cwidth / iwidth;
            pageViewer.zoomTo(zoom);
            pageViewer.moveTo(0, 0);
        },
    });

}
(function() {
    // loop on al image <span> to set events
    if (typeof imgkuhn !== 'undefined') wear(".pb", imgkuhn);
    if (typeof imgbale !== 'undefined') wear(".ed1page", imgbale);
    if (typeof imgchartier !== 'undefined') wear(".ed2page", imgchartier);
    // set the id of an image to load
    var id = false;
    do {
        if (!window.location.hash) {
            let el = document.querySelector(".pb");
            if (el) id = el.id;
            break;
        }
        id = window.location.hash.substring(1);
        let found = id.match(/^p\d+[a-b]\.\d+/);
        if (found) {
            id = found[0];
            break;
        }
        found = id.match(/^l\d+[a-b]\.\d+/);
        if (found) {
            id = 'p' + found[0].substring(1);
            break;
        }
    } while (false)


    /** Click on prev next image */
    function imagoViso(pdiff)
    {
        if (pageViewer.spanLast) pageViewer.spanLast.classList.remove("selected");
        image.pno = pad(parseInt(image.pno) + pdiff, 4);
        image.src = image.dat['url'].replace('%%', image.pno);
        pageViewer.update();
        pageViewer.resize();
    }

    let but = document.getElementById('image_prev');
    if (but) {
        but.onclick = function() {
            imagoViso(-1);
        }
    }
    but = document.getElementById('image_next');
    if (but) {
            but.onclick = function() {
            imagoViso(+1);
        }
    }

    // https://www.biusante.parisdescartes.fr/iiif/2/bibnum:00039x04:0038/full/max/0/default.jpg
    function wear(css, dat) {
        if (!dat) return;
        let els = document.querySelectorAll(css);
        for (let i = 0; i < els.length; ++i) {
            const span = els[i];
            if (!span.classList.contains('pb')) {
                const before = document.createElement("mark");
                before.className = "pbmark";
                span.parentNode.insertBefore(before, span);
            }
            let page = span.dataset.n;
            if (!page) page = span.dataset.page;
            // get the p int
            let p = parseInt(page.split('.').pop());

            let url;
            let pno;
            let text = '[';
            if (span.classList.contains('page1') || span.classList.contains('pbde')) {
                text += '…';
            }
            // build an url from a page number
            let pdiff = parseInt(dat['pdiff']);
            if (dat['pholes']) {
                for (const prop in dat['pholes']) {
                    if (p >= prop) {
                        pdiff = parseInt(dat['pholes'][prop]);
                    } else {
                        break;
                    }
                }
            }
            // if page number contains a dot, there’s already the volume name
            if (page.indexOf(".") < 0) {
                text += dat['vol'] + '.';
            }
            text += page + ' ' + dat['abbr'];
            // pad page number for biusante 
            pno = pad(p + pdiff, 4);
            url = dat['url'].replace('%%', pno);
            text += ']';
            span.innerText = text;
            span.classList.add("view");
            span.onclick = function() {
                if (pageViewer.spanLast) pageViewer.spanLast.classList.remove("selected");
                this.classList.add("selected");
                pageViewer.spanLast = this;
                image.pno = pno;
                image.dat = dat;
                image.src = url;
                let title = '';
                if (dat.title) title = text + ' source : ' + dat.title.replace('%%', pno);
                image.alt = title;
                const header = document.getElementById('image_title');
                if (header) header.innerHTML = title;
                pageViewer.update();
                pageViewer.resize();
            }
        }
    }

    const span = window.document.getElementById(id);
    if (span) {
        span.scrollIntoView({ block: "center" });
        span.click();
    }
    function pad(num, width) {
        var s = "000000000" + num;
        return s.substring(s.length - width);
    }
})();
(function() {
    const id = 'selnav';
    const select = document.getElementById(id);
    if (!select) return;

    function show(value) {
        console.log(value);
        if (!select.last) select.last = document.getElementById('titLat');
        const show = document.getElementById(value);
        if (!show) return;
        localStorage.setItem(id, value);
        select.last.style.display = 'none';
        select.last = show;
        show.style.display = 'block';
    }
    // on load last value
    window.addEventListener("load", function(e) {
        const value = localStorage.getItem(id);
        if (value) {
            select.value = value;
            show(value);
        }
    })
    select.addEventListener("change", function(e) {
        const value = select.value;
        show(value);
    });
}());
(function() {
    const navs = document.getElementById('navs');
    if (!navs) return;
    navs.addEventListener('click', function(e) {
        let a = selfOrAncestor(e.target, 'a');
        if (!a) return;
        if (document.lasta) document.lasta.classList.remove('selected');
        document.lasta = a;
        a.classList.add('selected');
    });

    function selfOrAncestor(el, name) {
        while (el.tagName.toLowerCase() != name) {
            el = el.parentNode;
            if (!el) return false;
            let tag = el.tagName.toLowerCase();
            if (tag == 'div' || tag == 'nav' || tag == 'body') return false;
        }
        return el;
    }
}());
/** Make line numbers selectable */
(function() {
    const main = document.querySelector('div.doc div.text');
    if (!main) return;
    main.addEventListener('copy', (event) => {
        helper = document.createElement("div");
        const selection = window.getSelection();
        rangeCount = selection.rangeCount;
        // selection is broken by pages breaks
        for (let i=0; i < rangeCount; i++) {
            helper.appendChild(
                selection.getRangeAt(i).cloneContents()
            );
        }
        // get the previous line break id
        const node = selection.getRangeAt(0).startContainer; // text node, start of selection
        var a = "";
        var ref = "";
        // TODO check if it is a page break
        var prev = node;
        do {
            prev = prev.previousSibling;
            if (!prev) break;
            if (prev.nodeType != 1) continue;
            if (!prev.classList.contains('lb')) continue;
            var url = prev.href;
            ref = '[' + prev.id.substring(1) + ' K]';
            a = '<a href="' + url + '">' + ref + '</a>';
            break;
        } while(true);

        event.clipboardData.setData("text/plain", `${ref} ${helper.innerText}`);
        event.clipboardData.setData("text/html", `${a} ${helper.innerHTML}`);
        event.preventDefault();
    });

}());

(function() {
    let lastScrollY = window.scrollY;
    const header = document.getElementById('header');
    // hide header on scroll
    window.addEventListener('scroll', (event) => {
        let scrollY = window.scrollY;
        if ( lastScrollY < scrollY) {
            header.classList.add("down");
            header.classList.remove("up");
        }
        // nothing for up
        /*
        else {
            header.classList.remove("down");
            header.classList.add("up");
        }
        */
        lastScrollY = scrollY;
    });
}());

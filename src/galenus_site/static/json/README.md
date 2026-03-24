# galenus_images.json — schema reference

This file maps early-printed edition facsimiles to their IIIF image sequences
on Medica (Université Paris Cité).  It is loaded by `reading.load_images_config`
and consumed by `reading.get_iiif_config`, which builds the JS config object
that `galenus.js` uses to attach clickable page-image links to edition
page-break spans in the reading view.

---

## Top-level structure

```json
{
  "<edition_key>": {
    "<volume>": { … per-volume config … },
    …
  },
  …
}
```

### Edition keys

| Key | Edition | JS variable | CSS selector on spans |
|---|---|---|---|
| `kuhn` | Kühn (1821–1833) | `imgkuhn` | `.pb` |
| `bale` | Bâle / Froben (1538) | `imgbale` | `.ed1page` |
| `chartier` | Chartier (1638–1679) | `imgchartier` | `.ed2page` |

`galenus.js` already handles `imgbale` and `imgchartier`; `app.py` currently
only emits `imgkuhn`.  Adding facsimile support for another edition requires
generating the corresponding JS variable from the appropriate edition key.

### Volume numbers

Volume numbers are **string keys** matching the volume field in Zotero (e.g.
`"1"`, `"2"`, `"17a"`, `"17b"`).  Not every edition covers every volume; omit
volumes that have no digitised facsimile.

---

## Per-volume config object

```json
{
  "pdiff":  <integer>,          // required
  "url":    "<template>",       // required
  "title":  "<html template>",  // required
  "pholes": { "<page>": <integer>, … }  // optional
}
```

### `pdiff` (integer, required)

The constant offset between an edition page number `p` and the physical image
index in the IIIF sequence.  `galenus.js` computes:

```
pno = pad(p + pdiff, 4)
url = vol_config.url.replace("%%", pno)
```

In practice this accounts for prefatory material (title pages, dedications,
tables) that appears before the numbered text pages in the digitised copy but
is not counted in the edition's own pagination.

**Example:** if the facsimile for Kühn vol. 1 has 265 unnumbered images before
edition page 1, set `"pdiff": 265`.

### `url` (string, required)

IIIF Image API URL template for the facsimile host.  The literal string `%%`
is replaced at runtime with the zero-padded 4-digit physical image index
computed from `p + pdiff`.

```
"url": "https://numerabilis.u-paris.fr/iiif/2/bibnum:45674x01:%%/full/full/0/default.jpg"
```

### `title` (string, required)

HTML fragment used as the caption and source link shown below the facsimile
viewer.  `%%` is replaced with the same padded image index so the link points
to the correct page on the host site.

```
"title": "<a target=\"_blank\" class=\"external\" href=\"https://numerabilis.u-paris.fr/histmed/medica/page?45674x01&p=%%\">Université Paris Cité, Bibliothèque numérique Medica</a>"
```

### `pholes` (object, optional)

An ordered map of `"edition_page_number": new_pdiff` pairs for volumes where
the offset between printed page numbers and physical image indices is not
uniform throughout the volume (e.g. because a fold-out plate or a missing page
shifts the count mid-volume).

`galenus.js` iterates the keys in insertion order and applies the last
`new_pdiff` whose key is ≤ the current page number `p`.  Before the first
matching key, the base `pdiff` value applies.

```json
"pholes": { "149": 21 }
```

This means: for pages < 149 use the base `pdiff`; for pages ≥ 149 use `21`
instead.

---

## Adding a new edition

1. Add a new top-level key (e.g. `"aldus"`) with one object per available
   volume.
2. For each volume, determine `pdiff` by finding a page whose printed number
   you know and counting back to image index 1.  Check a few pages across the
   volume; if the offset shifts, record the breakpoints in `pholes`.
3. Add the corresponding `abbr`, CSS selector, and JS variable name to
   `app.py` so the config is emitted to the template, and register it in
   `galenus.js` with `wear("<selector>", img<edition>)`.

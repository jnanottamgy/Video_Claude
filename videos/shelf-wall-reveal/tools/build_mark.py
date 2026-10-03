"""Cut the glass mark out of its navy plate for use on a light wall.

The source JPEG is glass rendered over navy, so its dark interior faces are
'navy seen through glass'. On a beige wall those must become 'wall seen
through glass' - a pale cool tint - not dark paint. And the plate's soft haze
around the mark must go entirely, or it reads as a smudge on the wall.
"""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

src = np.asarray(Image.open('assets/logo-src.jpg').convert('RGB')).astype(np.float64)
lum = 0.2126*src[:,:,0] + 0.7152*src[:,:,1] + 0.0722*src[:,:,2]

# silhouette of the glass body (rims seal the faces; fill what they enclose)
body = ndi.binary_closing(lum > 36, structure=np.ones((3,3)), iterations=2)
body = ndi.binary_fill_holes(body)
lab, n = ndi.label(body)
body = lab == (1 + int(np.argmax(ndi.sum(body, lab, range(1, n+1)))))

inside = ndi.distance_transform_edt(body)
outside = ndi.distance_transform_edt(~body)
edge = np.clip(0.5 + (inside - outside)/1.6, 0, 1)          # ~1px AA edge

lum_alpha = smoothstep(20, 60, lum)                          # lit glass -> opaque
interior = np.clip((inside - 2.5) / 4.0, 0, 1)               # 0 at the rim, 1 deep inside
alpha = edge * np.maximum(lum_alpha, 0.36 * interior)        # rim haze -> 0, faces -> tint

tint = np.array([138, 168, 220], dtype=np.float64)           # cool glass over a warm wall
w = (1 - smoothstep(25, 95, lum))[..., None]
rgb = (1 - w) * src + w * tint

x0,y0,x1,y1 = 133,100,542,573
pad = 18
out = np.dstack([rgb, alpha*255]).clip(0,255).astype(np.uint8)
Image.fromarray(out, 'RGBA').crop((x0-pad, y0-pad, x1+pad+1, y1+pad+1)).save('assets/mark.png')
m = np.asarray(Image.open('assets/mark.png'))[:,:,3]
print("assets/mark.png", Image.open('assets/mark.png').size,
      "opaque %.1f%%  translucent %.1f%%  clear %.1f%%" % ((m>250).mean()*100, ((m>5)&(m<=250)).mean()*100, (m<=5).mean()*100))

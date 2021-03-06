from PIL import Image
import potrace
import numpy as np
from Sand import PICTURE_PATH
from sandable import Sandable
from dialog import DialogFile, DialogInt, DialogFloat, DialogBreak
from Chains import Chains


class Sander(Sandable):
    """
### Turn a photograph or image into a sand drawing

#### Hints

Use the "Pictures" tab in the main navigation to more easily select photos.

#### Parameters

* **File Name** - name of the file to be drawn.  Files use a rudimentary file browser.
     Use the "Pictures" tab to more easily select pictures.
* **Turd Size** - size of the smallest "island" that is left in the image. Setting **Turd Size**
     to higher numbers will make the image smoother, less detailed, and faster to draw.
* **Number of Fill Iterations** - indicates how many shrunken-down drawings should be done inside the
     main image.  Each shrunken drawing is **Fill Decrement** away from the previous edge.  Details get
     lost as the fill image gets smaller. to completely fill in the image use higher numbers, the fill will
     automatically stop when it becomes too small (try 25).
* **Fill Decrement** - amount to shrink the outside image(s) by for the purpose of filling-in the drawing.
     The smaller the **Fill Decrement** is the tighter the lines are (try .25).
* **Height** - scale the resulting drawing to the specified height.
* **Width** and **Length** - how big the drawing should be. Probably not worth changing.
* **Starting locations** - where on the table the drawing should be drawn. Also normally not worth changing.
"""

    def __init__(self, width, length, ballSize, units):
        self.editor = [
            DialogFile("filename",            "File Name",                default=PICTURE_PATH, filter='.png|.jpg|.gif|.bmp'),
            DialogInt("turdSize",            "Turd Size",                default=40, min=0, max=1000),
            DialogInt("iterations",          "Number of Fill Iterations", default=0, min=0, max=100),
            DialogFloat("decrement",           "Fill Decrement",           units=units, default=0.5, min=0.0, max=10.0),
            DialogBreak(),
            DialogFloat("ballSize",            "Ball Size",                units=units, default=ballSize, min=0.25),
            DialogFloat("size",                "Height (Picture)",         units=units, default=length),
            DialogFloat("xOffset",             "X Origin",                 units=units, default=0.0),
            DialogFloat("yOffset",             "Y Origin",                 units=units, default=0.0),
            DialogFloat("width",               "Width (x)",                units=units, default=width, min=1.0, max=1000.0),
            DialogFloat("length",              "Length (y)",               units=units, default=length, min=1.0, max=1000.0),
        ]

    def generate(self, params):
        chains = []

        # Try to open the image file
        try:
            image = Image.open(params.filename)
            image.load()
        except Exception:
            return chains

        # Resize the image if it is too big (the detail can't be rendered anyway!)
        width, height = image.size
        if width > 800:
            factor = 800.0 / width
            image = image.resize((int(width * factor), int(height * factor)))

        # Remove the alpha channel (make it white)
        image = self._alphaToColor(image)

        # Convert image into a grayscale image
        image = image.convert('P', palette=Image.ADAPTIVE, colors=2)
        width, height = image.size

        pixels = [p % 2 for p in list(image.getdata())]
        data = [pixels[row*width:(row+1)*width] for row in range(height)]

        # Image is upside down, reverse it
        data.reverse()

        # Convert array into a bitmap and trace it
        bmp = potrace.Bitmap(np.array(data, np.uint32))
        path = bmp.trace(params.turdSize)

        # Tesselate the bezzier curves into straight lines
        chains = [[(p[0], p[1]) for p in curve.tesselate()] for curve in path]

        # Transform to 0,0, scale to 1", scale to height, transform to xOffset, yOffset
        chains = Chains.autoScaleCenter(chains, [(0., 0.), (params.width, params.length)])

        # Fill in the insides
        if params.iterations:
            import shrinky
            oldChains = chains
            for chain in shrinky.shrinky(oldChains, params.iterations, -params.decrement):
                chains += chain

        return Chains.scanalize(chains, params.xOffset, params.yOffset, params.width, params.length, 1.0 / params.ballSize)

    def _alphaToColor(self, image, color=(255, 255, 255)):
        if len(image.getbands()) == 4:
            i = np.array(image)
            r, g, b, a = np.rollaxis(i, axis=-1)
            r[a == 0] = color[0]
            g[a == 0] = color[1]
            b[a == 0] = color[2]
            return Image.fromarray(np.dstack([r, g, b]), 'RGB')
        return image

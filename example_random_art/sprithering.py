#!/usr/bin/env python
"""This script generates random colored pixel graphics.

A detailed blog post on this script can be found under
https://www.freecodecamp.org/news/how-to-create-generative-art-in-less-than-100-lines-of-code-d37f379859f/
"""

import getopt
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

__author__ = "Michael Wittmann and Eric Davidson"

__version__ = "1.0.0"
__maintainer__ = "Michael Wittmann"
__email__ = "michael.wittmann@tum.de"
__status__ = "Example"


def r():
    return random.randint(0, 255)


def rc():
    return r(), r(), r()


listSym = []


def create_square(border, draw, randColor, element, size):
    if element == int(size / 2):
        draw.rectangle(border, randColor)
    elif len(listSym) == element + 1:
        draw.rectangle(border, listSym.pop())
    else:
        listSym.append(randColor)
        draw.rectangle(border, randColor)


def create_invader(border, draw, size):
    x0, y0, x1, y1 = border
    squareSize = (x1 - x0) / size
    randColors = [rc(), rc(), rc(), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
    i = 1
    for y in range(0, size):
        i *= -1
        element = 0
        for x in range(0, size):
            topLeftX = x * squareSize + x0
            topLeftY = y * squareSize + y0
            botRightX = topLeftX + squareSize
            botRightY = topLeftY + squareSize
            create_square((topLeftX, topLeftY, botRightX, botRightY), draw, random.choice(randColors), element, size)
            if element == int(size / 2) or element == 0:
                i *= -1
                element += i


def main(size:int, invaders:int, imgSize:int, output_path:Path, samples:int):
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    origDimension = imgSize
    for n in range(0, samples):
        origImage = Image.new('RGB', (origDimension, origDimension))
        draw = ImageDraw.Draw(origImage)
        invaderSize = origDimension / invaders
        padding = invaderSize / size
        for x in range(0, invaders):
            for y in range(0, invaders):
                topLeftX = x * invaderSize + padding / 2
                topLeftY = y * invaderSize + padding / 2
                botRightX = topLeftX + invaderSize - padding
                botRightY = topLeftY + invaderSize - padding
                create_invader((topLeftX, topLeftY, botRightX, botRightY), draw, size)

        file_name =  f'{size}x{size}-{invaders}-{imgSize}-{time.time_ns()}.jpg'
        origImage.save(output_path.joinpath(file_name))

if __name__ == "__main__":
    output_folder: Path = Path('art')
    size: int = 15
    invaders: int = 30
    imgSize: int  = 3000
    samples:int = 20

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ho:g:i:s:n:', ['--output_dir=','--grid_size=', '--invaders=', '--img_size=', '--samples='])
    except getopt.GetoptError:
        print('sprithering.py -o <output_folder> -g <grid_size> -i <invaders> -s <img_size> -n <samples>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('sprithering.py -o <output_folder> -g <grid_size> -i <invaders> -s <img_size> -n <samples>')

        if opt in ('-o', '--output_dir='):
            output_folder = Path(arg)

        if opt in ('-i', '--invaders='):
            invaders = int(arg)

        if opt in ('-s', '--imgsize='):
            imgSize = int(arg)

        if opt in ('-g', '--grid_size='):
            size = int(arg)

        if opt in ('-n', '--samples='):
            samples = int(arg)


    main(size=size, invaders=invaders, samples=samples, imgSize=imgSize, output_path=output_folder)

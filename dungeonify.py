from cmath import cos, sin
import copy
import glob
from hashlib import new
from itertools import chain
import math
from operator import attrgetter
import random
from re import A, X
import sys
from unittest import case
import cairo
from cv2 import INTER_MAX
import numpy as np
from decimal import Decimal

from scipy import rand

from PIL import Image, ImageDraw

# outputs to "dungeonified.png"
from DungeonifyGenerators import GeneratorTypes


# File    : Dungeonify.py
# Classes : Dungeonify
# Author  : Adam Biggs (100197567)
# Date    : 18/05/2022
# Notes   : Is used to generate all image output of the various dungeonify stages.
#            


class Dungeonify:
    def __init__(self, structuresArray, roadsArray, inchesPerPixel, evaluateArea=False):
        self.evaluateAreaFlag = evaluateArea

        # remove the duplicate and unnessersary node
        for structure in structuresArray:
            structure['nodes'].pop(0)

        self.structuresArray = structuresArray
        self.roadsArray = roadsArray
        # New array used for dungeonified, after fitting nodes to grid has occurred
        self.newStructuresArray = []
        self.inchesPerPixel = inchesPerPixel

        self.zoomFactor = 1.0
        self.previousZoomFactor = 1.0
        self.border = 2  # grid squares
        self.assetSize = 0

    def updateZoomFactor(self, newZoom):
        # calculates the new multiply factor
        if newZoom < self.previousZoomFactor:
            self.zoomFactor = 1 / (self.previousZoomFactor - newZoom)
        else:
            self.zoomFactor = newZoom / self.previousZoomFactor
        self.previousZoomFactor = newZoom

    def calculateDistanceCoefficentBefore(self):
        totalsList = []
        for structure in self.structuresArray:
            originNode = structure['nodes'][0]
            total = 0
            for node in structure['nodes']:
                total += self.distanceBetweenNodes_xy(originNode, node)[0]
            totalsList.append(total)
        return totalsList

    def calculateDistanceCoefficentAfter(self):
        totalsList = []
        for structure in self.newStructuresArray:
            originNode = structure['nodes'][0]
            total = 0
            for node in structure['nodes']:
                total += self.distanceBetweenNodes_xy(originNode, node)[0]
            totalsList.append(total)
        return totalsList

    def generateNewImage(self):

        if not self.evaluateAreaFlag:
            self.calculateImageProperties(updateNodes=True)
        else:
            # False for calulating change in area of structures. This will break the display.
            self.calculateImageProperties(updateNodes=False)

        self.surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, int(self.imageWidth), int(self.imageHeight))
        self.ctx = cairo.Context(self.surface)
        # Rectangle(x0, y0, x1, y1)
        self.ctx.rectangle(0, 0, self.imageWidth, self.imageHeight)

    def generate(self, generatorType, zoomFactor):
        self.updateZoomFactor(zoomFactor)
        self.generateNewImage()

        switchOptions = {
            GeneratorTypes.selectedBuildings: self.drawSelectedStructures,
            GeneratorTypes.rotatedBuildings: self.drawRotatedStructures,
            GeneratorTypes.repositionedBuildings: self.redrawForDegreesStructures,
            GeneratorTypes.dungeonifiedBuildings: self.drawForDungeonified,
        }

        a = switchOptions[generatorType]()

    # TODO: think about instead just creating both image and image+grid on this one pass, then load each based on checkbox.
    def generate_grid(self, width=0, height=0):
        if width == 0 or height == 0:
            width = self.imageWidth
            height = self.imageHeight

        self.calculateImageProperties(updateNodes=False)

        inchesPerPixel_X = self.inchesPerPixel['horizontal'] / \
            self.previousZoomFactor
        inchesPerPixel_Y = self.inchesPerPixel['vertical'] / \
            self.previousZoomFactor

        totalInchesWidth = (inchesPerPixel_X * width) + (2 * self.border)
        totalInchesHeight = (inchesPerPixel_Y * height) + (2 * self.border)

        surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32, int(width), int(height))
        ctx = cairo.Context(surface)
        ctx.rectangle(0, 0, width, height)

        pat1 = cairo.SolidPattern(0, 0, 0, 0)
        pat2 = cairo.SolidPattern(0.4, 0.4, 1, 1)

        ctx.set_source(pat1)
        ctx.fill()
        ctx.set_source(pat2)
        ctx.set_line_width(1)

        for i in range(int(totalInchesWidth) + 1):
            ctx.move_to(i / inchesPerPixel_X, 0)
            ctx.line_to(i / inchesPerPixel_X, height)
        for i in range(int(totalInchesHeight) + 1):
            ctx.move_to(0,                  i / inchesPerPixel_Y)
            ctx.line_to(width,    i / inchesPerPixel_Y)
        ctx.stroke()

        surface.write_to_png("grid.png")

    def calculateImageProperties(self, updateNodes=False):
        offsetMultiplier = 0.0
        minX = sys.maxsize
        minY = sys.maxsize
        maxX = 0
        maxY = 0

        # Find the nodes which mark the area containing the structures.
        for structure in self.structuresArray:
            for currentNode in structure['nodes']:
                if currentNode['x'] > maxX:
                    maxX = currentNode['x']
                if currentNode['y'] > maxY:
                    maxY = currentNode['y']
                if currentNode['x'] < minX:
                    minX = currentNode['x']
                if currentNode['y'] < minY:
                    minY = currentNode['y']

        # so that there is at least a little border around the buildings of free space.
        minX = minX - minX * offsetMultiplier
        minY = minY - minY * offsetMultiplier
        maxX = maxX + maxX * offsetMultiplier
        maxY = maxY + maxY * offsetMultiplier

        self.pixelsPerGridSquare = self.roundNearest(
            1 / (self.inchesPerPixel['horizontal'] / self.previousZoomFactor), 1)

        self.borderPixels = self.border * self.pixelsPerGridSquare

        self.imageWidth = int(maxX - minX) * \
            self.zoomFactor + (2 * self.borderPixels)
        self.imageHeight = int(maxY - minY) * \
            self.zoomFactor + (2 * self.borderPixels)

        # round pixel coordinate to nearest pixelsPerGridSquare.
        self.imageWidth = self.roundUp(
            self.imageWidth, self.pixelsPerGridSquare)
        self.imageHeight = self.roundUp(
            self.imageHeight, self.pixelsPerGridSquare)

        self.totalInchesWidth = self.inchesPerPixel['horizontal'] * \
            self.imageWidth
        self.totalInchesHeight = self.inchesPerPixel['vertical'] * \
            self.imageHeight

        if updateNodes:
            for structure in self.structuresArray:
                for node in structure['nodes']:
                    node['x'] = (node['x'] - minX) * self.zoomFactor
                    node['y'] = (node['y'] - minY) * self.zoomFactor

    def drawSelectedStructures(self, fileName="basic.png"):
        pat = cairo.SolidPattern(1, 1, 1, 1)
        self.ctx.set_source(pat)
        self.ctx.fill()

        for structure in self.structuresArray:
            for currentNode in structure['nodes']:
                self.ctx.line_to(
                    currentNode['x'] + self.borderPixels, currentNode['y'] + self.borderPixels)

            self.ctx.move_to(0, 0)
            self.ctx.close_path()

            colourHexOutline = '0000FF'
            r = int(colourHexOutline[0:2], 16) / 256
            g = int(colourHexOutline[2:4], 16) / 256
            b = int(colourHexOutline[4:6], 16) / 256

            self.ctx.set_source_rgb(r, g, b)  # Solid color
            self.ctx.fill()
            self.ctx.set_line_width(2 / self.imageWidth)
            self.ctx.stroke()

        self.surface.write_to_png(fileName)  # Output to PNG

    def calculateStructureCentroid(self, nodes):
        xCoordinates = [vertex['x'] for vertex in nodes]
        yCoordinates = [vertex['y'] for vertex in nodes]
        x = sum(xCoordinates) / len(nodes)
        y = sum(yCoordinates) / len(nodes)
        return {'x': x, 'y': y}

    def drawRotatedStructures(self):
        pat = cairo.SolidPattern(1, 1, 1, 1)
        self.ctx.set_source(pat)
        self.ctx.fill()

        # rotate all nodes
        rotatedNode = {'x': -1, 'y': -1}

        for structure in self.structuresArray:

            originNode = self.calculateStructureCentroid(
                structure['nodes'])

            # Calculate which node pair is the longest distance, so that we can base the rotation angle on it.
            structureAngle = self.angleOfLongestDistanceBetweenNodes(
                structure['nodes'])

            for index in range(len(structure['nodes'])):
                currentNode = structure['nodes'][index]

                # rotatedNode = self.rotate_point(currentNode, angle, (firstNode['x'], firstNode['y']))
                rotatedNode = self.rotateNode(
                    originNode, currentNode, structureAngle)

                self.ctx.line_to(
                    rotatedNode['x'] + self.borderPixels, rotatedNode['y'] + self.borderPixels)

                structure['nodes'][index] = rotatedNode

            self.ctx.move_to(0, 0)
            self.ctx.close_path()

            colourHexOutline = '0000FF'
            r = int(colourHexOutline[0:2], 16) / 256
            g = int(colourHexOutline[2:4], 16) / 256
            b = int(colourHexOutline[4:6], 16) / 256

            self.ctx.set_source_rgb(r, g, b)  # Solid color
            self.ctx.fill()
            self.ctx.set_line_width(2 / self.imageWidth)
            self.ctx.stroke()

        self.generateNewImage()
        self.drawSelectedStructures("rotated.png")

    def rotateAllNodes(self, structure):
        inchCorrectedNode = {'x': 0, 'y': 0}

        newStructure = {'nodes': [],
                        'speciality': structure['speciality']}

        currentNode = structure['nodes'][0]

        inchCorrectedNode['x'] = self.roundToNearestInch(
            currentNode['x'])
        inchCorrectedNode['y'] = self.roundToNearestInch(
            currentNode['y'])

        newStructure['nodes'].append(inchCorrectedNode)
        # still -2 as we just added two extras to the end
        for index in range(len(structure['nodes']) - 1):
            nextNode = structure['nodes'][index + 1]
            # nextNextNode = newStructure['nodes'][index + 2]
            # Round nextNode nearest inch here too?
            # angle = self.angleForTwoNodes2(currentNode, nextNode, nextNextNode)
            #angle = self.angleForTwoNodes3(currentNode, nextNode)
            angle = self.angleForTwoNodes(currentNode, nextNode)
            # northNode = {'x': currentNode['x'], 'y': currentNode['y'] - 1}
            # angle1 = self.angleForThreeNodes(northNode, currentNode, nextNode)
            # angle between the vector and the horizontal or vertical - whichever is longer.
            # angle = self.angleForTwoNodes(nextNode, currentNode)

            # TODO: make the round to nearest inch calc occur within rotating the node as this may fix the error with diagonal nodes.
            rotatedNode = self.rotateNode(currentNode, nextNode, angle)
            inchCorrectedNode = {'x': 0, 'y': 0}
            inchCorrectedNode['x'] = self.roundToNearestInch(
                rotatedNode['x'])
            inchCorrectedNode['y'] = self.roundToNearestInch(
                rotatedNode['y'])
            # self.ctx.line_to(rotatedNode['x'] + self.borderPixels, rotatedNode['y'] + self.borderPixels)
            newStructure['nodes'].append(inchCorrectedNode)
            currentNode = inchCorrectedNode

        return newStructure

    def removeDuplicateNodes(self, structure):
        newStructure = {'nodes': [],
                        'speciality': structure['speciality']}

        for nodeIndex in range(len(structure['nodes']) - 1):
            if structure['nodes'][nodeIndex] != structure['nodes'][nodeIndex + 1]:
                newStructure['nodes'].append(structure['nodes'][nodeIndex])

        if structure['nodes'][len(structure['nodes']) - 1] != structure['nodes'][0]:
            newStructure['nodes'].append(
                structure['nodes'][len(structure['nodes']) - 1])

        return newStructure

    def simplifyNodes(self, structure):
        tempStructure = self.removeDuplicateNodes(structure)

        newStructure = {'nodes': [],
                        'speciality': tempStructure['speciality']}
        newStructure = copy.deepcopy(tempStructure)

        # Remove the center node of a collection of three, if the middle node is exactly horizontally or vertically between them.
        # i.e. it adds no value.

        for index in range(0, len(tempStructure['nodes']) - 2):
            currentNode = tempStructure['nodes'][index]
            nextNode = tempStructure['nodes'][index + 1]
            nextNextNode = tempStructure['nodes'][index + 2]

            if (currentNode['x'] == nextNode['x'] == nextNextNode['x']) or \
                    (currentNode['y'] == nextNode['y'] == nextNextNode['y']):
                newStructure['nodes'].remove(nextNode)

        # if (tempStructure['nodes'][index]['x'] == tempStructure['nodes'][index + 1]['x'] == tempStructure['nodes'][index + 2]['x']) or \
        #         (tempStructure['nodes'][index]['y'] == tempStructure['nodes'][index + 1]['y'] == tempStructure['nodes'][index + 2]['y']):
        #     newStructure['nodes'].remove(tempStructure['nodes'][index + 1])

        # if (tempStructure['nodes'][index + 1]['x'] == tempStructure['nodes'][index + 2]['x'] == tempStructure['nodes'][0]['x']) or \
        #         (tempStructure['nodes'][index + 1]['y'] == tempStructure['nodes'][index + 2]['y'] == tempStructure['nodes'][0]['y']):
        #     newStructure['nodes'].remove(tempStructure['nodes'][index + 2])

        tempStructure['nodes'].append(tempStructure['nodes'][0])
        tempStructure['nodes'].append(tempStructure['nodes'][1])
        tempStructure['nodes'].append(tempStructure['nodes'][2])

        return newStructure

    def fillNodeGaps(self, structure):
        newStructure = {'nodes': [],
                        'speciality': structure['speciality']}
        #fill in gaps

        # structure['nodes'].append(structure['nodes'][0])
        for index in range(0, len(structure['nodes']) - 1):
            currentNode = structure['nodes'][index]
            nextNode = structure['nodes'][index + 1]

            if currentNode['x'] != nextNode['x'] and currentNode['y'] != nextNode['y']:
                newNode = currentNode
                newNode['y'] = nextNode['y']
                newStructure['nodes'].append(newNode)
            newStructure['nodes'].append(currentNode)

        # newStructure['nodes'].append(
        #     structure['nodes'][len(structure['nodes']) - 1])

        if structure['nodes'][len(structure['nodes']) - 1]['x'] != structure['nodes'][0]['x'] \
                and structure['nodes'][len(structure['nodes']) - 1]['y'] != structure['nodes'][0]['y']:

            if structure['nodes'][len(structure['nodes']) - 3]['x'] == structure['nodes'][len(structure['nodes']) - 2]['x']:
                newNode = structure['nodes'][len(structure['nodes']) - 1]
                newNode['x'] = structure['nodes'][0]['x']
                newStructure['nodes'].append(newNode)
            elif structure['nodes'][len(structure['nodes']) - 3]['y'] == structure['nodes'][len(structure['nodes']) - 2]['y']:
                newNode = structure['nodes'][len(structure['nodes']) - 1]
                newNode['y'] = structure['nodes'][0]['y']
                newStructure['nodes'].append(newNode)
        else:
            newStructure['nodes'].append(
                structure['nodes'][len(structure['nodes']) - 1])

        # newStructure['nodes'].append(newStructure['nodes'][0])

        return newStructure

    def fixIncorrectRounding(self, structure):
        # newStructure = {'nodes': [],
        #         'speciality': structure['speciality']}

        # Move nodes which have incorrectly rounded to the wrong nearest inch, forming a non-perpendicular
        structure['nodes'].append(
            structure['nodes'][0])
        for index in range(0, len(structure['nodes']) - 2):
            currentNode = structure['nodes'][index]
            nextNode = structure['nodes'][index + 1]
            nextNextNode = structure['nodes'][index + 2]

            x1 = nextNode['x'] - currentNode['x']
            y1 = nextNode['y'] - currentNode['y']

            if not (x1 == 0 or y1 == 0):
                if abs(x1) < abs(y1):
                    if nextNextNode['x'] == nextNode['x']:
                        nextNextNode['x'] = currentNode['x']
                    nextNode['x'] = currentNode['x']
                elif abs(x1) > abs(y1):
                    if nextNextNode['y'] == nextNode['y']:
                        nextNextNode['y'] = currentNode['y']
                    nextNode['y'] = currentNode['y']
                else:
                    raise Exception(
                        "Exception: CurrentNode and NextNode equal in redrawForDegreesStructures")

            return structure

    def orderNodesToLongest(self, structure):
        node1, node2 = self.nodePairOfLongestDistanceBetweenNodes(
            structure['nodes'])

        nodeIndex = structure['nodes'].index(node1)

        newStructure = {'nodes': structure['nodes'][nodeIndex:] +
                        structure['nodes'][:nodeIndex], 'speciality': structure['speciality']}
        newStructure['nodes'].append(newStructure['nodes'][0])

        return newStructure

    def roundNodesToNearestInch(self, structure):
        newStructure = {'nodes': [],
                        'speciality': structure['speciality']}

        for node in structure['nodes']:
            newNode = {'x': 0, 'y': 0}
            newNode['x'] = self.roundToNearestInch(
                node['x'])
            newNode['y'] = self.roundToNearestInch(
                node['y'])

            newStructure['nodes'].append(newNode)

        return newStructure

    def fixNegativeNodes(self, structure):
        minX = min(structure['nodes'], key=lambda x: x['x'])[
            'x']
        minY = min(structure['nodes'], key=lambda x: x['y'])[
            'y']

        if minX < 0:
            for node in structure['nodes']:
                node['x'] += abs(minX)
        if minY < 0:
            for node in structure['nodes']:
                node['y'] += abs(minY)

        return structure

    def redrawForDegreesStructures(self):
        pat = cairo.SolidPattern(1, 1, 1, 1)
        self.ctx.set_source(pat)
        self.ctx.fill()

        # rotate odd angles
        rotatedNode = {'x': -1, 'y': -1}
        originNode = {'x': 0, 'y': 0}

        for structure in self.structuresArray:
            tempStructure = structure

            # currentStructure = self.roundNodesToNearestInch(tempStructure)
            # tempStructure = currentStructure

            # currentStructure = self.orderNodesToLongest(tempStructure)
            # tempStructure = currentStructure

            currentStructure = self.removeDuplicateNodes(structure)
            tempStructure = currentStructure

            currentStructure = self.rotateAllNodes(tempStructure)
            tempStructure = currentStructure

            currentStructure = self.simplifyNodes(tempStructure)
            tempStructure = currentStructure

            currentStructure = self.fixNegativeNodes(tempStructure)
            tempStructure = currentStructure

            currentStructure = self.fillNodeGaps(tempStructure)
            tempStructure = currentStructure

            # currentStructure = self.fixIncorrectRounding(tempStructure)
            # tempStructure = currentStructure

            # Make the structure a node cycle
            currentStructure['nodes'].append(currentStructure['nodes'][0])

            b = 0
            for index in range(len(currentStructure['nodes']) - 1):
                currentNode = currentStructure['nodes'][index]

                self.ctx.line_to(
                    currentNode['x'] + self.borderPixels, currentNode['y'] + self.borderPixels)

            self.newStructuresArray.append(currentStructure)

            self.ctx.move_to(0, 0)
            self.ctx.close_path()

            colourHexOutline = '0000FF'
            r = int(colourHexOutline[0:2], 16) / 256
            g = int(colourHexOutline[2:4], 16) / 256
            b = int(colourHexOutline[4:6], 16) / 256

            self.ctx.set_source_rgb(r, g, b)  # Solid color
            self.ctx.fill()
            self.ctx.set_line_width(2 / self.imageWidth)
            self.ctx.stroke()

        self.surface.write_to_png("AnglesRule.png")  # Output to PNG
        # self.surface.write_to_png("dungeonify.png")  # Output to PNG

    def create_blank(self, width, height, rgb_color=(0, 0, 0)):
        """Create new image(numpy array) filled with certain color in RGB"""
        # Create black blank image
        image = np.zeros((height, width, 3), np.uint8)

        # Since OpenCV uses BGR, convert the color first
        color = tuple(reversed(rgb_color))
        # Fill image with color
        image[:] = color

        return image

    def loadAWallAsset(self, url, needRotate=True):
        try:
            asset = Image.open(url)
        except:
            raise FileNotFoundError(f"No asset Found in '{url}'")

        asset.resize((int(self.pixelsPerGridSquare),
                     int(self.pixelsPerGridSquare)))

        if not needRotate:
            return asset
        else:
            return asset.rotate(90.0)

    def loadWallAssets(self, path):
        assetList = []
        for filename in glob.glob(path):  # assuming gif
            asset = Image.open(filename)
            asset.resize((int(self.pixelsPerGridSquare),
                         int(self.pixelsPerGridSquare)))

            assetList.append(asset)

        if len(assetList) == 0:
            raise FileNotFoundError(f"No assets Found in '{path}'")

        return assetList

    def loadAFloorAsset(self, url):
        try:
            floor = Image.open(url)
        except:
            raise FileNotFoundError(f"No asset Found in '{url}'")

        # pillar.resize((pixelsPerGridSquareInt,pixelsPerGridSquareInt))

        # The width and height of the background tile
        floorWidth, floorHeight = floor.size

        # Creates a new empty image, RGB mode, and size 1000 by 1000
        floorImage = Image.new('RGB', (int(self.imageWidthSquares * int(self.pixelsPerGridSquare)),
                               int(self.imageHeightSquares * int(self.pixelsPerGridSquare))))

        # The width and height of the new image
        w, h = floorImage.size

        # Iterate through a grid, to place the background tile
        for i in range(0, w, floorWidth):
            for j in range(0, h, floorHeight):
                # Change brightness of the images, just to emphasise they are unique copies
                # floor_grass = Image.eval(floor_grass, lambda x: x+(i+j)/1000)

                # paste the image at location i, j:
                floorImage.paste(floor, (i, j))

        # floorImage.show()
        return floorImage

    def loadFloorAssets(self, path):
        assetList = []
        for filename in glob.glob(path):  # assuming gif
            floor = Image.open(filename)
            # pillar.resize((pixelsPerGridSquareInt,pixelsPerGridSquareInt))
            # The width and height of the background tile
            floorWidth, floorHeight = floor.size
            # Creates a new empty image, RGB mode, and size 1000 by 1000
            floorImage = Image.new('RGB', (int(self.imageWidthSquares * int(
                self.pixelsPerGridSquare)), int(self.imageHeightSquares * int(self.pixelsPerGridSquare))))
            # The width and height of the new image
            w, h = floorImage.size
            # Iterate through a grid, to place the background tile
            for i in range(0, w, floorWidth):
                for j in range(0, h, floorHeight):
                    # Change brightness of the images, just to emphasise they are unique copies
                    # floor_grass = Image.eval(floor_grass, lambda x: x+(i+j)/1000)
                    # paste the image at location i, j:
                    floorImage.paste(floor, (i, j))
            # floorImage.show()
            assetList.append(floorImage)

        if len(assetList) == 0:
            raise FileNotFoundError(f"No assets Found in {path}")
        return assetList

    def generateAssetsBetweenNodes(self, orientation, addDoor, enableWindows, internalWallNodeIndex, currentNode, nextNode, iterator):
        if orientation == 'horizontal':
            start = currentNode['x']
            end = nextNode['x']
            alternate = currentNode['y']

            wallAsset = self.currentStructureAssets['wall'].rotate(90.0)
            doorAsset = self.currentStructureAssets['door']
            if enableWindows:
                windowAsset = self.currentStructureAssets['window']
                sillAsset = self.currentStructureAssets['sill']
        else:
            start = currentNode['y']
            end = nextNode['y']
            alternate = currentNode['x']

            wallAsset = self.currentStructureAssets['wall']
            doorAsset = self.currentStructureAssets['door'].rotate(90.0)
            if enableWindows:
                windowAsset = self.currentStructureAssets['window'].rotate(
                    90.0)
                sillAsset = self.currentStructureAssets['sill'].rotate(90.0)

        doorPosition = -1
        if addDoor:
            # ???
            if abs(start) < abs(end):
                doorPosition = random.randint(
                    start + iterator, end - 2 * iterator)
            else:
                doorPosition = random.randint(
                    end - iterator, start + 2 * iterator) + 1  # Fixed Bug

        constantCoordinate = (
            alternate * int(self.pixelsPerGridSquare)) + int(self.pixelsPerGridSquare / 2)

        lastGenerated = 'Wall'
        for i in range(start, end, +iterator):
            varyingCoordinate = (i * int(self.pixelsPerGridSquare)) + \
                (int(self.pixelsPerGridSquare) if iterator == 1 else 0)

            if (orientation == 'horizontal'):
                currentPoint = (varyingCoordinate, constantCoordinate)

                if start < end:
                    decreaseOffsetX = self.assetSize
                else:
                    decreaseOffsetX = 0

                decreaseOffsetY = 0
            else:
                currentPoint = (constantCoordinate, varyingCoordinate)
                if start < end:
                    decreaseOffsetY = self.assetSize
                else:
                    decreaseOffsetY = 0

                decreaseOffsetX = 0

            if i != start and i != end - iterator:
                # not ends of wall, so can put door or window instead
                rand = random.randint(0, 6)

                # #testing
                # if internalWallNodeIndex != None:
                #     if i in [internalWallNodeIndex - (2 * iterator), internalWallNodeIndex - (3 * iterator)]:
                #         self.new_image.paste(sillAsset.rotate(45.0),currentPoint, mask=windowAsset.rotate(45.0))

                if i == doorPosition:
                    # 1/6
                    # Build a door
                    currentVTTPoint = {'node': {'x': int((currentPoint[0] - decreaseOffsetX) / self.assetSize), 'y': int(
                        (currentPoint[1] - decreaseOffsetY) / self.assetSize)}, 'type': 'Door'}
                    self.vttStructure.append(currentVTTPoint)
                    self.new_image.paste(
                        doorAsset, currentPoint, mask=doorAsset)
                    # only one door.
                    lastGenerated = 'Door'
                elif (rand <= 1 and enableWindows) and (i not in [doorPosition, doorPosition - 1, doorPosition + 1]):
                    # elif (rand <= 1 and enableWindows):
                    # 2/6
                    # Build a window

                    if lastGenerated != 'Window':
                        # if building down or right add one to that
                        currentVTTPoint = {'node': {'x': int((currentPoint[0] - decreaseOffsetX) / self.assetSize), 'y': int(
                            (currentPoint[1] - decreaseOffsetY) / self.assetSize)}, 'type': 'Window'}
                        self.vttStructure.append(currentVTTPoint)
                    self.new_image.paste(
                        sillAsset, currentPoint, mask=sillAsset)
                    self.new_image.paste(
                        windowAsset, currentPoint, mask=windowAsset)
                    # if next node is in the same direction as this one was then remove current node from list.

                    lastGenerated = 'Window'
                else:

                    # 3/6
                    # Build a wall anyway
                    if lastGenerated != 'Wall':

                        currentVTTPoint = {'node': {'x': int((currentPoint[0] - decreaseOffsetX) / self.assetSize), 'y': int(
                            (currentPoint[1] - decreaseOffsetY) / self.assetSize)}, 'type': 'Wall'}
                        self.vttStructure.append(currentVTTPoint)

                    self.new_image.paste(
                        wallAsset, currentPoint, mask=wallAsset)

                    lastGenerated = 'Wall'
            else:
                if lastGenerated != 'Wall':
                    if not (iterator == 1 and i == end - iterator):
                        currentVTTPoint = {'node': {'x': int(
                            currentPoint[0] / self.assetSize), 'y': int(currentPoint[1] / self.assetSize)}, 'type': 'Wall'}
                    else:
                        currentVTTPoint = {'node': {'x': int((currentPoint[0] - decreaseOffsetX) / self.assetSize), 'y': int(
                            (currentPoint[1] - decreaseOffsetY) / self.assetSize)}, 'type': 'Wall'}

                    self.vttStructure.append(currentVTTPoint)
                self.new_image.paste(wallAsset, currentPoint, mask=wallAsset)

                lastGenerated = 'Wall'

        if len(self.vttStructure) > 0:
            if self.vttStructure[-1] != {'node': {'x': int(nextNode['x']), 'y': int(nextNode['y'])}, 'type': 'Wall'}:
                self.vttStructure.append({'node': nextNode, 'type': 'Wall'})

    # def calculatePerimeterLength(self, structure):
    #     totalDistance = 0
    #     for index in range(len(structure) - 1):
    #         currentNode = structure[index]
    #         nextNode = structure[index + 1]

    #         xDifferent = nextNode['x'] - currentNode['x']
    #         yDifferent = nextNode['y'] - currentNode['y']

    #         totalDistance += abs(xDifferent) + abs(yDifferent)

    #     return totalDistance

    def calculateStructureAreasBefore(self):
        structuresAreaArray = []
        for structure in self.structuresArray:
            area = self.calcPolygonArea(structure['nodes'])
            structuresAreaArray.append(area)
        return structuresAreaArray

    def calculateStructureAreasAfter(self):
        structuresAreaArray = []
        for structure in self.newStructuresArray:
            area = self.calcPolygonArea(structure['nodes'])
            structuresAreaArray.append(area)
        return structuresAreaArray

    def polyArea(self, structureNodesArray):  # xCoordinates,yCoordinates
        xValues = np.array([p[0] for p in structureNodesArray])
        yValues = np.array([p[1] for p in structureNodesArray])
        indexes = np.arange(len(xValues))
        # positive if the vertex sequence is counterclockwise
        area = np.abs(np.sum(
            xValues[indexes-1]*yValues[indexes]-xValues[indexes]*yValues[indexes-1])*0.5)

        return area

        # return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

    def calcPolygonArea(self, structureNodes):
        structureNodesArray = []

        for node in structureNodes:
            structureNodesArray.append((node['x'], node['y']))

        return self.polyArea(structureNodesArray)

    def findWallWhichContainsNode(self, structureNodes, searchNode):
        for nodeIndex in range(len(structureNodes) - 1):
            currentNode = structureNodes[nodeIndex]
            nextNode = structureNodes[nodeIndex + 1]

            xDifferent = nextNode['x'] - currentNode['x']
            yDifferent = nextNode['y'] - currentNode['y']

            if xDifferent != 0:
                #change in x
                iterator = int(math.copysign(1, xDifferent))

                start = currentNode['x']
                end = nextNode['x']
                constantCoordinate = currentNode['y']

                for varyingCoordinate in range(start, end, +iterator):
                    if {'x': varyingCoordinate, 'y': constantCoordinate} == searchNode:
                        return currentNode, nextNode

            elif yDifferent != 0:
                #change in y
                iterator = int(math.copysign(1, yDifferent))

                start = currentNode['y']
                end = nextNode['y']
                constantCoordinate = currentNode['x']

                for varyingCoordinate in range(start, end, +iterator):
                    if {'x': constantCoordinate, 'y': varyingCoordinate} == searchNode:
                        return currentNode, nextNode

    def nodesBetweenTwoNodes(self, orientation, currentNode, nextNode, iterator):
        nodes = []

        if orientation == 'horizontal':
            start = currentNode['x']
            end = nextNode['x']
            constantCoordinate = currentNode['y']
        else:
            start = currentNode['y']
            end = nextNode['y']
            constantCoordinate = currentNode['x']

        lastGenerated = 'Wall'
        for varyingCoordinate in range(start, end, +iterator):
            if (orientation == 'horizontal'):
                nodes.append({'x': varyingCoordinate, 'y': constantCoordinate})
            else:
                nodes.append({'x': constantCoordinate, 'y': varyingCoordinate})

        return nodes

    def getAllNodes(self, structureNodes):
        allNodes = []
        for index in range(len(structureNodes) - 1):
            currentNode = structureNodes[index]
            nextNode = structureNodes[index + 1]

            xDifferent = nextNode['x'] - currentNode['x']
            yDifferent = nextNode['y'] - currentNode['y']

            if xDifferent != 0:
                #change in x
                iterator = int(math.copysign(1, xDifferent))
                allNodes.extend(self.nodesBetweenTwoNodes(
                    'horizontal', currentNode, nextNode, iterator))

            elif yDifferent != 0:
                #change in y
                iterator = int(math.copysign(1, yDifferent))
                allNodes.extend(self.nodesBetweenTwoNodes(
                    'vertical', currentNode, nextNode, iterator))

        return allNodes

        # allNodes = []
        # allNodes.append(room[0])
        # for nodeIndex in range(len(room) - 1):
        #     currentNode = room[nodeIndex]
        #     nextNode = room[nodeIndex + 1]

        #     if currentNode['x'] == nextNode['x']:
        #         #diff y
        #         for i in range(currentNode['y'], nextNode['y']):
        #             allNodes.append({'x': currentNode['x'], 'y': i})
        #     else:
        #         #diff x
        #         for i in range(currentNode['x'], nextNode['x']):
        #             allNodes.append({'x': i, 'y': currentNode['y']})

        # return allNodes

    def roadsToGridCoorinates(self):
        roads = []
        for newRoad in self.roadsArray:
            road = []
            for node in newRoad:
                x = round(node['x'] / self.pixelsPerGridSquare)
                y = round(node['y'] / self.pixelsPerGridSquare)
                road.append({'x': x, 'y': y})
            roads.append(road)
        return roads

    def structuresToGridCoordinatesAndReorder(self):
        structures = []
        for newStructure in self.newStructuresArray:
            minNode = {'x': sys.maxsize, 'y': sys.maxsize}
            structureNodes = []
            for node in newStructure['nodes']:
                x = round(node['x'] / self.pixelsPerGridSquare)
                y = round(node['y'] / self.pixelsPerGridSquare)
                structureNodes.append({'x': x, 'y': y})

                if x <= minNode['x'] and y <= minNode['y']:
                    minNode = {'x': x, 'y': y}

            reorderedStructure = {'nodes': structureNodes[structureNodes.index(
                minNode):len(structureNodes)], 'speciality': newStructure['speciality']}
            reorderedStructure['nodes'].extend(
                structureNodes[0:structureNodes.index(minNode) + 1])

            # Make the order anticlockwise if it isn't already
            if reorderedStructure['nodes'][0]['y'] == reorderedStructure['nodes'][1]['y']:
                reorderedStructure['nodes'].reverse()

            structures.append(reorderedStructure)
        return structures

    def determineRooms(self, version, structureNodes, newWallStart, newWallEnd, nodes):
        room1 = []
        room2 = []

        if version == 1:
            a = structureNodes.index(nodes[0])
            b = structureNodes.index(nodes[1])
            c = structureNodes.index(nodes[2])
            d = structureNodes.index(nodes[3])
        else:
            c = structureNodes.index(nodes[0])
            d = structureNodes.index(nodes[1])
            a = structureNodes.index(nodes[2])
            b = structureNodes.index(nodes[3])

        # Calc node 1
        if a < b:
            room1.extend(structureNodes[0:a + 1])
        else:
            room1.extend(structureNodes[0:b + 1])

        # whichever below is closest to node1
        if self.manhattenDistance(newWallStart, nodes[0]) < self.manhattenDistance(newWallEnd, nodes[0]):
            room1.append(newWallStart)
            room1.append(newWallEnd)
        else:
            room1.append(newWallEnd)
            room1.append(newWallStart)

        if c < d:
            room1.extend(structureNodes[c + 1:len(structureNodes)])
        else:
            room1.extend(structureNodes[d + 1:len(structureNodes)])

        # Calc Room 2
        room2.append(newWallStart)

        if a < b:
            if c < d:
                room2.extend(structureNodes[a + 1:c + 1])
            else:
                room2.extend(structureNodes[a + 1:d + 1])
        else:
            if c < d:
                room2.extend(structureNodes[b + 1:c + 1])
            else:
                room2.extend(structureNodes[b + 1:d + 1])

        room2.append(newWallEnd)

        return room1, room2

    def recursiveAreaDivision(self, structure, minArea):
        # randomly determine the current structure's internal wall assets.

        if structure['speciality'] == False:
            self.currentStructureAssets = {
                'wall':   self.genericStructureAssets['interiorWalls'][random.randint(0, len(self.genericStructureAssets['interiorWalls']) - 1)],
                'door':   self.genericStructureAssets['doors'][random.randint(0, len(self.genericStructureAssets['doors']) - 1)],
                'sill':   None,
                'window': None}
        else:
            self.currentStructureAssets = {
                'wall':   self.specialityStructureAssets['interiorWalls'][random.randint(0, len(self.specialityStructureAssets['interiorWalls']) - 1)],
                'door':   self.specialityStructureAssets['doors'][random.randint(0, len(self.specialityStructureAssets['doors']) - 1)],
                'sill':   None,
                'window': None}

        area = self.calcPolygonArea(structure['nodes'])
        if area > minArea:
            return self.recursiveDivision(structure['nodes'], minArea)
        else:
            self.vttStructures.append([])
            return []

        # area = self.calcPolygonArea(structure)
        # if area > minArea:
        #     self.recursiveDivision(structure, minArea)

    def recursiveDivision(self, structureNodes, minArea):
        nodes = [-1, -1, -1, -1]

        # + self.getAllNodes(interiorWalls)
        allNodes = self.getAllNodes(structureNodes)

        # for i in range(numberOfSplits):
        nodes[0], nodes[1] = self.nodePairOfLongestDistanceBetweenNodes(
            structureNodes)
        if nodes[0]['x'] == nodes[1]['x']:
            # vertical wall so new wall is horizontal
            # make interior wall half way down longest wall
            newWallStart = {'x': nodes[0]['x'], 'y':  int(
                abs(nodes[1]['y'] + nodes[0]['y']) / 2)}

            if nodes[0]['y'] < nodes[1]['y']:
                iterator = 1
                max = self.imageWidthSquares
            else:
                iterator = -1
                max = -1

            foundWall = False
            for j in range(newWallStart['x'] + iterator, max, iterator):
                newWallEnd = {'x': j, 'y': newWallStart['y']}
                if (newWallEnd in allNodes):
                    foundWall = True
                    break
            if not foundWall:
                raise Exception(
                    'Exception: wall not found in recursiveDivision')

            self.generateAssetsBetweenNodes(
                'horizontal', True, False, None, newWallStart, newWallEnd, iterator)
            self.vttStructure.insert(0, {'node': newWallStart, 'type': 'Wall'})
            # self.vttStructure.insert(0, {'node': {'x': -1, 'y': -1}, 'type': 'INTERIOR'})
            self.vttStructure.append(
                {'node': {'x': -1, 'y': -1}, 'type': 'EXTERIOR'})
            self.vttStructures.append(self.vttStructure)

            nodes[2], nodes[3] = self.findWallWhichContainsNode(
                structureNodes, newWallEnd)

            wall1Index = min(structureNodes.index(
                nodes[0]), structureNodes.index(nodes[1]))
            wall2Index = min(structureNodes.index(
                nodes[2]), structureNodes.index(nodes[3]))

            if wall1Index < wall2Index:
                room1, room2 = self.determineRooms(
                    1, structureNodes, newWallStart, newWallEnd, nodes)
            else:
                room1, room2 = self.determineRooms(
                    2, structureNodes, newWallStart, newWallEnd, nodes)

        else:
            # vertical wall so new wall is horizontal
            # make interior wall half way down longest wall
            newWallStart = {
                'x': int(abs(nodes[1]['x'] + nodes[0]['x']) / 2), 'y': nodes[0]['y']}

            if nodes[0]['x'] < nodes[1]['x']:
                iterator = -1
                max = -1
            else:
                iterator = 1
                max = self.imageHeightSquares

            foundWall = False
            newWallEnd = {}
            for j in range(newWallStart['y'] + iterator, max, iterator):
                newWallEnd = {'x': newWallStart['x'], 'y': j}
                if (newWallEnd in allNodes):
                    foundWall = True
                    break

            if not foundWall:
                raise Exception(
                    'Exception: wall not found in recursiveDivision')

            self.generateAssetsBetweenNodes(
                'vertical', True, False, None, newWallStart, newWallEnd, iterator)
            self.vttStructure.insert(0, {'node': newWallStart, 'type': 'Wall'})
            # self.vttStructure.insert(0, {'node': {'x': -1, 'y': -1}, 'type': 'INTERIOR'})
            self.vttStructure.append(
                {'node': {'x': -1, 'y': -1}, 'type': 'EXTERIOR'})
            self.vttStructures.append(self.vttStructure)

            nodes[2], nodes[3] = self.findWallWhichContainsNode(
                structureNodes, newWallEnd)

            a = structureNodes.index(nodes[0])
            b = structureNodes.index(nodes[1])
            c = structureNodes.index(nodes[2])
            d = structureNodes.index(nodes[3])

            wall1Index = min(a, b)
            wall2Index = min(c, d)

            if wall1Index < wall2Index:
                room1, room2 = self.determineRooms(
                    1, structureNodes, newWallStart, newWallEnd, nodes)
            else:
                room1, room2 = self.determineRooms(
                    2, structureNodes, newWallStart, newWallEnd, nodes)

        self.vttStructure = []

        # Do it again?
        # annoyingly calcPolygonArea is sometimes zero

        room1Area = self.calcPolygonArea(room1)
        room2Area = self.calcPolygonArea(room2)

        return [newWallStart, newWallEnd]

        # if room1Area > minArea and room2Area > minArea:
        #     self.recursiveDivision(room1, minArea)
        #     self.recursiveDivision(room2, minArea)

        #     return 0

    def generateExterior(self, structure, structureIndex, internalWallNodes):
        addDoor = False

        structureNodes = structure['nodes']
        # randomly determine the current structure's assets.

        if structure['speciality'] == False:
            self.currentStructureAssets = {
                'wall':   self.genericStructureAssets['exteriorWalls'][random.randint(0, len(self.genericStructureAssets['exteriorWalls']) - 1)],
                'door':   self.genericStructureAssets['doors'][random.randint(0, len(self.genericStructureAssets['doors']) - 1)],
                'sill':   self.genericStructureAssets['sills'][random.randint(0, len(self.genericStructureAssets['sills']) - 1)],
                'window': self.genericStructureAssets['windows'][random.randint(0, len(self.genericStructureAssets['windows']) - 1)]}
        else:
            self.currentStructureAssets = {
                'wall':   self.specialityStructureAssets['exteriorWalls'][random.randint(0, len(self.specialityStructureAssets['exteriorWalls']) - 1)],
                'door':   self.specialityStructureAssets['doors'][random.randint(0, len(self.specialityStructureAssets['doors']) - 1)],
                'sill':   self.specialityStructureAssets['sills'][random.randint(0, len(self.specialityStructureAssets['sills']) - 1)],
                'window': self.specialityStructureAssets['windows'][random.randint(0, len(self.specialityStructureAssets['windows']) - 1)]}

        # length = self.calculatePerimeterLength(structure)
        # spotsForADoor = length - len(structure)

        doorAbleWallNodes = []
        # Somehow determine which wall section should have the door
        for index in range(len(structureNodes) - 1):
            currentNode = structureNodes[index]
            nextNode = structureNodes[index + 1]

            xDifferent = abs(nextNode['x'] - currentNode['x'])
            yDifferent = abs(nextNode['y'] - currentNode['y'])

            if (xDifferent >= 3 or yDifferent >= 3):
                doorAbleWallNodes.append(currentNode)

        randomIndex = random.randint(0, len(doorAbleWallNodes) - 1)

        # append the first node
        self.vttStructure.append({'node': structureNodes[0], 'type': 'Wall'})

        for index in range(len(structureNodes) - 1):
            currentNode = structureNodes[index]
            nextNode = structureNodes[index + 1]

            xDifferent = nextNode['x'] - currentNode['x']
            yDifferent = nextNode['y'] - currentNode['y']

            if currentNode == doorAbleWallNodes[randomIndex]:
                addDoor = True
            else:
                addDoor = False

            # Currently not functioning as intended.
            if xDifferent != 0:
                orientation = 'horizontal'
                iterator = int(math.copysign(1, xDifferent))
            else:
                orientation = 'vertical'
                iterator = int(math.copysign(1, yDifferent))

            internalWallNodeIndex = None
            if len(internalWallNodes) > 0:
                nodes = self.nodesBetweenTwoNodes(
                    orientation, currentNode, nextNode, iterator)
                if internalWallNodes[0] in nodes:
                    internalWallNodeIndex = nodes.index(internalWallNodes[0])
                elif internalWallNodes[1] in nodes:
                    internalWallNodeIndex = nodes.index(internalWallNodes[1])

            if xDifferent != 0:
                #change in x
                iterator = int(math.copysign(1, xDifferent))
                self.generateAssetsBetweenNodes(
                    'horizontal', addDoor, True, internalWallNodeIndex, currentNode, nextNode, iterator)

            elif yDifferent != 0:
                #change in y
                iterator = int(math.copysign(1, yDifferent))
                self.generateAssetsBetweenNodes(
                    'vertical', addDoor, True, internalWallNodeIndex, currentNode, nextNode, iterator)

        self.vttStructures[structureIndex].extend(self.vttStructure)
        self.vttStructure = []

    def drawForDungeonified(self):
        Image.MAX_IMAGE_PIXELS = None
        self.assetSize = 200.0
        roads = []
        structures = []

        roads = self.roadsToGridCoorinates()
        structures = self.structuresToGridCoordinatesAndReorder()

        # Add first node to end so last wall is added.
        # for structure in structures:
        #     structure.append(structure[0])

        # calculate which assets to use
        self.imageWidthSquares = round(
            self.imageWidth / self.pixelsPerGridSquare)
        self.imageHeightSquares = round(
            self.imageHeight / self.pixelsPerGridSquare)
        assetSizeMultiplicator = self.assetSize / self.pixelsPerGridSquare

        self.pixelsPerGridSquare *= assetSizeMultiplicator
        pixelsPerGridSquareInt = int(self.pixelsPerGridSquare)
        halfPixelsPerGridSquareInt = int(pixelsPerGridSquareInt / 2)

        # https://stackoverflow.com/questions/14063070/overlay-a-smaller-image-on-a-larger-image-python-opencv

        # calculate what the average asset dimensions are... --> or just ask the user for dpi?
        # recaluclate everything's size for self.pixelsPerGridSquare to be asset sized.

        # setup image synthesis:
        base = Image.open('AnglesRule.png')

        # All references to 'speciality' below are for religious structures.
        exterior_floors = self.loadFloorAssets(r'assets\floor\exterior\*.jpg')
        interior_floors = self.loadFloorAssets(r'assets\floor\interior\*.jpg')
        speciality_floors = self.loadFloorAssets(r'assets\floor\special\*.jpg')

        pillars = self.loadWallAssets(r'assets\pillar\wood\*.png')
        speciality_pillars = self.loadWallAssets(
            r'assets\pillar\special\*.png')

        exterior_walls = self.loadWallAssets(r'assets\wall\exterior\*.png')
        interior_walls = self.loadWallAssets(r'assets\wall\interior\*.png')
        doors = self.loadWallAssets(r'assets\door\single\*.png')
        windows = self.loadWallAssets(r'assets\window\*.png')
        sills = self.loadWallAssets(r'assets\sill\*.png')

        specialityWalls = self.loadWallAssets(r'assets\wall\special\*.png')
        specialityDoors = self.loadWallAssets(
            r'assets\door\single\special\*.png')
        specialitySills = self.loadWallAssets(r'assets\sill\special\*.png')
        specialityWindows = self.loadWallAssets(r'assets\window\special\*.png')

        # Generate Floor:
        compositeFloor = exterior_floors[random.randint(
            0, len(exterior_floors) - 1)]
        for structure in self.newStructuresArray:
            polygonStructures = []
            for node in structure['nodes']:
                polygonStructures.append((int(node['x'] * assetSizeMultiplicator + pixelsPerGridSquareInt), int(
                    node['y'] * assetSizeMultiplicator + pixelsPerGridSquareInt)))

            if structure['speciality'] == False:
                interiorFloor = interior_floors[random.randint(
                    0, len(interior_floors) - 1)]
            else:
                interiorFloor = speciality_floors[random.randint(
                    0, len(speciality_floors) - 1)]
            mask = Image.new("L", interiorFloor.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.polygon(polygonStructures, outline=255, fill=255)
            compositeFloor = Image.composite(
                interiorFloor, compositeFloor, mask)

        self.new_image = Image.new('RGB', (int(self.imageWidthSquares * pixelsPerGridSquareInt), int(
            self.imageHeightSquares * pixelsPerGridSquareInt)), (255, 255, 255))
        self.new_image.paste(compositeFloor, (0, 0))

        # Structures
        self.vttStructures = []
        self.vttStructure = []

        self.genericStructureAssets = {'exteriorWalls': exterior_walls,
                                       'interiorWalls': interior_walls, 'doors': doors, 'sills': sills, 'windows': windows}
        self.currentStructureAssets = {}

        self.specialityStructureAssets = {'exteriorWalls': specialityWalls, 'interiorWalls': specialityWalls,
                                          'doors': specialityDoors, 'sills': specialitySills, 'windows': specialityWindows}
        self.specialityStructure = {}

        # Generate Walls:

        minArea = 50
        internalWallNodes = []
        for structureIndex in range(len(structures)):
            # internal walls
            internalWallNodes = self.recursiveAreaDivision(
                structures[structureIndex], minArea)

            # external Walls
            structure = structures[structureIndex]
            self.generateExterior(structure, structureIndex, internalWallNodes)

        # for :

        # Generate Pillars:
        for newStructure in structures:
            if newStructure['speciality'] == False:
                pillar = pillars[random.randint(0, len(pillars) - 1)]
            else:
                pillar = speciality_pillars[random.randint(
                    0, len(speciality_pillars) - 1)]

            structure = []
            for node in newStructure['nodes'][:-1]:
                x = (node['x'] * pixelsPerGridSquareInt) + \
                    halfPixelsPerGridSquareInt
                y = (node['y'] * pixelsPerGridSquareInt) + \
                    halfPixelsPerGridSquareInt
                self.new_image.paste(pillar, (x, y), mask=pillar)

        self.new_image.save("testDungeonify.png", "PNG")
        self.structures = structures

    def manhattenDistance(self, fromNode, toNode):
        xDifference = abs(toNode['x'] - fromNode['x'])
        yDifference = abs(toNode['y'] - fromNode['y'])

        return xDifference + yDifference

    def angleOfLongestDistanceBetweenNodes(self, structureNodes):
        node1, node2 = self.nodePairOfLongestDistanceBetweenNodes(
            structureNodes)
        return self.angleForTwoNodes(node1, node2)

    def nodePairOfLongestDistanceBetweenNodes(self, structureNodes):
        inchesBetweenNodes = -1
        longestNodePair = []
        # for structure in self.structuresArray:

        for index in range(len(structureNodes) - 1):
            nextNode = structureNodes[index + 1]
            currentNode = structureNodes[index]

            currentDistance = self.distanceBetweenNodes_xy(
                currentNode, nextNode)
            if currentDistance[0] > inchesBetweenNodes:
                # save the details of this pair
                inchesBetweenNodes = currentDistance[0]
                longestNodePair = [currentNode, nextNode]

        return longestNodePair

        # if longestNodePair[0]['x'] > longestNodePair[1]['x'] and longestNodePair[0]['y'] > longestNodePair[1]['y']:
        #     return longestNodePair[0], longestNodePair[1]
        # else:
        #     return longestNodePair[1], longestNodePair[0]

    def angleForThreeNodes(self, prevNode, currentNode, nextNode):
        vector1 = [currentNode['x'] - prevNode['x'],
                   currentNode['y'] - prevNode['y']]
        vector2 = [currentNode['x'] - nextNode['x'],
                   currentNode['y'] - nextNode['y']]
        # vector2 = [nextNode['x'] - currentNode['x'], nextNode['y'] - currentNode['y']]
        # vector1 = [prevNode['x'] - currentNode['x'], prevNode['y'] - currentNode['y']]
        # vector2 = [nextNode['x'] - currentNode['x'], nextNode['y'] - currentNode['y']]

        return self.calculateAngle(vector1, vector2)

    def angleForTwoNodes2(self, currentNode, nextNode, nextNextNode):
        vector_1 = [nextNode['x'] - currentNode['x'],
                    nextNode['y'] - currentNode['y']]
        vector_2 = [nextNextNode['x'] - nextNode['x'],
                    nextNextNode['y'] - nextNode['y']]

        unit_vector_1 = vector_1 / np.linalg.norm(vector_1)
        unit_vector_2 = vector_2 / np.linalg.norm(vector_2)

        dot_product = np.dot(unit_vector_1, unit_vector_2)
        angle = np.arccos(dot_product)

        return angle

    def angleForTwoNodes3(self, currentNode, nextNode):
        angle = math.atan2(
            currentNode['y'] - nextNode['y'], currentNode['x'] - nextNode['x'])
        angle = math.radians(angle)

        return angle

    def angleForTwoNodes(self, currentNode, prevNode):
        vector1 = [currentNode['x'] - prevNode['x'],
                   currentNode['y'] - prevNode['y']]

        # Find the largest side, horizontal or vertical.
        vector2 = [0, 0]
        if abs(vector1[0]) > abs(vector1[1]):
            vector2 = [currentNode['x'] - prevNode['x'],
                       currentNode['y'] - currentNode['y']]
        else:
            vector2 = [currentNode['x'] - currentNode['x'],
                       currentNode['y'] - prevNode['y']]

        return self.calculateAngle(vector1, vector2)

    def calculateAngle(self, vector1, vector2):
        # same y, ie relative to the horizontal.
        unit_vector_1 = vector1 / np.linalg.norm(vector1)
        unit_vector_2 = vector2 / np.linalg.norm(vector2)

    #    # using cross-product formula
    #    return -math.degrees(math.asin((self.a * other.b - self.b * other.a)/(self.length()*other.length())))
    #    # the dot-product formula, left here just for comparison (does not return angles in the desired range)
    #    # return math.degrees(math.acos((self.a * other.a + self.b * other.b)/(self.length()*other.length())))

        # unsigned angle
        # dot_product = np.dot(unit_vector_1, unit_vector_2)
        # angle = np.arccos(dot_product)

        angle = np.arctan2(np.cross(unit_vector_1, unit_vector_2),
                           np.dot(unit_vector_1, unit_vector_2))

        return math.degrees(angle)

        # unit_vector_1 = vector1 / np.linalg.norm(vector1)
        # unit_vector_2 = vector2 / np.linalg.norm(vector2)
        # dot_product = np.dot(unit_vector_1, unit_vector_2)
        # angle = np.arccos(dot_product)
        # return angle

    def rotateNode(self, origin, point, angle):
        angleRadians = math.radians(angle)
        # Rotate a point counterclockwise by a given angle around a given origin.
        # The angleRadians should be given in radians.
        ox, oy = origin['x'], origin['y']
        px, py = point['x'], point['y']

        qx = ox + math.cos(angleRadians) * (px - ox) - \
            math.sin(angleRadians) * (py - oy)
        qy = oy + math.sin(angleRadians) * (px - ox) + \
            math.cos(angleRadians) * (py - oy)
        return {'x': qx, 'y': qy}

    def distanceBetweenNodes_xy(self, previousNode, currentNode):
        xDifference = currentNode['x'] - previousNode['x']
        yDifference = currentNode['y'] - previousNode['y']

        # Real world inches = / 30
        horizontalInches = xDifference * self.inchesPerPixel['horizontal']
        verticalInches = yDifference * self.inchesPerPixel['vertical']

        PythagoreanTheoremInches = math.sqrt(
            horizontalInches * horizontalInches + verticalInches * verticalInches)

        return PythagoreanTheoremInches, horizontalInches, verticalInches

    # Unused
    def calculateDistancesBetweenNodes(self):
        # Calculate distances for nodes
        print(f"--- Distances ---")
        print(f"N.B. ('-x' --> left), ('-y' --> up)")
        for structure in self.structuresArray:
            prevNode = None
            print(f"-Next Structure: ")
            for currentNode in structure:
                # avoid the first node, so this is not rotated.
                # Instead use this as the rotation about point for all other nodes.
                if prevNode:
                    # Positive inchesBetweenNodes_Horizontal means 'right'
                    # Positive inchesBetweenNodes_Vertical means 'down'
                    inchesBetweenNodes, inchesBetweenNodes_Horizontal, inchesBetweenNodes_Vertical = self.distanceBetweenNodes_xy(
                        prevNode, currentNode)
                    print(f"({prevNode['x']:.0f}, {prevNode['y']:.0f}) --> ({currentNode['x']:.0f},{currentNode['y']:.0f}) = {inchesBetweenNodes:.3f} (H: {inchesBetweenNodes_Horizontal:.3f}, V: {inchesBetweenNodes_Vertical:.3f} )")

                prevNode = currentNode
        print(f"--- END ---")

    def roundToNearestInch(self, x):
        return self.roundNearest(x, self.pixelsPerGridSquare)

    def roundNearest(self, number: float, roundedTo: float) -> float:
        number, roundedTo = Decimal(str(number)), Decimal(str(roundedTo))
        return float(round(number / roundedTo) * roundedTo)

    def roundDown(self, number: float, roundedTo: float) -> float:
        number, roundedTo = Decimal(str(number)), Decimal(str(roundedTo))
        return float(math.floor(number / roundedTo) * roundedTo)

    def roundUp(self, number: float, roundedTo: float) -> float:
        number, roundedTo = Decimal(str(number)), Decimal(str(roundedTo))
        return float(math.ceil(number / roundedTo) * roundedTo)

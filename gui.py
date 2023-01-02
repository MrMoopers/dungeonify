import unittest
import os
import sys
import time
import tracemalloc
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *

from dungeonify import Dungeonify
from DungeonifyGenerators import GeneratorTypes

# File    : gui.py
# Classes : QDungeonifyViewer
# Author  : Adam Biggs (100197567)
# Date    : 18/05/2022
# Notes   : This PyQt5 class is the main User Interface generated for the user. Within it, it contains
#               an image viewer and several basic image manipulation tools contained in the main task
#               bar. In addition, this file contains a main which is used to start the application.

# Global Constants used to control the QDungeonifyViewer window's size.
SCREEN_WIDTH = -1
SCREEN_HEIGHT = -1

# A useful global Constant used for debugging.
DEBUGGING = False

# Five global Constants used for testing and evaluation of the results.
DISABLE_SHOWN_PIPELINE_STEPS = False
EVALUATE_AREA = False
EVALUATE_TIME = False
EVALUATE_METHOD_TIMES = False
EVALUATE_MEMORY = False
EVALUATE_DISCOVERY_METRIC = False

RUN_UNIT_TESTS = False

# The main UI class.


class QDungeonifyViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dungeonify OSM Converter")

        self.printer = QPrinter()
        self.scaleFactor = 0.0

        self.imageLabel = QLabel()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setVisible(False)

        self.setCentralWidget(self.scrollArea)
        self.createActions()
        self.createMenus()

        # Resize the window to be a third the width and height of the screen.
        self.resize(int(SCREEN_WIDTH * 0.666), int(SCREEN_HEIGHT * 0.666))

        # When debugging use a specific url instead of requiring it off of the user.
        if not DEBUGGING:
            self.urlInput = self.getNewOSMUrl()
        else:
            # Generic Location.
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/52.62640/1.34812'

            # Location with a Religious Structure.
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/51.87076/0.15715'  # location 1

            # The URLs used for the results evaluation.
            self.urlInput = 'https://www.openstreetmap.org/#map=19/51.87166/0.15663'  # location 2
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/52.62956/1.26577'  # location 3
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/51.48076/-2.63602'  # location 4
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/47.91488/1.93173'  # location 5
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/35.68263/139.72467'  # location 6

            # rotation tests - curved structures
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/50.81705/4.39651' # location 7
            # self.urlInput = 'https://www.openstreetmap.org/#map=19/50.81802/4.39547' # location 8

        # Lists used to store the structures collected from the OSM API.
        self.structures = []
        self.structuresFromOSM = []

        self.inchesPerPixel = {}
        self.isGridVisible = False

        # Stores the dungeonify object used to generate each battlemap image.
        self.dungeonify = None

        # Store the results of the evaluation in these variables.
        self.areasResults = {'before': [], 'after': [],
                             'Difference': [], 'Mean Difference': 0}
        self.timingResults = {'start': -1, 'end': -1, 'total': -1}

        self.timingProcessesResults = {
            'osm': -1,
            'Selected Structures': -1,
            'Rotated Structures': -1,
            'Rotated & Resized Structures': -1,
            'Dungeonified Structures': -1,
            'VTT File': -1}

        self.memoryResults = {'peak': -1}
        self.similarityCoefficentResults = {
            'before': [], 'after': [], 'Difference': []}
        self.newStructureAreas = []
        self.structureTime = []
        self.battlemapTime = -1

        # Used to Convert the imported OSM API node data into a qImage which can be displayed in the window.
        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['osm'] = time.time()

        self.displayOSM()

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['osm'] = time.time(
            ) - self.timingProcessesResults['osm']
        self.enableScreenClicks = True

    # Display a new OSM URL input box.
    def getNewOSMUrl(self):
        text, ok = QInputDialog().getText(self, "URL Input Dialog",
                                          "Open Street Map URL:", QLineEdit.Normal)
        if ok and text:
            return text
        else:
            raise Exception('Exception: wall not found in getNewOSMUrl')

    # Used to make generate a new OSM location and import the data from that new location.
    def newOSMUrl(self):
        self.urlInput = self.getNewOSMUrl()

        # Lists used to store the structures collected from the OSM API.
        self.structures = []
        self.structuresFromOSM = []
        self.inchesPerPixel = {}

        self.isGridVisible = False

        # Used to Convert the imported OSM API node data into a qImage which can be displayed in the window.
        self.displayOSM()
        self.enableScreenClicks = True

    # The first stage in the dungeonify pipeline. It simply generates the structures which have been selected in the
    # window. In addition it starts any evaluation steps.
    def drawSelected(self):
        if EVALUATE_TIME:
            # Record the start time.
            self.timingResults['start'] = time.time()
        elif EVALUATE_MEMORY:
            # Record the starting memory usage.
            tracemalloc.start()

        # Create a new Dungeonify object using the structures, roads and inches per pixel information.
        # EVALUATE_AREA must be calculated within this object's processing, so must be an argument as well.
        self.dungeonify = Dungeonify(
            self.structures, self.roads, self.inchesPerPixel, EVALUATE_AREA)

        if EVALUATE_AREA:
            # Record the initial area information.
            self.areasResults['before'] = self.dungeonify.calculateStructureAreasBefore(
            )
        # elif EVALUATE_DISCOVERY_METRIC:
        #     # Record the starting similarity coefficent information.
        #     self.similarityCoefficentResults['before'] = self.dungeonify.calculateDistanceCoefficentBefore(
        #     )

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Selected Structures'] = time.time()

        # The generate method uses an enumerated type to switch on. This here generates the selected buildings only,
        # without any rotation.
        self.dungeonify.generate(GeneratorTypes.selectedBuildings, 3.0)

        # Generate the gridded image.
        self.dungeonify.generate_grid()

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Selected Structures'] = time.time(
            ) - self.timingProcessesResults['Selected Structures']

        # Enable and disable buttons in the menu structure.
        self.toggleGridAct.setEnabled(True)
        self.isGridVisible = True

        # Detail which image is the current one, such that it can be loaded.
        self.currentImage = "basic.png"
        self.load_image()

        self.enableScreenClicks = False
        self.drawSelectedAct.setEnabled(False)
        self.drawRotatedAct.setEnabled(True)

        if EVALUATE_TIME or EVALUATE_MEMORY or DISABLE_SHOWN_PIPELINE_STEPS:
            # For any of the above evaluation methods, or the DISABLE_SHOWN_PIPELINE_STEPS immediately run
            # the next pipeline stage. This maintains fairness as the user control will require time and resources
            # dependant on external factors.
            self.drawRotated()

    # The second stage in the dungeonify pipeline. It rotates each structure such that it's longest wall section
    #  becomes horizontal or vertical - whichever it is closest to being.
    def drawRotated(self):
        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Rotated Structures'] = time.time()

        # Generate for the enum rotatedBuildings at a set scale of 3.
        self.dungeonify.generate(GeneratorTypes.rotatedBuildings, 3.0)

        # Generate the gridded image.
        self.dungeonify.generate_grid()

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Rotated Structures'] = time.time(
            ) - self.timingProcessesResults['Rotated Structures']

        # Update the current image and load it.
        self.currentImage = "rotated.png"
        self.load_image()

        # Enable and disable buttons in the menu structure.
        self.drawRotatedAct.setEnabled(False)
        self.drawResizedAndRotatedAct.setEnabled(True)

        if EVALUATE_TIME or EVALUATE_MEMORY or DISABLE_SHOWN_PIPELINE_STEPS:
            # For any of the above evaluation methods, or the DISABLE_SHOWN_PIPELINE_STEPS immediately run
            # the next pipeline stage. This maintains fairness as the user control will require time and resources
            # dependant on external factors.
            self.drawResizedAndRotated()

    # The third stage in the dungeonify pipeline. It rotates each structure's wall section node pairs such that
    #  the pair becomes horizontal or vertical - whichever is closer.
    def drawResizedAndRotated(self):
        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Rotated & Resized Structures'] = time.time(
            )

        # Generate for the enum repositionedBuildings at a set scale of 3.
        self.dungeonify.generate(GeneratorTypes.repositionedBuildings, 3.0)
        # Generate the gridded image.
        self.dungeonify.generate_grid()

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Rotated & Resized Structures'] = time.time(
            ) - self.timingProcessesResults['Rotated & Resized Structures']

        if EVALUATE_AREA:
            # To evaluate the area, it records the area after all the rotation steps have been completed.
            # It then calculates the difference between the two for each structure and exits.
            self.areasResults['after'] = self.dungeonify.calculateStructureAreasAfter(
            )

            self.areasResults['Difference'] = []
            differenceList = []
            differenceTotal = 0
            for i in range(len(self.areasResults['before'])):
                difference = abs(
                    self.areasResults['after'][i] - self.areasResults['before'][i])
                differenceList.append(difference)
                differenceTotal += difference

            self.areasResults['Difference'] = differenceList
            self.areasResults['Mean Difference'] = differenceTotal / \
                len(self.areasResults['before'])
            print(f'Area Results: \n  {self.areasResults}')

            sys.exit()
        # elif EVALUATE_DISCOVERY_METRIC:
        #     # The Similarity Coefficent is recorded for after the rotation steps have been completed.
        #     self.similarityCoefficentResults['after'] = self.dungeonify.calculateDistanceCoefficentAfter(
        #     )
        #     print(
        #         f'Similarity Coefficient Results: \n  {self.similarityCoefficentResults}')
        #     sys.exit()

        # The current image text is updated, and loaded.

        # At this stage the grid is no longer useful, so it can be disabled.
        self.isGridVisible = False
        self.toggleGridAct.setText("Show &Grid")
        self.toggleGridAct.setEnabled(False)

        self.currentImage = "AnglesRule.png"
        self.load_image()

        # Enable and disable buttons in the menu structure.
        self.drawResizedAndRotatedAct.setEnabled(False)
        self.dungeonifyAct.setEnabled(True)

        if EVALUATE_TIME or EVALUATE_MEMORY or DISABLE_SHOWN_PIPELINE_STEPS:
            # For any of the above evaluation methods, or the DISABLE_SHOWN_PIPELINE_STEPS immediately run
            # the next pipeline stage. This maintains fairness as the user control will require time and resources
            # dependant on external factors.
            self.drawDungeonify()
        if RUN_UNIT_TESTS:
            return self.dungeonify.structuresArray

    # The fourth and final stage in the dungeonify pipeline. It generates the battlemap texture image using
    #  the configured structure node infomation. After this, it generates the FVTT compatible file.

    def drawDungeonify(self):
        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Dungeonified Structures'] = time.time(
            )

        # Generate the dungeonified structures at zoom scale 3.
        self.dungeonify.generate(GeneratorTypes.dungeonifiedBuildings, 3.0)

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['Dungeonified Structures'] = time.time(
            ) - self.timingProcessesResults['Dungeonified Structures']

        # Update the current image text.
        self.currentImage = "testDungeonify.png"

        # Load the image.
        self.load_image()

        # Enable and disable buttons in the menu structure.
        self.dungeonifyAct.setEnabled(False)

        #  --- FVTT File Generation Notes ---
        # Owing to the nature of how core battlemap images for scenes are stored in FoundryVTT it was decised
        # that loading battlemaps via a battlemap importing module would be more functional.
        # From staff working at FoundryVTT: 'if it did work you certainly wouldn't want to run with that
        # for performance reasons' — 08/03/2022.

        # How the files are generated can be seen my viewing the Generic_Battlemap.dd2vtt file. Within it
        # clearly shows how the data will be combined to form the FVTT file.

        # Testing
        # self.dungeonify.newStructuresArray
        # self.dungeonify.structuresArray
        # self.dungeonify.structures
        # self.dungeonify.vttStructures
        # self.dungeonify.border
        # self.dungeonify.borderPixels
        # in dungeonify add to it the pos of the doors and windows

        # self.dungeonify.vttStructures = [[{'node': {'x': 0, 'y': 6}, 'type': 'Wall'}, {'node': {'x': 5, 'y': 6}, 'type': 'Door'}, {'node': {'x': 7, 'y': 6}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 6}, 'type': 'Wall'}, {'node': {'x': -1, 'y': -1}, 'type': 'EXTERIOR'}, {'node': {'x': 0, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 0, 'y': 3}, 'type': 'Window'}, {'node': {'x': 0, 'y': 4}, 'type': 'Wall'}, {'node': {'x': 0, 'y': 6}, 'type': 'Window'}, {'node': {'x': 0, 'y': 7}, 'type': 'Wall'}, {'node': {'x': 0, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 2, 'y': 12}, 'type': 'Window'}, {'node': {'x': 3, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 5, 'y': 12}, 'type': 'Window'}, {'node': {'x': 7, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 11}, 'type': 'Window'}, {'node': {'x': 7, 'y': 10}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 8}, 'type': 'Window'}, {'node': {'x': 7, 'y': 7}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 6}, 'type': 'Window'}, {'node': {'x': 7, 'y': 5}, 'type': 'Wall'}, {'node': {'x': 7, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 5, 'y': 0}, 'type': 'Window'}, {'node': {'x': 3, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 0, 'y': 0}, 'type': 'Wall'}], [{'node': {'x': 8, 'y': 6}, 'type': 'Wall'}, {'node': {'x': 11, 'y': 6}, 'type': 'Door'}, {'node': {'x': 12, 'y': 6}, 'type': 'Wall'}, {'node': {'x': 15, 'y': 6}, 'type': 'Wall'}, {'node': {'x': -1, 'y': -1}, 'type': 'EXTERIOR'}, {'node': {'x': 8, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 8, 'y': 1}, 'type': 'Window'}, {'node': {'x': 8, 'y': 2}, 'type': 'Wall'}, {'node': {'x': 8, 'y': 8}, 'type': 'Window'}, {'node': {'x': 8, 'y': 9}, 'type': 'Wall'}, {'node': {'x': 8, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 12, 'y': 12}, 'type': 'Window'}, {'node': {'x': 13, 'y': 12}, 'type': 'Door'}, {'node': {'x': 15, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 15, 'y': 12}, 'type': 'Wall'}, {'node': {'x': 15, 'y': 10}, 'type': 'Window'}, {'node': {'x': 15, 'y': 8}, 'type': 'Wall'}, {'node': {'x': 15, 'y': 5}, 'type': 'Window'}, {'node': {'x': 15, 'y': 4}, 'type': 'Wall'}, {'node': {'x': 15, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 12, 'y': 0}, 'type': 'Window'}, {'node': {'x': 11, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 10, 'y': 0}, 'type': 'Window'}, {'node': {'x': 9, 'y': 0}, 'type': 'Wall'}, {'node': {'x': 8, 'y': 0}, 'type': 'Wall'}]]

        #   [Format] : decimal. This is essentially a version number

        if (EVALUATE_METHOD_TIMES):
            self.timingProcessesResults['VTT File'] = time.time()

        # For EVALUATE_DISCOVERY_METRIC
        discoveryMetrics = []
        wallCount = 0
        windowCount = 0
        doorCount = 0

        border = int(self.dungeonify.border / 2)
        vttWalls = ''
        vttPortals = ''
        for vttStructure in self.dungeonify.vttStructures:
            for vttNodeIndex in range(len(vttStructure) - 1):
                currentVttType = vttStructure[vttNodeIndex]['type']
                nextVttType = vttStructure[vttNodeIndex + 1]['type']

                if currentVttType == 'EXTERIOR' or nextVttType == 'EXTERIOR':
                    continue

                currentVttNode = vttStructure[vttNodeIndex]['node']
                nextVttNode = vttStructure[vttNodeIndex + 1]['node']

                if currentVttNode != nextVttNode:

                    if currentVttType == 'Wall':
                        wallCount += 1
                        vttWall = f"""[
                {{
                    "x": {currentVttNode['x'] + border},
                    "y": {currentVttNode['y'] + border}
                }},
                {{
                    "x": {nextVttNode['x'] + border},
                    "y": {nextVttNode['y'] + border}
                }}
            ],
            """

                        vttWalls += vttWall
                    else:
                        # portals:
                        # "closed": false, <-- windows
                        # "closed": true, <-- door
                        closed = ''
                        if currentVttType == 'Window':
                            windowCount += 1
                            closed = 'false'

                            # portals are only ever a startnode and an end node
                        elif currentVttType == 'Door':
                            doorCount += 1
                            closed = 'true'

                            # rotation:
                            # "rotation": 1.570796, <-- pi/2
                            # "rotation": 3.141593, <-- pi
                        vttPortal = f"""{{
                "position": {{
                    "x": {currentVttNode['x']+ border},
                    "y": {currentVttNode['y']+ border}
                }},
                "bounds": [
                    {{
                        "x": {currentVttNode['x']+ border},
                        "y": {currentVttNode['y']+ border}
                    }},
                    {{
                        "x": {nextVttNode['x']+ border},
                        "y": {nextVttNode['y']+ border}
                    }}
                ],
                "rotation": -1.570796,
                "closed": {closed},
                "freestanding": false
            }},
            """

                        vttPortals += vttPortal

            if EVALUATE_DISCOVERY_METRIC:
                # Calculate for each structure.
                discoveryMetric = (
                    (windowCount * doorCount) + len(vttStructure)) / (wallCount + windowCount + doorCount)

                discoveryMetrics.append(discoveryMetric)
        vttLights = ''
        # vttLight = f"""{{
        # 	"position": {{
        # 		"x": 5.02671,
        # 		"y": 10.487534
        # 	}},
        # 	"range": 5,
        # 	"intensity": 1,
        # 	"color": "ffeccd8b",
        # 	"shadows": true
        # }},"""

        vttWalls = vttWalls[:len(vttWalls) - 14]
        vttPortals = vttPortals[:len(vttPortals) - 14]

        import base64

        with open('testDungeonify.png', mode='rb') as file:
            img = file.read()
        imageData = base64.encodebytes(img).decode('utf-8')
        imageData = imageData.replace('\n', '')

        # print(json.dumps(data))

        vttFile = f"""{{
    "format": 0.3,
    "resolution": {{
        "map_origin": {{
            "x": 0,
            "y": 0
        }},
        "map_size": {{
            "x": {int(self.dungeonify.totalInchesWidth / 3)},
            "y": {int(self.dungeonify.totalInchesHeight / 3)}
        }},
        "pixels_per_grid": {int(self.dungeonify.assetSize)}
    }},
    "line_of_sight": [
        {vttWalls}
    ],
    "portals": [
        {vttPortals}
    ],
    "environment": {{
        "baked_lighting": true,
        "ambient_light": "ffffffff"
    }},
    "lights": [
        {vttLights}
    ],
    "image": "{imageData}"
}}"""
        # all needs to be on the same line.

        if os.path.exists("Battlemap.dd2vtt"):
            os.remove("Battlemap.dd2vtt")
        f = open("Battlemap.dd2vtt", "a")
        f.write(vttFile)
        f.close()

        if EVALUATE_METHOD_TIMES:
            self.timingProcessesResults['VTT File'] = time.time(
            ) - self.timingProcessesResults['VTT File']

            print(
                f'Core Processes\' Timing Results: \n  {self.timingProcessesResults}')

            with open("Core Processes Timing Results.txt", "a") as file_object:
                # Append 'hello' at the end of file
                file_object.write(
                    f"{self.timingProcessesResults} - {self.urlInput} - nodes:{len(self.structures[0]['nodes'])} - structures: {len(self.structures)} mapSize:{self.dungeonify.imageWidthSquares}X{self.dungeonify.imageHeightSquares}\n")

            sys.exit()
        if EVALUATE_TIME:
            self.timingResults['end'] = time.time()
            self.timingResults['total'] = self.timingResults['end'] - \
                self.timingResults['start']
            print(f'Timing Results: \n  {self.timingResults}')

            # Open a file with access mode 'a'
            with open("Timing Results.txt", "a") as file_object:
                # Append 'hello' at the end of file
                file_object.write(
                    f"{self.timingResults} - {self.urlInput} - nodes:{len(self.structures[0]['nodes'])} - structures: {len(self.structures)} mapSize:{self.dungeonify.imageWidthSquares}X{self.dungeonify.imageHeightSquares}\n")

            sys.exit()
        elif EVALUATE_MEMORY:
            size, self.memoryResults['peak'] = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f'Memory Results: \n  {self.memoryResults}')
            sys.exit()

        if EVALUATE_DISCOVERY_METRIC:
            totalInternalArea = sum(
                self.dungeonify.calculateStructureAreasAfter())
            totalExternalArea = (self.dungeonify.imageWidth *
                                 self.dungeonify.imageHeight) - totalInternalArea

            discoveryMetric_base = totalInternalArea / totalExternalArea

            for discoveryMetricIndex in range(len(discoveryMetrics) - 1):
                discoveryMetrics[discoveryMetricIndex] = discoveryMetrics[discoveryMetricIndex] * \
                    discoveryMetric_base

            print(f"Individual Discovery Metrics: {discoveryMetrics}")
            if len(discoveryMetrics) > 1:
                mean = sum(discoveryMetrics) / len(discoveryMetrics)
                print(f"Mean Average Discovery Metric: {mean}")

            sys.exit()

    def displayOSM(self):
        from osm_factory import GenerateOSM
        # convert the image to a dungeon map.
        print(f"{self.urlInput}")

        text = self.urlInput.split('/')
        # scrX': 805, 'scrY': 742

        longitudeInput = text[-1].split('&')[0]
        latitudeInput = text[-2]

        # https://www.openstreetmap.org/#map=19/52.62640/1.34811
        generateOSM = GenerateOSM()
        self.structuresFromOSM, self.roads, self.inchesPerPixel = generateOSM.generate(
            longitudeInput, latitudeInput, SCREEN_WIDTH, SCREEN_HEIGHT)

        self.currentImage = "example.png"
        self.load_image()

    def loadGrid(self, newImageName):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        # alternative for working with V.large images:
        # https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_setup/py_intro/py_intro.html#intro

        back = Image.open(self.currentImage)
        front = Image.open("grid.png")

        # Convert image to RGBA
        frontImage = front.convert("RGBA")
        background = back.convert("RGBA")

        # Calculate width to be at the center
        width = (background.width - frontImage.width) // 2
        height = (background.height - frontImage.height) // 2

        # Paste the frontImage at (width, height)
        background.paste(frontImage, (width, height), frontImage)

        # "combined.png"
        self.currentImage = newImageName
        # Save this image
        background.save(self.currentImage, format="png")
        # add grid.png and load that

    def toggleGrid(self):
        # if grid toggling is enabled
        self.isGridVisible = not self.isGridVisible

        if self.isGridVisible:
            self.toggleGridAct.setText("Hide &Grid")
        else:
            self.toggleGridAct.setText("Show &Grid")

        self.load_image()

    def load_image(self):
        if self.isGridVisible:
            # show with a grid
            # create gd and add grid.png and load that
            newImageName = self.currentImage[:len(
                self.currentImage) - 4] + 'Grid.png'
            self.loadGrid(newImageName)
        else:
            # show without a grid
            if 'Grid.png' in self.currentImage:
                self.currentImage = self.currentImage[:len(
                    self.currentImage) - 8] + '.png'
                # remove grid.png and load that

        # on the next pass it is 'combined.png'
        image = QImage(self.currentImage)

        if image.isNull():
            QMessageBox.information(self, "Image Viewer", "Cannot load image")

        self.imageLabel.setPixmap(QPixmap.fromImage(image))
        self.scaleFactor = 1.0

        self.scrollArea.setVisible(True)
        self.printAct.setEnabled(True)
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()

        if not self.fitToWindowAct.isChecked():
            self.imageLabel.adjustSize()

        self.fitToWindow()

    def point_in_polygon(self, polygon, point):
        # https://www.algorithms-and-technologies.com/point_in_polygon/python
        # A point is in a polygon if a line from the point to infinity crosses the polygon an odd number of times
        odd = False
        # For each edge (In this case for each point of the polygon and the previous one)
        i = 0
        j = len(polygon) - 1
        while i < len(polygon) - 1:
            i = i + 1
            # If a line from the point into infinity crosses this edge
            # One point needs to be above, one below our y coordinate
            # ...and the edge doesn't cross our Y corrdinate before our x coordinate (but between our x coordinate and infinity)

            if (((polygon[i]['y'] > point['y']) != (polygon[j]['y'] > point['y'])) and (point['x'] < (
                    (polygon[j]['x'] - polygon[i]['x']) * (point['y'] - polygon[i]['y']) / (polygon[j]['y'] - polygon[i]['y'])) +
                    polygon[i]['x'])):
                # Invert odd
                odd = not odd
            j = i
        # If the number of crossings was odd, the point is in the polygon
        return odd

    # Core
    def mousePressEvent(self, event):
        # Once started generating, stop allowing user to click buildings
        if self.enableScreenClicks:
            if event.button() == Qt.LeftButton:
                # print(f"x: {event.pos().x()}, y: {event.pos().y()}")
                if self.structuresFromOSM != []:
                    mousePosition = {
                        'x': event.pos().x(), 'y': event.pos().y()}
                    # TODO: Figure out this stuff for main menu
                    # the hright of that menu bar is 21 pixels, despite that it thinks it is 30
                    mousePosition['y'] -= self.menuHeight
                    structure = self.clickedAStructure(mousePosition)
                    if structure != None:
                        # print("You clicked a building! Woo!")
                        if structure not in self.structures:
                            self.structures.append(structure)
                        else:
                            self.structures.remove(structure)

                        if len(self.structures) > 0:
                            self.drawSelectedAct.setEnabled(True)
                        else:
                            self.drawSelectedAct.setEnabled(False)

                        self.structuresClickedLabel.setText(
                            f"Structures Clicked: {len(self.structures)}")

                    # print(f"Number of structures selected: {len(self.structures)}")
        # #TODO: REMOVE ONCE COMPLETE
        # elif self.dungeonifyAct.isEnabled():
        #     if event.button() == Qt.LeftButton:
        #         print(f"x: {event.pos().x()}, y: {event.pos().y()}")

    # https://stackoverflow.com/questions/9552692/get-the-value-of-scrollbar-produce-by-scrollarea-in-pyqt4-python

    def clickedAStructure(self, lastClickPosition):
        # print(f"scrolled X = {self.scrollArea.horizontalScrollBar().value()}")
        # print(f"scrolled Y = {self.scrollArea.verticalScrollBar().value()}")

        lastClickPosition['x'] += self.scrollArea.horizontalScrollBar().value()
        lastClickPosition['y'] += self.scrollArea.verticalScrollBar().value()

        counter = -1
        for structure in self.structuresFromOSM:
            counter += 1
            if self.point_in_polygon(structure['nodes'], lastClickPosition):
                # print(f"{counter}, ")
                return structure
        return None

    def createActions(self):
        self.printAct = QAction(
            "&Print...", self, shortcut="Ctrl+P", enabled=False, triggered=self.print_)
        self.exitAct = QAction(
            "E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.newOSMUrlAct = QAction(
            "&New Location", self, shortcut="Ctrl+N", triggered=self.newOSMUrl)

        self.drawSelectedAct = QAction(
            "&Draw Selected", self, enabled=False, shortcut="Ctrl+D", triggered=self.drawSelected)
        self.drawRotatedAct = QAction(
            "&Draw &Rotated", self, enabled=False, shortcut="Ctrl+D", triggered=self.drawRotated)
        self.drawResizedAndRotatedAct = QAction(
            "&Draw Resized \& Rotated", self, enabled=False, shortcut="Ctrl+D", triggered=self.drawResizedAndRotated)
        self.dungeonifyAct = QAction(
            "&Draw Dungeonify", self, enabled=False, shortcut="Ctrl+D", triggered=self.drawDungeonify)

        self.zoomInAct = QAction(
            "Zoom &In (50%)", self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)
        self.zoomOutAct = QAction(
            "Zoom &Out (50%)", self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)
        self.normalSizeAct = QAction(
            "Normal &Size", self, shortcut="Ctrl+S", enabled=False, triggered=self.normalSize)
        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False, checkable=True, shortcut="Ctrl+F",
                                      triggered=self.fitToWindow)
        self.toggleGridAct = QAction("Hide &Grid", self, enabled=False, checkable=False, shortcut="Ctrl+G",
                                     triggered=self.toggleGrid)
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered=qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)
        self.fileMenu.addAction(self.newOSMUrlAct)

        self.fileMenu.addAction(self.drawSelectedAct)
        self.fileMenu.addAction(self.drawRotatedAct)
        self.fileMenu.addAction(self.drawResizedAndRotatedAct)
        self.fileMenu.addAction(self.dungeonifyAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)
        self.viewMenu.addAction(self.toggleGridAct)

        self.helpMenu = QMenu("&Help", self)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.structuresClickedLabel = QAction("Structures Clicked: 0")
        self.structuresClickedLabel.setEnabled(False)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.helpMenu)

        self.menuBar().addAction(self.structuresClickedLabel)

        self.menuHeight = 21

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def about(self):
        QMessageBox.about(self, "About Dungeonify",
                          """<p>The <b>Dungeonify</b> application is used to create DND battlemaps from OSM data. </p>

                <h1>How To Use </h1>
                <ol>
                    <li>Click on a number of structures. A key is below.</li>
                    <li>Navigate through the menu options in file to run each of the draw commands.</li>
                    <li>Navigate to the program folder to find the output file called 'Battlemap.dd2vtt'.</li>
                </ol> 

                <h2>OSM Key:</h1>
                <ul>
                    <li style="color:blue" >Blue - Structures</li>
                    <li style="color:cyan" >Cyan - Structures (Religious)</li>
                    <li style="color:red"  > Red - Roads</li>
                    <li style="color:green">Green - Boundaries</li>
                </ul> 
                
            """)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(
            self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            size = self.imageLabel.pixmap().size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(),
                                size.width(), size.height())
            painter.setWindow(self.imageLabel.pixmap().rect())
            painter.drawPixmap(0, 0, self.imageLabel.pixmap())

    def zoomIn(self):
        self.scaleImage(1.5)

    def zoomOut(self):
        self.scaleImage(0.5)
        # if self.enableToggleGrid:
        #     self.load_grid(self.currentImage)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0
        # if self.enableToggleGrid:
        #     self.load_grid(self.currentImage)


if __name__ == '__main__':
    app1 = QApplication(sys.argv)

    screen = app1.primaryScreen()
    print('Screen: %s' % screen.name())
    size = screen.size()
    print('Size: %d x %d' % (size.width(), size.height()))
    SCREEN_WIDTH = size.width()
    SCREEN_HEIGHT = size.height()

    if RUN_UNIT_TESTS:
        from osm_factory import GenerateOSM
        # Location with a Religious Structure.

        structureRotationTests = [
            {
                'text': "'Single Structure Test'",
                'url': 'https://www.openstreetmap.org/#map=19/51.87166/0.15663',
                'structureIndexes': [154],
                'expected': "[{'nodes': [{'x': 0.02136412568936663, 'y': 121.6231431711019}, {'x': 7.986130802228658, 'y': 120.6708092653388}, {'x': 7.986130802228644, 'y': 351.467481367353}, {'x': 123.89019048885301, 'y': 336.9592662855307}, {'x': 123.91008122410894, 'y': 290.44372155162614}, {'x': 299.4660920483017, 'y': 268.6909483848119}, {'x': 299.4834043582103, 'y': 113.87536353690399}, {'x': 165.8143383347669, 'y': 130.46234780034317}, {'x': 165.7498776120878, 'y': 105.97265841849854}, {'x': 124.97828745686193, 'y': 111.03844142636923}, {'x': 124.91382673617464, 'y': 0.0}, {'x': 0.0, 'y': 15.58282952841077}], 'speciality': False}]"
            },
            {
                'text': "'Multiple Complex Structures Test'",
                'url': 'https://www.openstreetmap.org/#map=19/52.62956/1.26577',
                'structureIndexes': [124, 125, 126, 139],
                'expected': "[{'nodes': [{'x': 454.0149186062607, 'y': 395.43533249371256}, {'x': 454.040461195938, 'y': 379.1628862739759}, {'x': 448.6256070815956, 'y': 378.41024209294613}, {'x': 448.6256070815956, 'y': 254.41082477103612}, {'x': 535.5854756643711, 'y': 267.7116791709112}, {'x': 535.6650674084179, 'y': 335.9270131809757}, {'x': 560.9642589427566, 'y': 339.73496754784156}, {'x': 560.8846671899245, 'y': 395.51905084989323}, {'x': 535.6413555134488, 'y': 391.66097029271833}, {'x': 509.8301789477291, 'y': 387.7319439497733}, {'x': 509.8605162245884, 'y': 403.95426398909507}, {'x': 509.81195914567036, 'y': 437.85101642541724}, {'x': 399.88023845139736, 'y': 420.97586462194306}, {'x': 399.9287955216422, 'y': 387.0791121757271}], 'speciality': False}, {'nodes': [{'x': 698.5905195356526, 'y': 82.22793198485317}, {'x': 741.9096620239033, 'y': 81.92857096120792}, {'x': 741.9096620239033, 'y': 252.00058961561007}, {'x': 711.5057889378974, 'y': 251.99335066808334}, {'x': 722.0125784169437, 'y': 290.97721549529666}, {'x': 608.5489131676728, 'y': 332.78939127185896}, {'x': 579.8539784000479, 'y': 226.37773026064266}, {'x': 693.317643649319, 'y': 184.5655544840804}, {'x': 698.6071722614244, 'y': 204.20184459513774}], 'speciality': False}, {'nodes': [{'x': 962.317021213135, 'y': 204.33322473770494}, {'x': 936.5738364469427, 'y': 285.0479079664532}, {'x': 910.6264937414575, 'y': 272.62202631588804}, {'x': 878.414409741959, 'y': 271.8959245779043}, {'x': 879.5264088012951, 'y': 287.4278786237665}, {'x': 881.8056886966799, 'y': 320.83874789914495}, {'x': 831.2831885841767, 'y': 321.7828605988052}, {'x': 828.9305948962135, 'y': 288.3881245589216}, {'x': 769.1348047010139, 'y': 289.45610227820845}, {'x': 763.0799566803487, 'y': 202.91105880191213}, {'x': 856.7773549919774, 'y': 201.16527289688395}, {'x': 853.0366651423601, 'y': 133.8686652877837}, {'x': 954.8815033012827, 'y': 133.8686652877837}, {'x': 936.3387307234912, 'y': 191.76670797077557}], 'speciality': False}, {'nodes': [{'x': 31.325563527301533, 'y': 0.0}, {'x': 95.84245751857664, 'y': 1.5013230703632843}, {'x': 94.87566813962798, 'y': 124.17776056159805}, {'x': 62.017140338673, 'y': 123.45066612932679}, {'x': 62.01330574169579, 'y': 358.6399832641804}, {'x': 0.0, 'y': 357.76089131383236}, {'x': 1.7763568394002505e-15, 'y': 36.393341451118744}, {'x': 30.966322328377423, 'y': 36.76241584240154}], 'speciality': False}]"
            },
            {
                'text': "'Diagonal Structures Test'",
                'url': 'https://www.openstreetmap.org/#map=19/51.48076/-2.63602',
                'structureIndexes': [7, 148, 18],
                'expected': "[{'nodes': [{'x': 183.44870962735328, 'y': 661.0176740400761}, {'x': 130.47634247501762, 'y': 661.3420103808976}, {'x': 87.6610761557082, 'y': 716.6168954855116}, {'x': 20.188812527794607, 'y': 717.1578930279074}, {'x': 0.0, 'y': 743.4253229155092}, {'x': 2.05042892467911, 'y': 777.6797809714785}, {'x': 14.28737937706821, 'y': 800.0259767725133}, {'x': 191.0907859867471, 'y': 800.0259767725133}], 'speciality': False}, {'nodes': [{'x': 616.2054684238428, 'y': 268.5947056105516}, {'x': 723.0899498468208, 'y': 257.9382275204053}, {'x': 724.8357262786325, 'y': 242.67202633382823}, {'x': 799.2460791322218, 'y': 235.20554119808156}, {'x': 802.1899319650249, 'y': 177.44823454184967}, {'x': 916.5747294726324, 'y': 163.79052061537647}, {'x': 915.9320799307568, 'y': 175.93382967619908}, {'x': 1033.5677151630427, 'y': 160.9809184115561}, {'x': 1033.3691843428192, 'y': 174.5028672830466}, {'x': 1166.0658741699856, 'y': 156.01234746863355}, {'x': 1166.0658741699856, 'y': 4.6668534471089345}, {'x': 1107.7611598730457, 'y': 13.546316896604168}, {'x': 1107.8907061022908, 'y': 0.0}, {'x': 986.1139769659156, 'y': 18.988034988453236}, {'x': 986.7566265165547, 'y': 6.844725902819945}, {'x': 926.7752595917078, 'y': 14.97921051950361}, {'x': 927.0821748721728, 'y': 3.786346861260199}, {'x': 855.530401271984, 'y': 13.484353093235256}, {'x': 856.1596854883818, 'y': 27.298718414055656}, {'x': 799.2728097919407, 'y': 31.944698388460438}, {'x': 798.812402063771, 'y': 90.57925440478738}, {'x': 746.8234319987646, 'y': 96.95536503705335}, {'x': 745.5936825515785, 'y': 79.56905263877104}, {'x': 724.7109832136089, 'y': 81.35566991253029}, {'x': 723.229937746512, 'y': 101.14426359145412}, {'x': 613.703645987649, 'y': 114.22739102477092}], 'speciality': False}, {'nodes': [{'x': 1331.367014113456, 'y': 213.4077395327082}, {'x': 1331.311776246619, 'y': 272.79270276472033}, {'x': 1341.729688261381, 'y': 271.43086480577773}, {'x': 1341.7033117036547, 'y': 341.5568013884512}, {'x': 1353.8475503063094, 'y': 339.8388427369744}, {'x': 1353.8145477535538, 'y': 414.7995171464734}, {'x': 1367.6413431435315, 'y': 412.86262457167237}, {'x': 1367.6324235314212, 'y': 495.6908670044381}, {'x': 1360.1435836429907, 'y': 496.7780201809483}, {'x': 1360.1883728252792, 'y': 572.2169690977707}, {'x': 1424.8760521705635, 'y': 563.2300259864362}, {'x': 1424.8594234700781, 'y': 632.6033145481604}, {'x': 1432.3044935662224, 'y': 631.6533481158838}, {'x': 1432.2972304555105, 'y': 713.2729060824283}, {'x': 1425.7761044172653, 'y': 714.2153560500747}, {'x': 1425.7543150859885, 'y': 793.7141566980044}, {'x': 1415.222932906878, 'y': 795.1909433137873}, {'x': 1415.261287224157, 'y': 868.9651713571752}, {'x': 1290.7244977762284, 'y': 886.2155415604989}, {'x': 1290.7244977762284, 'y': 720.8556683085208}, {'x': 1308.5615493070718, 'y': 718.3844390855836}, {'x': 1308.5377849225545, 'y': 589.4445243728264}, {'x': 1152.7991205824687, 'y': 611.0992581414821}, {'x': 1152.8437186273113, 'y': 527.677792531837}, {'x': 1236.5452644740965, 'y': 516.1416312384381}, {'x': 1236.521627511401, 'y': 437.98870180087107}, {'x': 1217.5077610099, 'y': 440.5379199829354}, {'x': 1217.528339821725, 'y': 291.96244237439174}, {'x': 1164.3397565057367, 'y': 299.32789566107897}, {'x': 1164.3124242764889, 'y': 236.59125256909834}], 'speciality': False}]"
            },
            {
                'text': "'Large Structure Test'",
                'url': 'https://www.openstreetmap.org/#map=19/47.91488/1.93173',
                'structureIndexes': [330, 252],
                'expected': "[{'nodes': [{'x': 3.552713678800501e-15, 'y': 2.994282159479326}, {'x': 0.0, 'y': 881.1363119726489}, {'x': 110.5045824537298, 'y': 876.7821176188384}, {'x': 109.8535521985007, 'y': 784.4640844913627}, {'x': 80.43679468729307, 'y': 787.2620583682643}, {'x': 81.16251505803841, 'y': 0.0}], 'speciality': False}]"
            },
            {
                'text': "'Twenty Structures Test'",
                'url': 'https://www.openstreetmap.org/#map=19/35.68263/139.72467',
                'structureIndexes': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
                'expected': "[{'nodes': [{'x': 3357.775977707757, 'y': 3247.73369657312}, {'x': 3283.6839335326035, 'y': 3200.3257967100017}, {'x': 3283.2486878172995, 'y': 3146.1455746513184}, {'x': 3314.3259123512703, 'y': 3166.2280356587353}, {'x': 3314.3259123512703, 'y': 2701.0183575396204}, {'x': 3366.046340777323, 'y': 2742.7409604308996}], 'speciality': False}, {'nodes': [{'x': 3737.9587263708786, 'y': 2073.3542461010493}, {'x': 3737.9428021641816, 'y': 2151.477215972058}, {'x': 3719.2363111392892, 'y': 2148.690092263254}, {'x': 3719.2418233664484, 'y': 2269.7649642330643}, {'x': 3678.951920766462, 'y': 2263.8838469812017}, {'x': 3678.9519207664625, 'y': 1947.3589099946169}, {'x': 3719.235545557838, 'y': 1953.0961641503832}, {'x': 3719.2522353341105, 'y': 2070.5671223927648}], 'speciality': False}, {'nodes': [{'x': 3485.3664089009985, 'y': 2090.307683303364}, {'x': 3485.366408924533, 'y': 2219.5045709676524}, {'x': 3443.283866604883, 'y': 2200.844457223596}, {'x': 3443.283866604883, 'y': 2071.64756955591}], 'speciality': False}, {'nodes': [{'x': 3609.292997845208, 'y': 2637.890778214206}, {'x': 3609.292997845208, 'y': 2839.7373657572452}, {'x': 3547.604469726974, 'y': 2810.7290441869045}, {'x': 3547.549044282902, 'y': 2608.8910928911746}], 'speciality': False}, {'nodes': [{'x': 2505.0102183220556, 'y': 3279.0786163436405}, {'x': 2505.010218322056, 'y': 2735.2516972877065}, {'x': 2453.280618960668, 'y': 2702.5311168941744}, {'x': 2447.330811134197, 'y': 2734.852988104266}, {'x': 2374.211497149496, 'y': 2699.4898327285855}, {'x': 2327.183442239445, 'y': 2700.4478211569176}, {'x': 2311.764597283711, 'y': 2707.984622126065}, {'x': 2295.395726449438, 'y': 2718.7083869699827}, {'x': 2274.5349641913604, 'y': 2753.3262555112206}, {'x': 2264.7019344008586, 'y': 2798.649304816083}, {'x': 2266.0010551530577, 'y': 3104.5041309459657}], 'speciality': False}, {'nodes': [{'x': 493.46351714876675, 'y': 982.003716216801}, {'x': 541.1816379778248, 'y': 955.9400811321032}, {'x': 580.7304504143978, 'y': 1018.0738511274408}, {'x': 580.7304504143976, 'y': 1253.2935032044618}, {'x': 549.9717548659827, 'y': 1300.9740597932555}, {'x': 526.975123080324, 'y': 1265.1920610930015}, {'x': 507.817249973924, 'y': 1310.411503833441}, {'x': 454.64430407266434, 'y': 1307.6249315606442}, {'x': 435.9258870170679, 'y': 1273.3152397138206}, {'x': 425.7422304993311, 'y': 1197.474857984138}, {'x': 429.95269131220925, 'y': 1103.4969672476418}], 'speciality': False}, {'nodes': [{'x': 11.106578096686645, 'y': 1472.3192741997973}, {'x': 81.89817444118823, 'y': 1472.0107131138564}, {'x': 81.89817444118822, 'y': 1632.8589576560084}, {'x': 37.751560139760066, 'y': 1633.0699794626362}, {'x': 37.80705168610612, 'y': 1601.2460278525682}, {'x': 11.105975456939186, 'y': 1601.3434692939213}], 'speciality': False}, {'nodes': [{'x': 227.58179917649642, 'y': 2054.1766250167866}, {'x': 227.5975619644494, 'y': 1974.5401813931903}, {'x': 288.0385748477963, 'y': 1972.31061579722}, {'x': 288.0228120479553, 'y': 2051.9470594206887}, {'x': 338.7554309708077, 'y': 2050.045015426369}, {'x': 338.7554309708077, 'y': 2326.2530159754942}, {'x': 200.42135249922183, 'y': 2331.24433086881}, {'x': 200.36371152912957, 'y': 2055.179718205567}], 'speciality': False}, {'nodes': [{'x': 0.0, 'y': 2171.7840702613375}, {'x': 140.6843932896573, 'y': 2171.7840702613375}, {'x': 140.6843932896573, 'y': 2402.6160702562765}, {'x': 0.0, 'y': 2402.6160702562765}], 'speciality': False}, {'nodes': [{'x': 631.2318037045065, 'y': 1389.3485505870487}, {'x': 571.2658277766446, 'y': 1561.5886050237718}, {'x': 328.6221637851133, 'y': 1561.5886050237718}, {'x': 388.6500117640849, 'y': 1389.2185204032608}], 'speciality': False}, {'nodes': [{'x': 480.50585577297517, 'y': 1952.7570178447938}, {'x': 493.98938536510235, 'y': 1948.770517954447}, {'x': 494.0060504970001, 'y': 1923.0355510177922}, {'x': 582.8760471891652, 'y': 1896.9450279578537}, {'x': 582.8760471891652, 'y': 2075.7990573781863}, {'x': 480.54844444074894, 'y': 2105.589249423746}], 'speciality': False}, {'nodes': [{'x': 410.8955042714679, 'y': 1338.5566710344403}, {'x': 322.14422919903325, 'y': 1369.8565722058188}, {'x': 322.14422919903325, 'y': 1021.4114694818509}, {'x': 410.895504270017, 'y': 990.1115683235485}], 'speciality': False}, {'nodes': [{'x': 313.7685189905677, 'y': 1715.9705065581868}, {'x': 313.78554545864216, 'y': 1815.3307584533004}, {'x': 220.10631577039786, 'y': 1814.6943575339044}, {'x': 220.08928929045047, 'y': 1853.8625144998955}, {'x': 163.76942334827677, 'y': 1853.4233466911112}, {'x': 163.76942334827675, 'y': 1714.8949378366142}], 'speciality': False}, {'nodes': [{'x': 476.63425170058116, 'y': 1921.7307291354257}, {'x': 476.6342517005812, 'y': 2102.171495236018}, {'x': 379.7006557822147, 'y': 2132.829411392073}, {'x': 379.70065578221454, 'y': 1952.3886452914812}], 'speciality': False}, {'nodes': [{'x': 590.6218905497278, 'y': 204.88801295890335}, {'x': 588.8105416328756, 'y': 245.83417545613554}, {'x': 628.8805413579372, 'y': 272.60623456927675}, {'x': 612.9468110794052, 'y': 455.54939785761786}, {'x': 590.3112704034556, 'y': 443.2646048443756}, {'x': 587.7540719254775, 'y': 443.7138404672346}, {'x': 585.7946366595579, 'y': 448.3097532474557}, {'x': 579.2932846132853, 'y': 510.32747466443755}, {'x': 577.0647656184352, 'y': 514.2188741407055}, {'x': 574.1247097394271, 'y': 514.8364484782293}, {'x': 561.456102926432, 'y': 505.5325357203019}, {'x': 553.5118119121066, 'y': 606.3090134448478}, {'x': 451.2329028160663, 'y': 543.9117137389136}, {'x': 436.1624076044605, 'y': 603.7264359599801}, {'x': 346.65323746784554, 'y': 551.3481146379813}, {'x': 354.6462886086551, 'y': 485.3410038864373}, {'x': 314.8200895686865, 'y': 457.97649110186444}, {'x': 308.08577243407353, 'y': 457.24533391292977}, {'x': 306.1895447315727, 'y': 449.428856190162}, {'x': 304.7032634440102, 'y': 441.8751895874358}, {'x': 300.99388090298123, 'y': 431.1426688117485}, {'x': 301.8462803954307, 'y': 460.81160540259293}, {'x': 300.70132005980304, 'y': 468.53059182449124}, {'x': 297.63846088130776, 'y': 474.3501038304701}, {'x': 293.88212415252497, 'y': 477.18322390820873}, {'x': 290.4472431467274, 'y': 477.9761718398273}, {'x': 206.28182321068792, 'y': 466.815880825909}, {'x': 202.176941759862, 'y': 439.94840733201625}, {'x': 183.1568751868284, 'y': 438.6906032070731}, {'x': 182.24849183480475, 'y': 462.69881129492495}, {'x': 181.0963077742181, 'y': 464.9354617084929}, {'x': 179.44207485438156, 'y': 466.3379519724616}, {'x': 121.80578310602402, 'y': 456.9736614344675}, {'x': 121.82564835978977, 'y': 451.9224752696448}, {'x': 108.30644796020412, 'y': 452.3390292144444}, {'x': 109.78911743295481, 'y': 457.15152781330596}, {'x': 107.49016710416545, 'y': 459.0273772389911}, {'x': 66.37453325039462, 'y': 459.4463963889492}, {'x': 63.84803560438273, 'y': 409.3943226208725}, {'x': 73.91068380541434, 'y': 388.85090629329346}, {'x': 71.46725900184819, 'y': 379.4816853558769}, {'x': 70.35480543278072, 'y': 277.6871157746958}, {'x': 62.51887029197228, 'y': 272.84093841067687}, {'x': 62.518870291972306, 'y': 0.0}, {'x': 182.9708642656053, 'y': 13.497506755266727}, {'x': 183.2742607032566, 'y': 2.224296834307495}, {'x': 262.3126422070318, 'y': 6.92537218736453}, {'x': 270.0329977574952, 'y': 17.983020971588985}, {'x': 280.89567343072645, 'y': 16.434819874304196}, {'x': 299.4082733770836, 'y': 32.87432204202611}, {'x': 299.9626942324401, 'y': 44.38220354710131}, {'x': 294.328189128763, 'y': 44.159081396908164}, {'x': 294.78328377216405, 'y': 54.0860801375332}, {'x': 308.4270933911215, 'y': 56.54737592167453}, {'x': 308.16884524819665, 'y': 50.64795983451626}, {'x': 309.6731858802682, 'y': 45.07065285458265}, {'x': 312.87148988119503, 'y': 41.406890070615475}], 'speciality': False}, {'nodes': [{'x': 160.94431768010784, 'y': 1434.3286296344127}, {'x': 228.33391166311526, 'y': 1430.442941050064}, {'x': 228.3419880418071, 'y': 1462.7038171563638}, {'x': 239.29110045869268, 'y': 1462.1713782253041}, {'x': 239.29110045869268, 'y': 1570.1872409967689}, {'x': 221.3213646708944, 'y': 1571.1754316648676}, {'x': 221.36399004827425, 'y': 1601.420603842123}, {'x': 160.99255165143228, 'y': 1604.9945195401115}], 'speciality': False}, {'nodes': [{'x': 686.2682728598214, 'y': 936.5403422789152}, {'x': 686.2682728605756, 'y': 1700.8529362972836}, {'x': 598.9633137140793, 'y': 1717.3317982543078}, {'x': 598.9633137140794, 'y': 953.0192042228052}], 'speciality': False}, {'nodes': [{'x': 718.3998913762731, 'y': 2051.535948284318}, {'x': 718.355722092024, 'y': 2082.3273017845268}, {'x': 761.6695606598558, 'y': 2056.09278700521}, {'x': 761.6695606598558, 'y': 2287.615864025117}, {'x': 748.776004110398, 'y': 2295.4196949583848}, {'x': 748.7737363279463, 'y': 2326.809662991781}, {'x': 666.8098604724178, 'y': 2376.3149664139655}, {'x': 666.8123375859212, 'y': 2334.903675879832}, {'x': 638.4039557396121, 'y': 2352.003889614688}, {'x': 638.4317970278563, 'y': 2176.7833827178165}, {'x': 666.8708112915257, 'y': 2159.5424648451}, {'x': 666.880475502887, 'y': 2082.763204645651}], 'speciality': False}, {'nodes': [{'x': 606.5478338315405, 'y': 1633.6316583886473}, {'x': 575.8408280585364, 'y': 1742.2617486460704}, {'x': 462.41307641660364, 'y': 1742.2617486460704}, {'x': 493.118629166415, 'y': 1633.4771253649471}], 'speciality': False}, {'nodes': [{'x': 153.39941658892974, 'y': 1731.8496122607683}, {'x': 153.38617250735564, 'y': 1850.372018890772}, {'x': 61.60712875284028, 'y': 1854.6179026978502}, {'x': 61.56620794949682, 'y': 1878.6675033971067}, {'x': 20.363986870114374, 'y': 1880.5650642244739}, {'x': 20.363986870114374, 'y': 1737.8483201236118}], 'speciality': False}]"
            },
            {
                'text': "'Religious Structure Test'",
                'url': 'https://www.openstreetmap.org/#map=19/51.87076/0.15715',
                'structureIndexes': [2, 3],
                'expected': "[{'nodes': [{'x': 700.0587596563277, 'y': 184.25135277100864}, {'x': 712.1292616512218, 'y': 83.78899247538845}, {'x': 803.5636314053181, 'y': 85.7978566451456}, {'x': 813.8066199354113, 'y': 4.263256414560601e-14}, {'x': 1228.842557354319, 'y': 0.0}, {'x': 1227.9281206684745, 'y': 97.02947103199693}, {'x': 1212.439838057778, 'y': 225.52764830487652}, {'x': 1195.2533862932578, 'y': 223.5350680737051}, {'x': 785.5470258057601, 'y': 236.6773309529635}, {'x': 791.6118965856076, 'y': 186.15032597248185}], 'speciality': True}, {'nodes': [{'x': 199.40900105986043, 'y': 720.8739923917157}, {'x': 196.45132440018585, 'y': 643.8033819138515}, {'x': 224.35888234067488, 'y': 639.0560386348881}, {'x': 229.25565164023755, 'y': 629.0963033275995}, {'x': 229.4440951424637, 'y': 617.8820867835093}, {'x': 223.0938573799038, 'y': 609.225196140125}, {'x': 212.56562033832415, 'y': 610.4419445675869}, {'x': 212.4882904212193, 'y': 553.9164019612701}, {'x': 158.50982430431839, 'y': 560.3525219581583}, {'x': 159.93072942712212, 'y': 286.37881892989435}, {'x': 43.46140466445655, 'y': 301.97088032577983}, {'x': 43.45022907912876, 'y': 314.1396208588561}, {'x': 8.089069042654089, 'y': 318.316140569145}, {'x': 8.089069042654089, 'y': 649.216248920637}, {'x': 0.0, 'y': 650.2591007923683}, {'x': 0.03314139196984911, 'y': 745.3914994168546}, {'x': 49.162816158791216, 'y': 739.4622598797263}, {'x': 49.12691297881689, 'y': 760.4897020195327}, {'x': 56.69670263251179, 'y': 780.0295293858377}, {'x': 66.76622682422182, 'y': 791.4490865144637}, {'x': 80.27462015212551, 'y': 799.0859274199595}, {'x': 96.83343466240579, 'y': 803.7257917715438}, {'x': 112.58728583429418, 'y': 801.5134998229146}, {'x': 127.06101857974163, 'y': 796.3646448207127}, {'x': 140.59998420309012, 'y': 784.0243607958852}, {'x': 152.02284617787808, 'y': 770.0008184223234}, {'x': 158.27918332920575, 'y': 757.2909942287102}, {'x': 161.23519007275166, 'y': 742.9954089897195}, {'x': 160.6966424334529, 'y': 727.506932533648}], 'speciality': True}]"
            },
            {
                'text': "'Curved Structure Test'",
                'url': 'https://www.openstreetmap.org/#map=19/50.81802/4.39547',
                'structureIndexes': [1, 2, 5],
                'expected': "[{'nodes': [{'x': 340.76230607220384, 'y': 0.0}, {'x': 346.55670849112795, 'y': 0.36654960725670094}, {'x': 352.271287090268, 'y': 1.1814926119470783}, {'x': 357.90604187463765, 'y': 2.4448290018212333}, {'x': 363.3976281707185, 'y': 4.122083138946948}, {'x': 368.61386358957236, 'y': 6.305260081333444}, {'x': 373.6180927975793, 'y': 9.028835478006414}, {'x': 378.352464171534, 'y': 12.097377346759515}, {'x': 382.88032238368027, 'y': 15.54536132483139}, {'x': 387.0694850446564, 'y': 19.46479247000056}, {'x': 390.98878986444043, 'y': 23.72919009834277}, {'x': 394.5060544591102, 'y': 28.430559255618306}, {'x': 397.6901165462078, 'y': 33.44241924704113}, {'x': 400.5409761244594, 'y': 38.764770071917695}, {'x': 402.9952885203453, 'y': 44.36313609231536}, {'x': 405.1218914509838, 'y': 50.11103661321704}, {'x': 406.7831094829885, 'y': 56.26143302511932}, {'x': 408.053273376652, 'y': 62.52688829982449}, {'x': 408.86354542029494, 'y': 69.0338831203311}, {'x': 409.2827633314611, 'y': 75.65593679185372}, {'x': 409.31092710343535, 'y': 82.39304932571625}, {'x': 408.8846920685638, 'y': 89.21074507219961}, {'x': 408.07289594353927, 'y': 95.98254333605541}, {'x': 406.80670100580454, 'y': 102.83492482431896}, {'x': 405.154944984206, 'y': 109.64140881839916}, {'x': 403.11762787916854, 'y': 116.40199531852721}, {'x': 400.6314050104592, 'y': 123.08220869809517}, {'x': 397.75962105074706, 'y': 129.71652459457292}, {'x': 394.57111372428955, 'y': 136.17846230185054}, {'x': 391.07137607842475, 'y': 142.3070654740346}, {'x': 387.18607734283245, 'y': 148.38977116382262}, {'x': 382.98954828910803, 'y': 154.13914231921117}, {'x': 378.5451335827817, 'y': 159.58965458876355}, {'x': 373.7206508429047, 'y': 164.8333130198584}, {'x': 368.7171201671193, 'y': 169.65163186986888}, {'x': 363.5290485261042, 'y': 174.20556744955817}, {'x': 358.0297465610926, 'y': 178.4261685066349}, {'x': 352.4835790625385, 'y': 182.12942490196886}, {'x': 346.6895259189462, 'y': 185.53382240060455}, {'x': 340.8486072367969, 'y': 188.42087524974707}, {'x': 334.8919853056862, 'y': 190.9170641330886}, {'x': 332.73569452169147, 'y': 191.7108441626866}, {'x': 178.00939168589818, 'y': 225.86930409128712}, {'x': 177.3554650907095, 'y': 301.7482718031043}, {'x': 250.2269870106149, 'y': 285.83126231264094}, {'x': 249.9917067903163, 'y': 332.42780790507817}, {'x': 249.75490249492498, 'y': 392.30314657032187}, {'x': 172.6477016575326, 'y': 407.5543273606909}, {'x': 172.2196885246566, 'y': 484.3759793264287}, {'x': 325.27448576930425, 'y': 451.9309299112208}, {'x': 331.4185698320367, 'y': 451.504119673463}, {'x': 337.48283007957417, 'y': 451.525702820658}, {'x': 343.5306111867106, 'y': 452.0301549914322}, {'x': 349.3663860897146, 'y': 453.07500560516854}, {'x': 354.99015478229666, 'y': 454.6602546734226}, {'x': 360.53959270957193, 'y': 456.5329407821241}, {'x': 365.74484203034905, 'y': 459.0380304144462}, {'x': 370.8069228632622, 'y': 461.9570377942512}, {'x': 375.59914586756173, 'y': 465.2210116341177}, {'x': 380.1160179816313, 'y': 468.99090830212526}, {'x': 384.2308498710109, 'y': 473.19777649929733}, {'x': 388.07582393177756, 'y': 477.7496111565313}, {'x': 391.58759547783364, 'y': 482.6119366590059}, {'x': 394.7606714664295, 'y': 487.945709340133}, {'x': 397.47385560585525, 'y': 493.5210215675245}, {'x': 399.79049256291535, 'y': 499.37234899043693}, {'x': 401.77392700568976, 'y': 505.5341672588213}, {'x': 403.3029626483324, 'y': 511.77656872850207}, {'x': 404.4354511027447, 'y': 518.2949854054905}, {'x': 405.10804770127254, 'y': 525.0549416400677}, {'x': 405.3262455000938, 'y': 531.8954810761725}, {'x': 405.1533891530094, 'y': 538.8510793859418}, {'x': 404.5261339999285, 'y': 545.8872609087944}, {'x': 403.5133177688484, 'y': 552.8775449256768}, {'x': 402.0461027191936, 'y': 559.9484121787536}, {'x': 400.1988196342885, 'y': 566.8124255924483}, {'x': 397.8971377366732, 'y': 573.7570222305505}, {'x': 395.2098947493293, 'y': 580.6557213862563}, {'x': 392.07923905321684, 'y': 587.3130910646473}, {'x': 388.69520465631365, 'y': 593.8325582026323}, {'x': 384.8677575452017, 'y': 600.1106958753206}, {'x': 380.79242479534145, 'y': 606.0899746397552}, {'x': 376.40036867202156, 'y': 611.896875226314}, {'x': 371.62824450673673, 'y': 617.4969219848144}, {'x': 366.61372773958857, 'y': 622.6371535134363}, {'x': 361.4146700067857, 'y': 627.5130017715054}, {'x': 355.9732196658299, 'y': 631.9290348112511}, {'x': 350.28388367941153, 'y': 636.0462089540679}, {'x': 344.47884443774245, 'y': 639.7725191426393}, {'x': 338.9546491294775, 'y': 642.8319501698886}, {'x': 272.11442918888594, 'y': 659.7362808315938}, {'x': 273.09520794448275, 'y': 693.3871577702203}, {'x': 0.0, 'y': 755.096463954311}, {'x': 7.105427357601002e-14, 'y': 100.95209260418001}, {'x': 0.07140960605345725, 'y': 98.85966017737671}, {'x': 0.3961979057582852, 'y': 96.9051303020724}, {'x': 0.916513281773284, 'y': 94.8930709842737}, {'x': 1.7590450681325862, 'y': 92.89243352272564}, {'x': 2.659428478972494, 'y': 91.08722804407793}, {'x': 3.8820283060214464, 'y': 89.29344440989406}, {'x': 5.28916910543893, 'y': 87.7640440349382}, {'x': 6.822999251469838, 'y': 86.3035949356163}, {'x': 8.409187979232058, 'y': 85.19953415260686}, {'x': 10.185410727976404, 'y': 84.19890028362639}, {'x': 11.29522845902791, 'y': 83.81924808155321}, {'x': 271.60427436263825, 'y': 28.1027434408345}, {'x': 271.84526988620513, 'y': 13.478770199763773}, {'x': 334.7558974545862, 'y': 0.1738488236871092}], 'speciality': False}, {'nodes': [{'x': 635.4338101439596, 'y': 1777.1734490867934}, {'x': 674.5557454819814, 'y': 1752.0874760223553}, {'x': 668.2329832775372, 'y': 1704.7914295983428}, {'x': 671.1380915145999, 'y': 1645.4916278492553}, {'x': 685.6252070948349, 'y': 1598.9458161456216}, {'x': 699.9402209527534, 'y': 1561.9186073011026}, {'x': 729.5122949901859, 'y': 1523.9223452980166}, {'x': 696.949941633834, 'y': 1501.7435317303784}, {'x': 754.9461763012921, 'y': 1292.0998203707045}, {'x': 1214.737736093627, 'y': 1292.0998203707045}, {'x': 1180.5423951967368, 'y': 1452.7438273262478}, {'x': 1172.2802530471806, 'y': 1491.3496550409448}, {'x': 1147.4505884630087, 'y': 1503.8379369595382}, {'x': 1149.488123523328, 'y': 1545.382183943884}, {'x': 1144.3204613974444, 'y': 1602.5563206828429}, {'x': 1131.449998235534, 'y': 1648.21122867865}, {'x': 1099.9753744319328, 'y': 1717.936166898961}, {'x': 1087.5526207896721, 'y': 1736.113728691454}, {'x': 1055.2447236166502, 'y': 1778.9708864106124}, {'x': 1004.1103834827479, 'y': 1829.4085406711897}, {'x': 952.3839978682956, 'y': 1861.903081481376}, {'x': 923.8645407576837, 'y': 1874.2663242868275}, {'x': 895.1418690477983, 'y': 1886.6451969754753}, {'x': 835.4235600741463, 'y': 1898.0862762705108}, {'x': 774.5963699244512, 'y': 1900.618318417959}, {'x': 722.885296516388, 'y': 1889.724285247541}, {'x': 710.2203761115195, 'y': 1884.0037455978688}, {'x': 682.3905090175695, 'y': 1921.406071801995}, {'x': 601.7962989713062, 'y': 1929.955621491477}], 'speciality': False}, {'nodes': [{'x': 1419.2946927773855, 'y': 723.2929783392898}, {'x': 1579.5930222521677, 'y': 722.4130221258889}, {'x': 1573.9369620106502, 'y': 836.0965074766614}, {'x': 1727.35887403442, 'y': 836.0899103683728}, {'x': 1686.4170848033252, 'y': 1016.0498226425472}, {'x': 1343.2431569278654, 'y': 1016.0498226425473}, {'x': 1384.1849461496747, 'y': 836.0899103776936}], 'speciality': False}]"
            },
            {
                'text': "'Curved and Tapered Structure Test'",
                'url': 'https://www.openstreetmap.org/#map=19/50.81705/4.39651',
                'structureIndexes': [47],
                'expected': "[{'nodes': [{'x': 65.32837124306499, 'y': 2.249983747426512}, {'x': 65.33674861585507, 'y': 94.69760031163594}, {'x': 79.15945595898117, 'y': 91.64266571267879}, {'x': 79.12924666673547, 'y': 0.0}, {'x': 89.64724326293216, 'y': 9.385820432567968}, {'x': 93.92724883855942, 'y': 13.309777011447437}, {'x': 108.7252510108095, 'y': 26.61955402312283}, {'x': 123.52761957007888, 'y': 39.76834085721313}, {'x': 144.9363802376536, 'y': 59.066143374837836}, {'x': 166.41309066030124, 'y': 78.23698594485813}, {'x': 187.8218513216679, 'y': 97.53478847408218}, {'x': 209.61211222689906, 'y': 117.03677231268085}, {'x': 231.2708400023696, 'y': 136.6316858802747}, {'x': 252.92956777826623, 'y': 156.2265994480964}, {'x': 263.8290646187537, 'y': 165.81660119026674}, {'x': 274.66497808540583, 'y': 175.37257271428422}, {'x': 285.2334588980302, 'y': 185.27539388479215}, {'x': 292.39463582770543, 'y': 192.37464222976027}, {'x': 299.41991323354074, 'y': 199.7278104924522}, {'x': 306.18212437407254, 'y': 207.26683822496204}, {'x': 312.617685875466, 'y': 214.95769520913728}, {'x': 318.85376448581803, 'y': 222.8684418815114}, {'x': 324.8267768242325, 'y': 230.96504803507509}, {'x': 331.2735250723897, 'y': 240.62181731792086}, {'x': 337.32567392633564, 'y': 250.55737580003597}, {'x': 343.1147565012835, 'y': 260.67879377448384}, {'x': 349.6780263186372, 'y': 273.17448665566377}, {'x': 354.5682088890764, 'y': 283.1414619179435}, {'x': 355.8466967347188, 'y': 285.9489687472567}, {'x': 361.62076774952936, 'y': 299.0022400492627}, {'x': 366.8468743014348, 'y': 313.23218116540585}, {'x': 371.6783814529207, 'y': 327.74091149241804}, {'x': 375.9201726929054, 'y': 342.58733055205687}, {'x': 379.4625468194222, 'y': 357.05941721132814}, {'x': 382.6146879325393, 'y': 371.64930290388367}, {'x': 385.17711314078844, 'y': 386.5768773176941}, {'x': 387.00710256186414, 'y': 399.9691578949121}, {'x': 388.37890920205075, 'y': 413.6061974762176}, {'x': 389.4920159577457, 'y': 427.26810636135554}, {'x': 390.2192560883383, 'y': 440.8868241028764}, {'x': 390.55189681145146, 'y': 454.7843310664102}, {'x': 391.0160706771674, 'y': 468.5889082779777}, {'x': 382.2794916883486, 'y': 469.6294848769168}, {'x': 382.2302090695964, 'y': 652.2027951685964}, {'x': 317.91353612407784, 'y': 666.6149106854954}, {'x': 130.30397914916, 'y': 707.9730200853596}, {'x': 0.0, 'y': 736.5564261179306}, {'x': 1.4210854715202004e-14, 'y': 122.93654889411843}, {'x': 10.836742741569111, 'y': 120.57008667873666}, {'x': 10.818007903140852, 'y': 14.234124064858023}], 'speciality': False}]"
            },
        ]

        # DISABLE_SHOWN_PIPELINE_STEPS = True
        app2 = QApplication(sys.argv)
        qImageViewer = QDungeonifyViewer()

        # counter = 0
        passedTestCounter = 0
        failedTestCounter = 0
        for structureRotationTest in structureRotationTests:
            urlInput = structureRotationTest['url']
            structureIndexes = structureRotationTest['structureIndexes']

            text = urlInput.split('/')
            # scrX': 805, 'scrY': 742

            longitudeInput = text[-1].split('&')[0]
            latitudeInput = text[-2]

            # https://www.openstreetmap.org/#map=19/52.62640/1.34811
            generateOSM = GenerateOSM()
            structuresFromOSM, roads, inchesPerPixel = generateOSM.generate(
                longitudeInput, latitudeInput, SCREEN_WIDTH, SCREEN_HEIGHT)

            selectedStructures = []

            for structureIndex in range(len(structuresFromOSM) - 1):
                if structureIndex in structureIndexes:
                    selectedStructures.append(
                        structuresFromOSM[structureIndex])

            qImageViewer.structures = selectedStructures
            qImageViewer.drawSelected()
            qImageViewer.drawRotated()
            structuresArray = qImageViewer.drawResizedAndRotated()

            if str(structuresArray) == structureRotationTest['expected']:
                print(f"Unit Test: { structureRotationTest['text'] } Passed")
                passedTestCounter += 1
            else:
                print(
                    f"ERROR: Unit Test: { structureRotationTest['text'] } Failed")
                failedTestCounter += 1

        print(f"\n-----")
        print(f"{passedTestCounter} / {len(structureRotationTests)} Unit Tests Passed")
        print(f"{failedTestCounter} / {len(structureRotationTests)} Unit Tests Failed")
        print(f"-----\n")

        sys.exit()

    if not DEBUGGING:
        windowOpenStreetMap = QWebEngineView()
        windowOpenStreetMap.load(QtCore.QUrl(
            'https://www.openstreetmap.org/#map=19/52.62640/1.34845'))  # load google on startup
        windowOpenStreetMap.showMaximized()
        app1.exec_()

        app2 = QApplication(sys.argv)

        qImageViewer = QDungeonifyViewer()
        qImageViewer.show()

        sys.exit(app2.exec_())
    else:
        app2 = QApplication(sys.argv)

        qImageViewer = QDungeonifyViewer()
        qImageViewer.show()

        app2.exec_()
        sys.exit()

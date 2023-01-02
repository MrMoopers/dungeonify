from osmapi import OsmApi
from coord_conversion import CoordConversion
# import tag_tables
# from tag_tables import x
import math
# import drawSvg as draw
import cairo

# File    : osm_factory.py
# Classes : GenerateOSM
# Author  : Adam Biggs (100197567)
# Date    : 18/05/2022
# Notes   : Is used to collect and configure data pulled out of the OSM API.


# Create API
myApi = OsmApi()

# proper colours:
# https://github.com/gravitystorm/openstreetmap-carto/blob/master/style/roads.mss

# basic_highway_tags = {
# 'motorway': 'E990A0',
# 'trunk': 'FBC0AC',
# 'primary': 'FDD7A1',
# 'secondary': 'F6FABB',
# 'tertiary': 'FEFEFE',
# 'unclassified': 'FEFEFE',
# 'residential': 'FEFEFE',
# 'service': '888888',#wrong
# 'default': '000000',
# }

# basic_building_tags = {
# 'default': 'AAAAAA',   #wrong
# 'default': 'D9D0C9',
# }

# ----------------
# Handy dandy reg exp for vscode:
# (building 	[\w]* 	)

# # All Roads Red
tagData = {
    # Structures
    'building': '0000FF',
    'brand': '0000FF',
    'abutters': '0000FF',
    'name': '0000FF',
    'addr:housenumber': '0000FF',
    'addr:city': '0000FF',
    'house': '0000FF',
    'craft': '0000FF',
    'emergency': '0000FF',
    'office': '0000FF',
    'shop': '0000FF',
    'sport': '0000FF',
    'telecom': '0000FF',
    'tourism': '0000FF',
    'place_of_worship': '0AA0FF',

    # Roads, paths, etc.
    'highway': 'FF0000',
    'footway': 'FF0000',
    'cycleway': 'FF0000',
    'busway': 'FF0000',
    'aerialway': 'FF0000',
    'aeroway': 'FF0000',
    'electrified': 'FF0000',
    'bicycle': 'FF0000',
    'bridge': 'FF0000',
    'cycleway:both': 'FF0000',
    'public_footpath': 'FF0000',
    'access': 'FF0000',
    'designation': 'FF0000',
    'foot': 'FF0000',

    # Wildlife grass areas: the broads
    'natural': '00FF00',
    'note': '00FF00',

    # Region of land: residential zoning
    'landuse': '888888',

    #e.g. fencing
    'barrier': '0FFFF0',

    # Just remove these:
    'boat': 'FFFFFF',
    'fixme': 'FFFFFF',
    '': 'FFFFFF',
    'amenity': 'FFFFFF',
    'addr:postcode': 'FFFFFF',
    'parking': 'FFFFFF',
    'park': 'FFFFFF',
    'default1': 'FFFFFF',
    'leisure': 'FFFFFF',

    'source': '00FF00',
    'default2': '000000'
}

colourHexOutline = ''
colourHexFill = ''

# Area at zoom 19:
#   https://www.openstreetmap.org/#map=19/52.62956/1.33192

# Test Position
# # Top Left:                    Zoom / lat / long
# https://www.openstreetmap.org/#map=19/52.63010/1.33118
# #bottom Right:
# https://www.openstreetmap.org/#map=19/52.62898/1.33309
#
# def Map(self, min_lon, min_lat, max_lon, max_lat)


class GenerateOSM():
    def generate(self, lng, lat, SCREEN_WIDTH, SCREEN_HEIGHT):
        latLngZoomFactor = 0.002
        screenRatioA = SCREEN_WIDTH / SCREEN_HEIGHT
        screenRatioB = SCREEN_HEIGHT / SCREEN_WIDTH
        lng_upper = float(lng) + latLngZoomFactor * screenRatioA
        lng_lower = float(lng) - latLngZoomFactor * screenRatioA
        lat_upper = float(lat) + latLngZoomFactor * screenRatioB
        lat_lower = float(lat) - latLngZoomFactor * screenRatioB

        topLeft = {'lng': lng_lower, 'lat': lat_upper, 'scrX': 0, 'scrY': 0}
        bottomRight = {'lng': lng_upper, 'lat': lat_lower,
                       'scrX': SCREEN_WIDTH, 'scrY': SCREEN_HEIGHT}

        # Will i need to make sure the larger numbers go into the correct arguments? ... YES
        # sector1 =  myApi.Map(1.33118, 52.63010, 1.33309, 52.62898) # Original
        # sector1 =  myApi.Map( 1.33309, 52.62898, 1.33118,  52.63010) # swapped both
        # topLeft = {'lng': 1.33118, 'lat': 52.63010, 'scrX': 0, 'scrY': 0}
        # bottomRight = {'lng': 1.33309, 'lat': 52.62898, 'scrX': 805, 'scrY': 742}

        WIDTH = bottomRight['scrX'] - topLeft['scrX']
        HEIGHT = bottomRight['scrY'] - topLeft['scrY']

        # WINDOW_WIDTH = 805
        # WINDOW_HEIGHT = 742

        # establish the coordinate system converting lat and lng to x and y coordinates.
        coordinateSystem = CoordConversion(topLeft['scrX'], topLeft['scrY'], topLeft['lat'], topLeft['lng'],
                                           bottomRight['scrX'], bottomRight['scrY'], bottomRight['lat'], bottomRight['lng'])

        inchesForLatitude_vertical = distanceBetweenNodes_inches(
            topLeft['lat'], bottomRight['lat'], topLeft['lng'], topLeft['lng'])
        inchesForLongitude_horizontal = distanceBetweenNodes_inches(
            topLeft['lat'], topLeft['lat'], topLeft['lng'], bottomRight['lng'])

        # Calculate the per pixel lat and long changes for use in dungeonify.py
        horizontalPixels = bottomRight['scrX']
        verticalPixels = bottomRight['scrY']

        # longitudeDifference = bottomRight['lng'] - topLeft['lng'] # horizontal
        # latitudeDifference = bottomRight['lat'] - topLeft['lat'] # vertical

        inchesPerPixel_vertical = inchesForLatitude_vertical / verticalPixels
        inchesPerPixel_horizontal = inchesForLongitude_horizontal / horizontalPixels

        # To convert from real world 2.5ft doorways to 1 inch dnd doorways divide by 30.
        # TODO: figure out if next bit is required. Im going to use real world data for the moment only.
        inchesPerPixel_verticalBattlemap = inchesPerPixel_vertical / 30
        inchesPerPixel_horizontalbattlemap = inchesPerPixel_horizontal / 30
        # inchesPerPixel_verticalBattlemap = inchesPerPixel_vertical
        # inchesPerPixel_horizontalbattlemap = inchesPerPixel_horizontal
        # print("1.")
        # print(f"inchesPerPixel_horizontalbattlemap = {inchesPerPixel_horizontalbattlemap}")
        # print(f"inchesPerPixel_verticalBattlemap = {inchesPerPixel_verticalBattlemap}")

        xModifier = inchesPerPixel_verticalBattlemap / inchesPerPixel_horizontalbattlemap
        inchesPerPixel_horizontalbattlemap = inchesPerPixel_horizontalbattlemap * xModifier
        # print("2.")
        # print(f"inchesPerPixel_horizontalbattlemap = {inchesPerPixel_horizontalbattlemap}")
        # print(f"inchesPerPixel_verticalBattlemap = {inchesPerPixel_verticalBattlemap}")

        # I think the order depends on which hemisphere it is in, or the side of the planet?
        # The osmAPI data for the region
        sector = myApi.Map(
            topLeft['lng'], bottomRight['lat'], bottomRight['lng'],  topLeft['lat'])

        nodes = [n for n in sector if n['type'] == 'node']
        ways = [w for w in sector if w['type'] == 'way']
        # relations = [r for r in sector if r['type'] == 'relation']

        # for each node calculate the node's x / y and save it on the node
        nodes_data = [n['data'] for n in nodes]
        ways_data = [w['data'] for w in ways]

        ways_tags = [t['tag'] for t in ways_data]

        structures = []

        roads = []
        #   Start Cairo
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        ctx = cairo.Context(surface)
        ctx.scale(WIDTH, HEIGHT)  # Normalizing the canvas

        pat = cairo.SolidPattern(1, 1, 1, 1)
        ctx.rectangle(0, 0, 1, 1)  # Rectangle(x0, y0, x1, y1)
        ctx.set_source(pat)
        ctx.fill()

        for way in ways_data:
            nodes = way['nd']

            key = ''
            specialityStructure = False

            if way['tag']:
                # print(way['tag'])

                key = next(iter(way['tag']))
                if key == 'amenity' and way['tag']['amenity'] == 'place_of_worship':
                    colourHexOutline = tagData['place_of_worship']
                    specialityStructure = True
                elif key in tagData.keys():
                    # print(key + ", ")
                    colourHexOutline = tagData[key]

                    # if isinstance(colourDict, dict):
                    #     value = way['tag'].get(key)

                    #     if value in colourDict.keys():
                    #         colourHexOutline = colourDict[value]
                    #     else:
                    #         colourHexOutline = colourDict['default']
                    # else:
                    #     colourHexOutline = tagData['default']
                else:
                    # print("2. " + key)
                    colourHexOutline = tagData['default2']
            else:
                colourHexOutline = tagData['default1']

            # #find the tag to determine the color
            # key = ''
            # if way['tag']:
            #     key = next(iter(way['tag']))
            #     if key in tagData.keys():
            #         colourDict = tagData[key]

            #         if isinstance(colourDict, dict):
            #             value = way['tag'].get(key)

            #             if value in colourDict.keys():
            #                 colourHexOutline = colourDict[value]
            #             else:
            #                 colourHexOutline = colourDict['default']
            #         else:
            #             colourHexOutline = tagData['default']
            #     else:
            #         colourHexOutline = tagData['default']
            # else:
            #     colourHexOutline = tagData['default']

            # colour = tuple(int(colourHexOutline[i:i+2], 16) for i in (0, 2, 4))
            r = int(colourHexOutline[0:2], 16) / 256
            g = int(colourHexOutline[2:4], 16) / 256
            b = int(colourHexOutline[4:6], 16) / 256

            # print("'%s' : '%s' was colour (%s,%s,%s)" %( key, value, r,g,b))

            ctx.set_source_rgb(r, g, b)  # Solid color

            structureNodes = []
            roadNodes = []
            for node in nodes:
                # May be inefficent at large scale
                node = [n for n in nodes_data if n['id'] == node][0]

                coordinate = coordinateSystem.latlngToScreenXY(
                    node['lat'], node['lon'], xModifier)

                # The x & y out of the total width & height.
                ctx.line_to(coordinate['x'] / WIDTH, coordinate['y'] / HEIGHT)

                if isStructure(colourHexOutline):
                    # wk15: removing lat/long from outside this python file.
                    # structureNodes.append({'x': coordinate['x'],'y': coordinate['y'], 'latitude': node['lat'], 'longitude': node['lon']})

                    structureNodes.append(
                        {'x': coordinate['x'], 'y': coordinate['y']})
                elif isRoad(colourHexOutline):
                    roadNodes.append(
                        {'x': coordinate['x'], 'y': coordinate['y']})

            if len(structureNodes) != 0:
                # structures.append( structureNodes)
                structures.append(
                    {'nodes': structureNodes, 'speciality': specialityStructure})

            if len(roadNodes) != 0:
                roads.append(roadNodes)

            ctx.move_to(0, 0)
            ctx.close_path()

            if isStructure(colourHexOutline):
                ctx.fill()

            ctx.set_line_width(2 / WIDTH)
            ctx.stroke()

        surface.write_to_png("example.png")  # Output to PNG

        return structures, roads, {'horizontal': inchesPerPixel_horizontalbattlemap, 'vertical': inchesPerPixel_verticalBattlemap}


def distanceBetweenNodes_inches(latStart, latEnd, longStart, longEnd):
    import geopy.distance

    coords_1 = (latStart, longStart)
    coords_1 = (latStart, longStart)
    coords_2 = (latEnd, longEnd)

    # print(f"PC decide distance = {geopy.distance.distance(coords_1, coords_2).m}") --> geodesic (might include height distances)

    distance = geopy.distance.great_circle(coords_1, coords_2).ft * 12
    # print(f"great_circle distance = {distance} inches") # perfect sphere

    return distance


def isStructure(colourHex):
    if colourHex == '0000FF' or colourHex == '0AA0FF':
        # if key == 'building' or key == 'amenity' or key == 'office':
        return True
    return False


def isRoad(colourHex):
    if colourHex == 'FF0000':
        # if key == 'building' or key == 'amenity' or key == 'office':
        return True
    return False

import math

EARTH_RADIUS = 6371  # Earth Radius in KM

# File    : coord_conversion.py
# Classes : ReferencePoint & CoordConversion
# Author  : Adam Biggs (100197567)
# Date    : 18/05/2022
# Notes   : Is used to configure latitude and longitude values into screen x and y coordinates.


class ReferencePoint:
    # scrX = 0.0
    # scrY = 0.0
    pos = {'x': 0.0, 'y': 0.0}

    def __init__(self, scrX, scrY, lat, lng):
        self.scrX = scrX
        self.scrY = scrY
        self.lat = lat
        self.lng = lng

    # @pos.setter
    # def pos(self, value):
    #     self.pos['x'] = value['x']
    #     self.pos['y'] = value['y']


class CoordConversion:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def __init__(self, p1_scrX, p1_scrY, p1_lat, p1_lng,
                 p2_scrX, p2_scrY, p2_lat, p2_lng):
        self.p1 = ReferencePoint(p1_scrX, p1_scrY, p1_lat, p1_lng)
        self.p2 = ReferencePoint(p2_scrX, p2_scrY, p2_lat, p2_lng)

    # def return_vals(self):
    #     x = 4
    #     y = 10
    #     return x, y

    # This function converts lat and lng coordinates to GLOBAL X and Y positions
    def latlngToGlobalXY(self, lat, lng):
        # Calculates x based on cos of average of the latitudes
        x = EARTH_RADIUS * lng * math.cos((self.p1.lat + self.p2.lat)/2)
        # Calculates y based on latitude
        y = EARTH_RADIUS * lat
        return {'x': x, 'y': y}
        # return x, y

    def setPos(self):
        self.p1.pos = self.latlngToGlobalXY(self.p1.lat, self.p1.lng)
        self.p2.pos = self.latlngToGlobalXY(self.p2.lat, self.p2.lng)

    # This function converts lat and lng coordinates to SCREEN X and Y positions
    def latlngToScreenXY(self, lat, lng, xModifier):
        # x, y = return_vals()

        # Calculate global X and Y for projection point
        pos = self.latlngToGlobalXY(lat, lng)

        self.setPos()
        # OLD
        # Calculate the percentage of Global X position in relation to total global width
        perX = ((pos['x']-self.p1.pos['x']) /
                (self.p2.pos['x'] - self.p1.pos['x']))
        # Calculate the percentage of Global Y position in relation to total global height
        perY = ((pos['y']-self.p1.pos['y']) /
                (self.p2.pos['y'] - self.p1.pos['y']))

        # # Calculate the percentage of Global X position in relation to total global width
        # perX = ((pos['x']-self.p1.scrX) / (self.p2.scrX - self.p1.scrX))
        # # Calculate the percentage of Global Y position in relation to total global height
        # perY = ((pos['y']-self.p1.scrY)/(self.p2.scrY - self.p1.scrY))

        # Returns the screen position based on reference points
        return {
            'x': (self.p1.scrX + (self.p2.scrX - self.p1.scrX)*perX) * xModifier,
            'y': self.p1.scrY + (self.p2.scrY - self.p1.scrY)*perY
        }

    @staticmethod
    def get_pi(arg):
        return arg + 3.14159286

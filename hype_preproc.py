import os
import haversine
import numpy
from osgeo import ogr


class SubBasin(object):
    id_field = "SUBID"
    x_field = "CENTERX"
    y_field = "CENTERY"
    area_field = "AREA"
    elev_field = "ELEV"

    def __init__(self, id_):
        self.id = id_
        self.centroid = None
        self.area = None
        self.elev = None

    @classmethod
    def read(cls, feature):
        cls.id = feature.GetField(SubBasin.id_field)
        cls.centroid = (feature.GetField(SubBasin.x_field), feature.GetField(SubBasin.y_field))
        cls.area = feature.GetField(SubBasin.area_field)
        cls.elev = feature.GetField(SubBasin.elev_field)
        return cls


def initialize(db_path):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    data_source = driver.Open(os.path.join(db_path, "SUBID_subbasins.dbf"), 0)
    layer = data_source.GetLayer()
    basins = []
    for feature in layer:
        basins.append(SubBasin.read(feature))
    return basins


def create_links(dataset, basins):
    lons = dataset.variables["longitude"][:]
    lats = dataset.variables["latitude"][:]
    nearest_points = find_nearest(lons, lats, basins)
    forcing_ids = {}
    id = 100000
    for p in list(set(nearest_points.values())):
        forcing_ids[id] = p
        for b in basins:
            if nearest_points[b.id] == p:
                setattr(b, "forcing_id", id)
        id += 1
    return forcing_ids


def find_nearest(lons, lats, basins):
    x, y = [b.centroid[0] for b in basins], [b.centroid[1] for b in basins]
    xm, xp, ym, yp = min(x), max(x), min(y), max(y)
    imin, imax = max(0, int(numpy.argmin(lons < xm)) - 1), numpy.argmax(lons > xp)
    jmin, jmax = max(0, int(numpy.argmin(lats < ym)) - 1), numpy.argmax(lats > yp)
    gridlons, gridlats = numpy.meshgrid(lons[imin:imax], lats[jmin:jmax])
    result = {}
    for basin in basins:
        def func(x_, y_):
            return haversine.haversine(basin.centroid, (x_, y_))

        vfunc = numpy.vectorize(func)
        dists = vfunc(gridlons, gridlats)
        i, j = numpy.unravel_index(numpy.argmin(dists), dims=gridlats.shape)
        result[basin.id] = (i + imin, j + jmin)
    return result

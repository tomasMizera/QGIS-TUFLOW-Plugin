# to co sa robi s vlayerom v prototype
# class s menom TuflowParticlesLayer
# ked sa v plugine otvori file, tu bude nieco ako canOpen (pozrie variables netcdf suboru), ak je valid
# spravi open.

# Slider zobrazuje najblizsi nizsi cas

from qgis.core import QgsVectorLayer


class TuflowParticlesLayer(QgsVectorLayer):

    def __init__(self, **kwargs):
        # catch delete signal on layer
        super(kwargs)

    def destroyLayer(self):
        pass

    def populateLayerWithData(self):
        pass
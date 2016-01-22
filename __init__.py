# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapDash
                                 A QGIS plugin
 This plugin transforms a QGIS project to a web dashboard
                             -------------------
        begin                : 2015-12-09
        copyright            : (C) 2015 by Brian Duffy
        email                : brian.duffy@soprasteria.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load MapDash class from file MapDash.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .map_dash import MapDash
    return MapDash(iface)

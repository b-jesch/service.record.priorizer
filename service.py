import time
from resources.lib.toollib import *

k = KodiLib()

# PVR server

_has_pvr = False
_st = int(time.time())
_attempts = k.getAddonSetting('conn_attempts', sType=NUM, multiplicator=5)
while not _has_pvr and _attempts > 0:
    query = {'method': 'PVR.GetProperties',
             'params': {'properties': ['available']}}
    response = k.jsonrpc(query)
    _has_pvr = True if (response is not None and response.get('available', False)) else False
    if _has_pvr: break
    xbmc.sleep(1000)
    _attempts -= 1

k.writeLog('Waiting %s seconds for PVR response' % (int(time.time()) - _st))

if not _has_pvr:
    k.writeLog('PVR timed out', xbmc.LOGERROR)
    k.notify(ADDON_NAME, LS(30032), icon=xbmcgui.NOTIFICATION_WARNING)

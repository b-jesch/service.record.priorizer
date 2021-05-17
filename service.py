import os.path
import sys
import time
from datetime import datetime

from resources.lib.toollib import *

TVH = 'pvr.hts'
TIME_OFFSET = round((datetime.now() - datetime.utcnow()).seconds, -1)
JSON_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
LOCAL_TIME_FORMAT = '{} - {}'.format(xbmc.getRegion('dateshort'), xbmc.getRegion('time'))

k = KodiLib()


class Mon(xbmc.Monitor):

    settingschanged = False

    def onSettingsChanged(self):
        self.settingschanged = True


# check PVR server availability

_has_pvr = False
_st = time.time()

attempts = k.getAddonSetting('conn_attempts', sType=NUM, multiplicator=5)
margin = k.getAddonSetting('margin', sType=NUM)

while not _has_pvr and attempts > 0:
    query = {'method': 'PVR.GetProperties',
             'params': {'properties': ['available']}}
    response = k.jsonrpc(query)
    _has_pvr = True if (response and response.get('available', False)) else False
    if _has_pvr: break
    xbmc.sleep(1000)
    attempts -= 1

k.writeLog('Waiting {:.2f} seconds for PVR responses'.format(time.time() - _st))

# check presence of TVHeadend

_tvh_client = False
query = {'method': 'PVR.getClients',
         'params': {}}
response = k.jsonrpc(query)
if response:
    clients = response.get('clients', None)
    addon_ids = [client['addonid'] for client in clients]
    if TVH in addon_ids: _tvh_client = True

if _has_pvr and _tvh_client:
    k.writeLog('TVH server available and ready')
else:
    k.writeLog('TVH not available or timed out', xbmc.LOGERROR)
    k.notify(ADDON_NAME, LS(30100), icon=xbmcgui.NOTIFICATION_WARNING)
    sys.exit()


def read_priorized():
    cgs_ids_priorized = list()

    # resolve priorized channelgroups by name to channelgroup IDs

    cgs_names_priorized = k.getAddonSetting('channelgroups').split(', ')
    if cgs_names_priorized:
        query = {'method': 'PVR.GetChannelgroups',
                 'params': {'channeltype': 'tv'}}
        response = k.jsonrpc(query)
        if response:
            for cg_name_priorized in cgs_names_priorized:
                for group in response['channelgroups']:
                    if group['label'] == cg_name_priorized: cgs_ids_priorized.append(group['channelgroupid'])

        # collect priorized channel Ids

        c_ids = list()
        for cg_id_priorized in cgs_ids_priorized:
            query = {'method': 'PVR.GetChannelGroupDetails',
                     'params': {'channelgroupid': cg_id_priorized}}
            response = k.jsonrpc(query)
            if response:
                channels = response['channelgroupdetails']['channels']
                c_ids.extend([channel['channelid'] for channel in channels])
                k.writeLog('Update priorized channel IDs: {}'.format(c_ids))
                return c_ids
    return False


def service(CP=None):

    while not monitor.abortRequested():

        if monitor.waitForAbort(5):
            break

        if monitor.settingschanged:
            CP = read_priorized()
            monitor.settingschanged = False

        if not CP: continue

        # check for priorized timers

        isREC = False
        timer_id = None
        timer_title = None
        query = {'method': 'PVR.GetTimers',
                 'params': {'properties': ['starttime', 'startmargin', 'istimerrule', 'state', 'channelid', 'title']}}
        response = k.jsonrpc(query)
        if response and response.get('timers', False):
            for timer in response.get('timers'):
                if timer['channelid'] not in CP or timer['istimerrule'] or timer['state'] == 'disabled':
                    continue
                elif timer['state'] == 'recording' or \
                        time.mktime(time.strptime(timer['starttime'], JSON_TIME_FORMAT)) - \
                        margin - (timer['startmargin'] * 60) + TIME_OFFSET < int(time.time()):
                    isREC = True
                    timer_id = timer['channelid']
                    break
                else:
                    pass
        else:
            continue

        # check for player activities and stop player if necessary, collect player properties

        if isREC:
            props = dict({'title': timer_title})
            query = {
                "method": "Player.GetActivePlayers",
                }
            response = k.jsonrpc(query)

            if response:
                props.update({'playerid': response[0].get('playerid', None)})
                query = {
                    "method": "Player.GetItem",
                    "params": {"properties": ["title", "season", "episode", "file"],
                               "playerid": props['playerid']},
                    "id": "VideoGetItem"
                }
                response = k.jsonrpc(query)

                if response:
                    props.update({'media': response['item'].get('type', None),
                                  'channelid': response['item'].get('id', None),
                                  'title': response['item'].get('title', None)})

                if props['media'] != 'channel': continue
                if props['channelid'] not in CP or props['channelid'] == timer_id: continue

                # Stop player and notify user

                query = {
                    "method": "Player.Stop",
                    "params": {"playerid": props['playerid']},
                }
                response = k.jsonrpc(query)

                if response == "OK":
                    k.writeLog('Player stopped')
                    k.notify('{} - {}'.format(ADDON_NAME, LS(30050)),
                             '{} - {}'.format(LS(30051), props['title']))
    return


if __name__ == '__main__':
    try:
        option = sys.argv[1].lower()
        if option == 'set_tvgroup':
            query = {'method': 'PVR.GetChannelgroups',
                     'params': {'channeltype': 'tv'}}
            response = k.jsonrpc(query)
            if response:
                _clist = list()
                channelgroups = response.get('channelgroups', [])
                for channel in channelgroups:
                    liz = xbmcgui.ListItem(label=channel.get('label'))
                    liz.setProperty('channelgroupid', str(channel.get('channelgroupid')))
                    _clist.append(liz)
                dialog = xbmcgui.Dialog()
                _idx = dialog.multiselect(LS(30013), _clist)
                if _idx is not None:
                    ADDON.setSetting('channelgroups', ', '.join([_clist[i].getLabel() for i in _idx]))

    except IndexError:
        CP = read_priorized()
        monitor = Mon()
        service(CP)




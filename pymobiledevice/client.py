from time import sleep
import socketio
import lockdown
import plistlib


sio = socketio.Client()
lockdownClient = None
service_map = {}


@sio.event
def connect():
    global lockdownClient
    print('connection established')

    lockdownClient = lockdown.LockdownClient()
    if lockdownClient:
        print("[client] file: %s_infos.plist" % lockdownClient.udid)
        n = lockdown.writeHomeFile(lockdown.HOMEFOLDER, "%s_infos.plist" % lockdownClient.udid, plistlib.writePlistToString(lockdownClient.allValues))
        sio.emit('lockdown_client_connected', {'device_id': lockdownClient.udid})
    else:
        print("Unable to connect to device")


@sio.event
def disconnect():
    print('disconnected from server')


@sio.on('start_lockdown_service')
def on_start_lockdown_service(data):
    global lockdownClient
    print(f"[client] start lockdown service: {data}")
    service_name = data['Service']
    if service_name in service_map:
        return

    if lockdownClient:
        plist_service = lockdownClient.myStartService(data)
        service_map[service_name] = plist_service

        if service_name == 'com.apple.mobile.screenshotr':
            print("[client] start com.apple.mobile.screenshotr")
            DLMessageVersionExchange = plist_service.recvPlist()
            version_major = DLMessageVersionExchange[1]
            plist_service.sendPlist(["DLMessageVersionExchange", "DLVersionsOk", version_major])
            DLMessageDeviceReady = plist_service.recvPlist()
            sio.emit('start_lockdown_service_success', {'port': plist_service.port, 'name': data['Service']})
        else:
            sio.emit('start_lockdown_service_success', {'port': plist_service.port, 'name': data['Service']})
    else:
        sio.emit('start_lockdown_service_failure', {})


@sio.on('service_command_request')
def on_service_command_request(data):
    global lockdownClient
    print(f"[client] service_command: {data}")
    service_name = data['service']
    if service_name in service_map:
        plist_service = service_map[service_name]
        if plist_service:
            print(f"[client] send command: {data['command']}")
            plist_service.sendPlist(data['command'])
            response = plist_service.recvPlist()
            # print(f"[client] response: {response}")
            sio.emit('service_command_response', {'response': response, 'name': service_name})


@sio.on('common_request')
def on_common_request(data):
    global lockdownClient
    print(f"[client] common_request: {data}")
    print(f"[client] lockdown all values: {lockdownClient.allValues}")
    if lockdownClient:
        response = lockdownClient.mySendRequest(data)
        print(f"[client] response: {response}")
        sio.emit('common_response', {'response': response})


sio.connect('http://127.0.0.1:5000')

sio.wait()
